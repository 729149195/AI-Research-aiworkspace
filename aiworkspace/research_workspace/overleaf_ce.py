"""Built-in Overleaf Community Edition (CE) client and sync transport.

Communicates directly with a self-hosted Overleaf CE server via its standard
HTTPS and Socket.IO 0.9 real-time OT protocol—no third-party editor plugin,
browser automation, or Pro Git Bridge required.

Security boundaries:
- Never store raw passwords in workspace files, configs, or command arguments.
- Session cookies are stored only under `.rw/overleaf/ce-session.json` (0600,
  git-ignored, outside manuscript/ and export boundaries).
- Same-host HTTPS redirect enforcement prevents cookie leakage.
- Only the explicitly configured `manuscript/` subtree is synchronized.
"""
from __future__ import annotations

import difflib
import http.cookiejar
import json
import mimetypes
import os
import re
import secrets
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .model import WorkspaceError, identifier, now, pretty, require
from .publication_io import MAX_DOWNLOAD, MAX_EXPANDED, MAX_FILES, archive_path, sha, tree_bytes
from .store import Store, atomic_write, read_text, safe_path

SESSION_FILE = '.rw/overleaf/ce-session.json'
VERIFY_FILE = '.rw/overleaf/ce-verify.json'
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/131.0.0.0 Safari/537.36'
)
TEXT_DOC_EXTENSIONS = {
    '.tex', '.ltx', '.latex', '.bib', '.bibtex', '.cls', '.sty', '.bst',
    '.bbx', '.cbx', '.def', '.clo', '.cfg', '.fd', '.dtx', '.ins', '.txt',
    '.md', '.csv', '.dat', '.json', '.xml', '.yml', '.yaml', '.tikz', '.mtx',
    '.rtex', '.rnw', '.lua', '.gv', '.mf', '.lhs', '.mk', '.inc', '.asy',
    '.lbx', '.lco', '.ldf', '.rmd', '.xmpdata',
}
TEXT_DOC_FILENAMES = {'LICENSE', 'README', 'COPYING', 'latexmkrc', '.latexmkrc', 'makefile', 'Makefile'}


# ---------------------------------------------------------------------------
# UTF-16 & Overleaf ShareJS OT helpers
# ---------------------------------------------------------------------------

def decode_overleaf_doc_line(line: str) -> str:
    """Decode Overleaf real-time Socket.IO 0.9 joinDoc lines (UTF-8 bytes packed in Latin-1)."""
    try:
        return line.encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return line


def utf16_len(text: str) -> int:
    """Return length in UTF-16 code units, matching JavaScript / Overleaf OT offsets."""
    return len(text.encode('utf-16-le')) // 2


def compute_ot_ops(old_text: str, new_text: str) -> list[dict[str, Any]]:
    """Compute minimal sequential ShareJS/Overleaf OT ops transforming old_text -> new_text."""
    if old_text == new_text:
        return []
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    ops: list[dict[str, Any]] = []
    pos = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            pos += utf16_len(''.join(old_lines[i1:i2]))
            continue
        removed = ''.join(old_lines[i1:i2])
        inserted = ''.join(new_lines[j1:j2])
        # Trim common character prefix/suffix inside a replacement hunk for minimal OT diffs.
        prefix = 0
        limit = min(len(removed), len(inserted))
        while prefix < limit and removed[prefix] == inserted[prefix]:
            prefix += 1
        suffix = 0
        rem_left = len(removed) - prefix
        ins_left = len(inserted) - prefix
        s_limit = min(rem_left, ins_left)
        while suffix < s_limit and removed[len(removed) - 1 - suffix] == inserted[len(inserted) - 1 - suffix]:
            suffix += 1
        edit_pos = pos + utf16_len(removed[:prefix])
        del_part = removed[prefix:len(removed) - suffix] if suffix else removed[prefix:]
        ins_part = inserted[prefix:len(inserted) - suffix] if suffix else inserted[prefix:]
        if del_part:
            ops.append({'p': edit_pos, 'd': del_part})
        if ins_part:
            ops.append({'p': edit_pos, 'i': ins_part})
        pos += utf16_len(inserted)
    return ops


def apply_ot_ops_local(text: str, ops: list[dict[str, Any]]) -> str:
    """Apply Overleaf OT ops locally using UTF-16 code unit indexing (for verification/tests)."""
    buf = text.encode('utf-16-le')
    for item in ops:
        p = item['p']
        byte_pos = p * 2
        require(0 <= byte_pos <= len(buf), 'OT offset out of bounds.')
        if 'd' in item:
            del_bytes = item['d'].encode('utf-16-le')
            require(buf[byte_pos:byte_pos + len(del_bytes)] == del_bytes, 'OT delete mismatch.')
            buf = buf[:byte_pos] + buf[byte_pos + len(del_bytes):]
        if 'i' in item:
            ins_bytes = item['i'].encode('utf-16-le')
            buf = buf[:byte_pos] + ins_bytes + buf[byte_pos:]
    return buf.decode('utf-16-le')


def is_text_doc(path: str, data: bytes) -> bool:
    """Return True if a new path should be created as an Overleaf OT text doc."""
    if b'\x00' in data:
        return False
    p = Path(path)
    if p.suffix.lower() not in TEXT_DOC_EXTENSIONS and p.name not in TEXT_DOC_FILENAMES:
        return False
    try:
        data.decode('utf-8')
        return True
    except UnicodeDecodeError:
        return False


def make_probe_png(nonce: str) -> bytes:
    """Build a valid 1x1 transparent PNG connection probe (not research data)."""
    def chunk(ctype: bytes, payload: bytes) -> bytes:
        crc = zlib.crc32(ctype + payload) & 0xFFFFFFFF
        return struct.pack('>I', len(payload)) + ctype + payload + struct.pack('>I', crc)

    ihdr = struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0)
    text_chunk = chunk(b'tEXt', b'AIWorkspaceProbe\x00NOT RESEARCH DATA; ' + nonce.encode('ascii'))
    idat = chunk(b'IDAT', zlib.compress(b'\x00\x00\x00\x00\x00'))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + text_chunk + idat + chunk(b'IEND', b'')


# ---------------------------------------------------------------------------
# HTML / metadata parsers & multipart encoding
# ---------------------------------------------------------------------------

def extract_csrf(html: str) -> str:
    """Extract Overleaf CSRF token from HTML page."""
    patterns = (
        r'<meta\s+name=["\']ol-csrfToken["\']\s+content=["\']([^"\']+)["\']',
        r'<meta\s+content=["\']([^"\']+)["\']\s+name=["\']ol-csrfToken["\']',
        r'window\.csrfToken\s*=\s*["\']([^"\']+)["\']',
        r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']',
        r'value=["\']([^"\']+)["\'][^>]*name=["\']_csrf["\']',
    )
    for pattern in patterns:
        m = re.search(pattern, html, re.I)
        if m:
            return m.group(1)
    raise WorkspaceError('Could not locate Overleaf CSRF token. Verify the server URL and reachability.')


def extract_meta_json(html: str, name: str) -> Any:
    """Extract a JSON-encoded <meta name="..." data-type="json" content="..."> blob."""
    from html import unescape
    m = re.search(
        r'<meta\s+[^>]*name=["\']' + re.escape(name) + r'["\'][^>]*content=["\']([^"\']*)["\']',
        html,
        re.I,
    )
    if not m:
        m = re.search(
            r'<meta\s+[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']' + re.escape(name) + r'["\']',
            html,
            re.I,
        )
    if not m:
        return None
    try:
        return json.loads(unescape(m.group(1)))
    except json.JSONDecodeError:
        return None


def encode_multipart(fields: dict[str, str], file_field: str, filename: str, data: bytes, content_type: str) -> tuple[bytes, str]:
    """Encode a multipart/form-data payload using stdlib only."""
    boundary = '----AIWorkspaceBoundary' + secrets.token_hex(12)
    parts: list[bytes] = []
    for k, v in fields.items():
        parts.append(
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="{k}"\r\n\r\n'
            f'{v}\r\n'.encode('utf-8')
        )
    safe_name = filename.replace('"', '_').replace('\r', '').replace('\n', '')
    parts.append(
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="{file_field}"; filename="{safe_name}"\r\n'
        f'Content-Type: {content_type}\r\n\r\n'.encode('utf-8')
        + data
        + b'\r\n'
    )
    parts.append(f'--{boundary}--\r\n'.encode('utf-8'))
    return b''.join(parts), f'multipart/form-data; boundary={boundary}'


# ---------------------------------------------------------------------------
# Project tree representation
# ---------------------------------------------------------------------------

@dataclass
class ProjectTree:
    project_id: str
    name: str
    root_folder_id: str
    root_doc_id: str | None = None
    compiler: str | None = None
    folders: dict[str, str] = field(default_factory=dict)  # '' -> root_folder_id, 'a/b' -> id
    docs: dict[str, str] = field(default_factory=dict)     # 'main.tex' -> doc_id
    files: dict[str, str] = field(default_factory=dict)    # 'fig.png' -> file_id


def flatten_project(project: dict[str, Any]) -> ProjectTree:
    """Flatten Overleaf joinProject payload into safe POSIX path -> entity ID maps."""
    root_list = project.get('rootFolder')
    require(isinstance(root_list, list) and len(root_list) >= 1 and isinstance(root_list[0], dict),
            'Malformed Overleaf project tree.')
    root = root_list[0]
    root_id = str(root.get('_id', ''))
    require(bool(root_id), 'Missing rootFolder _id in Overleaf project.')
    tree = ProjectTree(
        project_id=str(project.get('_id', '')),
        name=str(project.get('name', '')),
        root_folder_id=root_id,
        root_doc_id=str(project['rootDoc_id']) if project.get('rootDoc_id') else None,
        compiler=str(project['compiler']) if project.get('compiler') else None,
        folders={'': root_id},
    )

    def walk(folder: dict[str, Any], prefix: str) -> None:
        for doc in folder.get('docs', []) or []:
            rel = archive_path((prefix + '/' + doc['name']) if prefix else doc['name'])
            tree.docs[rel] = str(doc['_id'])
        for ref in folder.get('fileRefs', []) or []:
            rel = archive_path((prefix + '/' + ref['name']) if prefix else ref['name'])
            tree.files[rel] = str(ref['_id'])
        for sub in folder.get('folders', []) or []:
            rel = archive_path((prefix + '/' + sub['name']) if prefix else sub['name'])
            tree.folders[rel] = str(sub['_id'])
            walk(sub, rel)

    walk(root, '')
    return tree


# ---------------------------------------------------------------------------
# Same-host HTTPS session & cookie management
# ---------------------------------------------------------------------------

class _SameHostRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, allowed_netloc: str):
        self.allowed_netloc = allowed_netloc.lower()
        self.hops = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.hops += 1
        require(self.hops <= 6, 'Too many redirects from Overleaf server.')
        target = urllib.parse.urljoin(req.full_url, newurl)
        u = urllib.parse.urlsplit(target)
        require(u.scheme == 'https' and u.netloc.lower() == self.allowed_netloc,
                'Refused cross-host or insecure redirect while talking to Overleaf CE.')
        return super().redirect_request(req, fp, code, msg, headers, target)


def _normalize_server(server: str) -> str:
    u = urllib.parse.urlsplit(server.rstrip('/'))
    require(
        u.scheme == 'https' and u.hostname and not u.username and not u.password
        and not u.query and not u.fragment and u.path in ('', '/'),
        'Use an HTTPS Overleaf server homepage URL without embedded credentials.',
    )
    return urllib.parse.urlunsplit((u.scheme, u.netloc.lower(), '', '', ''))


class CEHttpSession:
    """HTTPS session bound to one Overleaf CE origin with isolated cookie jar."""

    def __init__(self, server: str, cookies: list[dict[str, Any]] | None = None):
        self.server = _normalize_server(server)
        self.netloc = urllib.parse.urlsplit(self.server).netloc
        self.host = urllib.parse.urlsplit(self.server).hostname or self.netloc
        self.jar = http.cookiejar.CookieJar()
        if cookies:
            for item in cookies:
                c = http.cookiejar.Cookie(
                    version=0,
                    name=item['name'],
                    value=item['value'],
                    port=None,
                    port_specified=False,
                    domain=item.get('domain') or self.host,
                    domain_specified=bool(item.get('domain')),
                    domain_initial_dot=str(item.get('domain', '')).startswith('.'),
                    path=item.get('path', '/'),
                    path_specified=True,
                    secure=bool(item.get('secure', True)),
                    expires=item.get('expires'),
                    discard=item.get('expires') is None,
                    comment=None,
                    comment_url=None,
                    rest={'HttpOnly': None},
                )
                self.jar.set_cookie(c)
        self.csrf: str | None = None

    def _opener(self):
        return urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar),
            _SameHostRedirect(self.netloc),
        )

    def cookie_header(self) -> str:
        return '; '.join(f'{c.name}={c.value}' for c in self.jar)

    def export_cookies(self) -> list[dict[str, Any]]:
        return [
            {
                'name': c.name,
                'value': c.value,
                'domain': c.domain,
                'path': c.path,
                'secure': c.secure,
                'expires': c.expires,
            }
            for c in self.jar
        ]

    def request(
        self,
        method: str,
        path: str,
        *,
        data: bytes | None = None,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: int = 30,
        max_bytes: int = MAX_DOWNLOAD,
    ) -> tuple[int, str, dict[str, str], bytes]:
        require(path.startswith('/'), 'Relative server path must start with /.')
        url = self.server + path
        req_headers = {
            'User-Agent': USER_AGENT,
            'Accept': '*/*',
            'Origin': self.server,
            'Referer': self.server + '/',
        }
        if json_body is not None:
            data = json.dumps(json_body).encode('utf-8')
            req_headers['Content-Type'] = 'application/json'
            req_headers['Accept'] = 'application/json, text/plain, */*'
        if headers:
            req_headers.update(headers)
        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
        try:
            with self._opener().open(req, timeout=timeout) as resp:
                body = resp.read(max_bytes + 1)
                require(len(body) <= max_bytes, 'Overleaf response exceeded safety size limit.')
                hdrs = {k.lower(): v for k, v in resp.headers.items()}
                return resp.status, resp.url, hdrs, body
        except urllib.error.HTTPError as exc:
            err_body = exc.read(8192)
            hdrs = {k.lower(): v for k, v in exc.headers.items()}
            return exc.code, getattr(exc, 'url', url), hdrs, err_body
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise WorkspaceError(f'Network error contacting Overleaf CE ({self.host}): {type(exc).__name__}') from exc

    def login(self, email: str, password: str) -> dict[str, Any]:
        require(bool(email.strip()) and bool(password), 'Email and password are required for Overleaf CE login.')
        status, _, _, body = self.request('GET', '/login')
        require(status == 200, f'Failed to open Overleaf login page (HTTP {status}).')
        html = body.decode('utf-8', errors='replace')
        exposed = extract_meta_json(html, 'ol-ExposedSettings') or {}
        recaptcha = exposed.get('recaptchaDisabled')
        if isinstance(recaptcha, dict) and recaptcha.get('login') is False:
            raise WorkspaceError(
                'Overleaf server requires CAPTCHA on /login. '
                'Log in via your own browser and import the session cookie with RW_OVERLEAF_COOKIE instead.'
            )
        csrf = extract_csrf(html)
        status, final_url, _, resp_body = self.request(
            'POST',
            '/login',
            json_body={'_csrf': csrf, 'email': email.strip(), 'password': password},
            headers={'X-Csrf-Token': csrf, 'Referer': self.server + '/login'},
        )
        if status >= 400:
            raise WorkspaceError(f'Overleaf CE login rejected (HTTP {status}). Check email and password.')
        text = resp_body.decode('utf-8', errors='replace').strip()
        if text.startswith('{'):
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = {}
            msg = payload.get('message')
            if isinstance(msg, dict) and msg.get('type') == 'error':
                raise WorkspaceError('Overleaf CE login failed: ' + str(msg.get('text', 'invalid credentials')))
        elif '/login' in urllib.parse.urlsplit(final_url).path:
            raise WorkspaceError('Overleaf CE login did not create an authenticated session.')
        return self.verify_session()

    def login_with_cookie(self, raw_cookie: str) -> dict[str, Any]:
        require(bool(raw_cookie.strip()) and '\r' not in raw_cookie and '\n' not in raw_cookie,
                'Invalid cookie header value.')
        added = 0
        for part in raw_cookie.split(';'):
            part = part.strip()
            if '=' not in part:
                continue
            name, value = part.split('=', 1)
            name, value = name.strip(), value.strip()
            if not name:
                continue
            c = http.cookiejar.Cookie(
                version=0, name=name, value=value, port=None, port_specified=False,
                domain=self.host, domain_specified=True, domain_initial_dot=False,
                path='/', path_specified=True, secure=True, expires=None, discard=True,
                comment=None, comment_url=None, rest={'HttpOnly': None},
            )
            self.jar.set_cookie(c)
            added += 1
        require(added > 0, 'No valid cookie name=value pairs supplied.')
        return self.verify_session()

    def verify_session(self) -> dict[str, Any]:
        status, final_url, _, body = self.request('GET', '/project')
        if status != 200 or '/login' in urllib.parse.urlsplit(final_url).path:
            raise WorkspaceError('Overleaf CE session is unauthenticated or expired; run overleaf login --online.')
        html = body.decode('utf-8', errors='replace')
        self.csrf = extract_csrf(html)
        user_email = ''
        m = re.search(r'<meta\s+name=["\']ol-usersEmail["\']\s+content=["\']([^"\']*)["\']', html, re.I)
        if m:
            user_email = m.group(1)
        return {
            'version': 1,
            'server': self.server,
            'logged_in_at': now(),
            'user_email': user_email,
            'cookies': self.export_cookies(),
        }

    def refresh_project_csrf(self, project_id: str) -> str:
        status, final_url, _, body = self.request('GET', f'/project/{project_id}')
        if status == 404:
            raise WorkspaceError(f'Overleaf project not found or no access: {project_id}')
        if status != 200 or '/login' in urllib.parse.urlsplit(final_url).path:
            raise WorkspaceError('Overleaf CE session expired or project inaccessible; run overleaf login --online.')
        self.csrf = extract_csrf(body.decode('utf-8', errors='replace'))
        return self.csrf

    def list_projects(self) -> list[dict[str, Any]]:
        status, final_url, _, body = self.request('GET', '/project')
        if status != 200 or '/login' in urllib.parse.urlsplit(final_url).path:
            raise WorkspaceError('Overleaf CE session expired; run overleaf login --online.')
        html = body.decode('utf-8', errors='replace')
        self.csrf = extract_csrf(html)
        blob = extract_meta_json(html, 'ol-prefetchedProjectsBlob')
        projects = blob.get('projects', []) if isinstance(blob, dict) else []
        out = []
        for item in projects:
            if not isinstance(item, dict):
                continue
            out.append({
                'id': item.get('id') or item.get('_id'),
                'name': item.get('name', ''),
                'access_level': item.get('accessLevel', ''),
                'last_updated': item.get('lastUpdated', ''),
                'archived': bool(item.get('archived', False)),
                'trashed': bool(item.get('trashed', False)),
            })
        return out

    def create_project(self, name: str, *, template: str = 'none') -> dict[str, Any]:
        clean = name.strip()
        require(bool(clean) and len(clean) <= 200 and not any(ord(c) < 32 for c in clean),
                'Provide a valid Overleaf project name (1-200 printable characters).')
        require(template in ('none', 'example'), 'Unsupported Overleaf project template.')
        status, final_url, _, body = self.request('GET', '/project')
        if status != 200 or '/login' in urllib.parse.urlsplit(final_url).path:
            raise WorkspaceError('Overleaf CE session expired; run overleaf login --online.')
        csrf = extract_csrf(body.decode('utf-8', errors='replace'))
        self.csrf = csrf
        st, _, _, resp_body = self.request(
            'POST',
            '/project/new',
            json_body={'_csrf': csrf, 'projectName': clean, 'template': template},
            headers={'X-Csrf-Token': csrf, 'Referer': self.server + '/project'},
        )
        require(st in (200, 201), f'Failed to create Overleaf CE project (HTTP {st}).')
        parsed = json.loads(resp_body.decode('utf-8'))
        pid = str(parsed.get('project_id') or parsed.get('_id') or '')
        require(bool(pid), 'Overleaf server did not return a project_id.')
        return {
            'created': True,
            'server': self.server,
            'project_id': pid,
            'name': clean,
            'url': f'{self.server}/project/{pid}',
        }


# ---------------------------------------------------------------------------
# Socket.IO 0.9.17-overleaf real-time WebSocket client
# ---------------------------------------------------------------------------

class OverleafSocket:
    """Minimal Socket.IO 0.9 client speaking Overleaf CE's real-time protocol."""

    def __init__(self, session: CEHttpSession, project_id: str, timeout: float = 20.0):
        self.session = session
        self.project_id = project_id
        self.timeout = timeout
        self.ws = None
        self._msg_id = 0
        self._initial_project: tuple[dict[str, Any], str] | None = None

    def connect(self) -> None:
        try:
            import websocket  # type: ignore[import-not-found]
        except ImportError as exc:
            raise WorkspaceError(
                'Built-in Overleaf CE mode requires websocket-client in the framework venv '
                '(pip install "websocket-client>=1.6,<2").'
            ) from exc
        ts = int(time.time() * 1000)
        q = urllib.parse.urlencode({'projectId': self.project_id, 't': str(ts)})
        status, _, _, body = self.session.request(
            'GET',
            f'/socket.io/1/?{q}',
            headers={'Referer': f'{self.session.server}/project/{self.project_id}'},
        )
        require(status == 200, f'Overleaf Socket.IO handshake failed (HTTP {status}).')
        parts = body.decode('utf-8', errors='replace').strip().split(':')
        require(len(parts) >= 4 and 'websocket' in parts[3].split(','),
                'Overleaf server did not offer Socket.IO 0.9 websocket transport.')
        sid = parts[0]
        ws_url = f'wss://{self.session.netloc}/socket.io/1/websocket/{sid}?projectId={urllib.parse.quote(self.project_id)}'
        headers = [
            f'Cookie: {self.session.cookie_header()}',
            f'Origin: {self.session.server}',
            f'User-Agent: {USER_AGENT}',
        ]
        self._initial_project = None
        self.ws = websocket.create_connection(ws_url, header=headers, timeout=self.timeout)
        # Wait for either Overleaf CE 5.x auto-pushed joinProjectResponse or CE 4.x connectionAccepted.
        deadline = time.monotonic() + min(self.timeout, 15.0)
        saw_connect = False
        while time.monotonic() < deadline:
            remaining = max(0.2, deadline - time.monotonic())
            self.ws.settimeout(remaining)
            try:
                frame = self.ws.recv()
            except Exception:
                if saw_connect:
                    break
                raise WorkspaceError('Timed out waiting for Overleaf real-time connection.')
            if not isinstance(frame, str):
                continue
            if frame.startswith('2::'):
                self.ws.send('2::')
            elif frame.startswith('1::'):
                saw_connect = True
            elif frame.startswith('5:::'):
                ev = self._parse_event(frame[4:])
                if not ev:
                    continue
                ev_name = ev.get('name')
                if ev_name == 'joinProjectResponse':
                    ev_args = ev.get('args') or []
                    if ev_args and isinstance(ev_args[0], dict) and isinstance(ev_args[0].get('project'), dict):
                        payload = ev_args[0]
                        perms = str(payload.get('permissionsLevel', ''))
                        self._initial_project = (payload['project'], perms)
                        break
                    raise WorkspaceError('Overleaf joinProjectResponse did not contain project metadata.')
                if ev_name == 'connectionAccepted':
                    break
                if ev_name in ('connectionRejected', 'forceDisconnect', 'joinProjectError'):
                    raise WorkspaceError('Overleaf real-time connection rejected; re-authenticate with overleaf login --online.')
            elif frame.startswith('7:::'):
                raise WorkspaceError('Overleaf real-time server returned an error frame.')
        self.ws.settimeout(self.timeout)

    def close(self) -> None:
        if self.ws is not None:
            try:
                self.ws.send('0::')
            except Exception:
                pass
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None

    def __enter__(self) -> 'OverleafSocket':
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @staticmethod
    def _parse_event(raw: str) -> dict[str, Any] | None:
        try:
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None

    def emit_ack(self, name: str, args: list[Any], *, accept_event: str | None = None) -> list[Any]:
        require(self.ws is not None, 'Overleaf WebSocket is not connected.')
        self._msg_id += 1
        mid = self._msg_id
        payload = json.dumps({'name': name, 'args': args}, separators=(',', ':'))
        self.ws.send(f'5:{mid}+::{payload}')
        deadline = time.monotonic() + self.timeout
        ack_prefix = f'6:::{mid}+'
        while time.monotonic() < deadline:
            self.ws.settimeout(max(0.2, deadline - time.monotonic()))
            try:
                frame = self.ws.recv()
            except Exception as exc:
                raise WorkspaceError(f'Timed out waiting for Overleaf ACK on {name}.') from exc
            if not isinstance(frame, str):
                continue
            if frame.startswith('2::'):
                self.ws.send('2::')
                continue
            if frame.startswith(ack_prefix):
                raw_args = frame[len(ack_prefix):]
                parsed = json.loads(raw_args) if raw_args else []
                require(isinstance(parsed, list), f'Unexpected ACK format for {name}.')
                if parsed and parsed[0]:
                    err = parsed[0]
                    detail = err.get('message', str(err)) if isinstance(err, dict) else str(err)
                    raise WorkspaceError(f'Overleaf real-time {name} failed: {detail}')
                return parsed[1:] if len(parsed) > 1 else []
            if frame == f'6:::{mid}':
                return []
            if frame.startswith('5:::'):
                ev = self._parse_event(frame[4:])
                if ev:
                    if ev.get('name') in ('otUpdateError', 'forceDisconnect', 'connectionRejected'):
                        raise WorkspaceError(f'Overleaf real-time rejected operation ({ev.get("name")}).')
                    if accept_event and ev.get('name') == accept_event:
                        return ev.get('args', [])
            if frame.startswith('7:::'):
                raise WorkspaceError(f'Overleaf real-time error during {name}.')
        raise WorkspaceError(f'Timed out waiting for Overleaf ACK on {name}.')

    def join_project(self) -> tuple[dict[str, Any], str]:
        if self._initial_project is not None:
            return self._initial_project
        res = self.emit_ack('joinProject', [{'project_id': self.project_id}])
        require(len(res) >= 1 and isinstance(res[0], dict), 'Overleaf joinProject did not return project metadata.')
        permissions = str(res[1]) if len(res) >= 2 else ''
        return res[0], permissions

    def join_doc(self, doc_id: str) -> tuple[list[str], int]:
        res = self.emit_ack('joinDoc', [doc_id, {'encodeRanges': True}])
        require(len(res) >= 2 and isinstance(res[0], list) and isinstance(res[1], int),
                f'Overleaf joinDoc returned malformed response for doc {doc_id}.')
        return [decode_overleaf_doc_line(str(line)) for line in res[0]], int(res[1])

    def leave_doc(self, doc_id: str) -> None:
        try:
            self.emit_ack('leaveDoc', [doc_id])
        except Exception:
            pass

    def apply_ot_update(self, doc_id: str, version: int, ops: list[dict[str, Any]]) -> None:
        if not ops:
            return
        update = {'doc': doc_id, 'op': ops, 'v': version}
        self.emit_ack('applyOtUpdate', [doc_id, update], accept_event='otUpdateApplied')


# ---------------------------------------------------------------------------
# Session persistence helpers
# ---------------------------------------------------------------------------

def save_session(store: Store, session_data: dict[str, Any]) -> Path:
    path = safe_path(store.root, SESSION_FILE, governed=False)
    # Never persist passwords or raw credential headers.
    sanitized = {
        'version': 1,
        'server': _normalize_server(session_data['server']),
        'logged_in_at': session_data.get('logged_in_at', now()),
        'user_email': session_data.get('user_email', ''),
        'cookies': session_data.get('cookies', []),
    }
    atomic_write(path, pretty(sanitized))
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def load_session(store: Store, expected_server: str) -> CEHttpSession:
    path = safe_path(store.root, SESSION_FILE, governed=False)
    require(path.is_file(), 'No Overleaf CE session saved; run `rw overleaf login --online` first.')
    data = json.loads(read_text(path))
    expected = _normalize_server(expected_server)
    require(data.get('server') == expected,
            'Saved Overleaf CE session belongs to another server; run `rw overleaf login --online`.')
    cookies = data.get('cookies')
    require(isinstance(cookies, list) and len(cookies) > 0, 'Saved Overleaf CE session is empty; log in again.')
    return CEHttpSession(expected, cookies=cookies)


def clear_session(store: Store) -> dict[str, Any]:
    path = safe_path(store.root, SESSION_FILE, governed=False)
    existed = path.exists()
    path.unlink(missing_ok=True)
    return {'logged_out': True, 'session_removed': existed, 'remote_unchanged': True}


def login_ce(
    store: Store,
    server: str,
    *,
    online: bool = False,
    email: str | None = None,
    password: str | None = None,
    cookie: str | None = None,
) -> dict[str, Any]:
    require(online, 'Overleaf CE login requires --online.')
    norm = _normalize_server(server)
    session = CEHttpSession(norm)
    if cookie:
        saved = session.login_with_cookie(cookie)
        method = 'cookie'
    else:
        require(bool(email) and bool(password), 'Provide email and password (or cookie) to log into Overleaf CE.')
        saved = session.login(email, password)
        method = 'password'
    save_session(store, saved)
    return {
        'authenticated': True,
        'server': norm,
        'method': method,
        'user_email': saved.get('user_email') or (email or ''),
        'logged_in_at': saved['logged_in_at'],
        'session_file': SESSION_FILE,
        'password_stored': False,
    }


def list_ce_projects(store: Store, server: str, *, online: bool = False) -> dict[str, Any]:
    require(online, 'Listing Overleaf CE projects requires --online.')
    session = load_session(store, server)
    projects = session.list_projects()
    return {'server': session.server, 'count': len(projects), 'projects': projects}


def create_ce_project(store: Store, server: str, name: str, *, online: bool = False, approve: bool = False) -> dict[str, Any]:
    require(online, 'Creating an Overleaf CE project requires --online.')
    if not approve:
        return {'created': False, 'server': _normalize_server(server), 'name': name.strip(),
                'note': 'Preview only; pass --approve to create a new remote Overleaf CE project.'}
    session = load_session(store, server)
    return session.create_project(name)


# ---------------------------------------------------------------------------
# Built-in CETransport implementing the same read()/push() contract as GitTransport
# ---------------------------------------------------------------------------

def _snapshot_digest(files: dict[str, bytes]) -> str:
    return sha(pretty({k: sha(v) for k, v in sorted(files.items())}).encode('utf-8'))[:40]


class CETransport:
    """Native Overleaf CE transport compatible with overleaf.synchronize() / recover_sync()."""

    def __init__(self, store: Store, c: dict[str, Any], *, session: CEHttpSession | None = None):
        from .overleaf import managed
        self.store = store
        self.c = c
        self._managed = managed
        self.server = _normalize_server(c['server'])
        self.project_id = c['project_id']
        self.session = session or load_session(store, self.server)
        self.last_tree: ProjectTree | None = None
        self.last_permissions: str = ''

    def _read_tree_and_files(self, sock: OverleafSocket) -> tuple[ProjectTree, dict[str, bytes], str]:
        project, perms = sock.join_project()
        self.last_permissions = perms
        tree = flatten_project(project)
        self.last_tree = tree
        values: dict[str, bytes] = {}
        total = 0

        for rel, doc_id in sorted(tree.docs.items()):
            if not self._managed(rel):
                continue
            lines, _ = sock.join_doc(doc_id)
            sock.leave_doc(doc_id)
            data = '\n'.join(lines).encode('utf-8')
            total += len(data)
            require(len(data) <= MAX_DOWNLOAD and total <= MAX_EXPANDED and len(values) < MAX_FILES,
                    'Remote Overleaf project exceeds safe size limits.')
            values[rel] = data

        for rel, file_id in sorted(tree.files.items()):
            if not self._managed(rel):
                continue
            status, _, _, data = self.session.request(
                'GET',
                f'/project/{self.project_id}/file/{file_id}',
                headers={'Referer': f'{self.server}/project/{self.project_id}'},
                max_bytes=MAX_DOWNLOAD,
            )
            require(status == 200, f'Failed to download remote file {rel} (HTTP {status}).')
            total += len(data)
            require(len(data) <= MAX_DOWNLOAD and total <= MAX_EXPANDED and len(values) < MAX_FILES,
                    'Remote Overleaf project exceeds safe size limits.')
            values[rel] = data

        return tree, values, _snapshot_digest(values)

    def read(self) -> tuple[dict[str, bytes], str]:
        self.session.refresh_project_csrf(self.project_id)
        with OverleafSocket(self.session, self.project_id) as sock:
            _, values, commit = self._read_tree_and_files(sock)
        return values, commit

    def _ensure_folder(self, tree: ProjectTree, folder_path: str) -> str:
        if not folder_path or folder_path == '.':
            return tree.root_folder_id
        if folder_path in tree.folders:
            return tree.folders[folder_path]
        parts = folder_path.split('/')
        current = ''
        parent_id = tree.root_folder_id
        for part in parts:
            current = f'{current}/{part}' if current else part
            if current in tree.folders:
                parent_id = tree.folders[current]
                continue
            status, _, _, body = self.session.request(
                'POST',
                f'/project/{self.project_id}/folder',
                json_body={'parent_folder_id': parent_id, 'name': part},
                headers={
                    'X-Csrf-Token': self.session.csrf or '',
                    'Referer': f'{self.server}/project/{self.project_id}',
                },
            )
            require(status in (200, 201), f'Failed to create remote folder {current} (HTTP {status}).')
            created = json.loads(body.decode('utf-8'))
            new_id = str(created['_id'])
            tree.folders[current] = new_id
            parent_id = new_id
        return parent_id

    def _create_doc(self, parent_id: str, name: str) -> str:
        status, _, _, body = self.session.request(
            'POST',
            f'/project/{self.project_id}/doc',
            json_body={'parent_folder_id': parent_id, 'name': name},
            headers={
                'X-Csrf-Token': self.session.csrf or '',
                'Referer': f'{self.server}/project/{self.project_id}',
            },
        )
        require(status in (200, 201), f'Failed to create remote doc {name} (HTTP {status}).')
        created = json.loads(body.decode('utf-8'))
        return str(created['_id'])

    def _upload_file(self, parent_id: str, name: str, data: bytes) -> str:
        mime = mimetypes.guess_type(name)[0] or 'application/octet-stream'
        body, ctype = encode_multipart(
            {'relativePath': 'null', 'name': name, 'type': mime},
            'qqfile',
            name,
            data,
            mime,
        )
        q = urllib.parse.urlencode({'folder_id': parent_id, 'qqfilename': name})
        status, _, _, resp_body = self.session.request(
            'POST',
            f'/project/{self.project_id}/upload?{q}',
            data=body,
            headers={
                'Content-Type': ctype,
                'X-Csrf-Token': self.session.csrf or '',
                'Referer': f'{self.server}/project/{self.project_id}',
            },
        )
        require(status in (200, 201), f'Failed to upload remote file {name} (HTTP {status}).')
        parsed = json.loads(resp_body.decode('utf-8'))
        require(parsed.get('success', True) is not False, f'Overleaf rejected upload of {name}.')
        return str(parsed.get('entity_id', ''))

    def _delete_entity(self, kind: str, entity_id: str, rel: str) -> None:
        require(kind in ('doc', 'file', 'folder'), 'Invalid Overleaf entity kind.')
        status, _, _, _ = self.session.request(
            'DELETE',
            f'/project/{self.project_id}/{kind}/{entity_id}',
            headers={
                'X-Csrf-Token': self.session.csrf or '',
                'Referer': f'{self.server}/project/{self.project_id}',
            },
        )
        require(status in (200, 204), f'Failed to delete remote {kind} {rel} (HTTP {status}).')

    def push(self, files: dict[str, bytes], parent: str) -> str:
        self.session.refresh_project_csrf(self.project_id)
        for name in files:
            require(self._managed(name), 'Unmanaged upload path: ' + name)
        with OverleafSocket(self.session, self.project_id) as sock:
            tree, live_remote, live_commit = self._read_tree_and_files(sock)
            require(live_commit == parent, 'Remote Overleaf project changed after preview; rerun sync.')

            # 1. Additions & modifications
            for rel in sorted(files):
                new_bytes = files[rel]
                if live_remote.get(rel) == new_bytes:
                    continue
                folder_rel = '' if '/' not in rel else rel.rsplit('/', 1)[0]
                filename = rel.rsplit('/', 1)[-1]
                parent_id = self._ensure_folder(tree, folder_rel)

                if rel in tree.docs:
                    new_text = new_bytes.decode('utf-8').replace('\r\n', '\n')
                    doc_id = tree.docs[rel]
                    lines, version = sock.join_doc(doc_id)
                    ops = compute_ot_ops('\n'.join(lines), new_text)
                    if ops:
                        sock.apply_ot_update(doc_id, version, ops)
                    sock.leave_doc(doc_id)
                elif rel in tree.files:
                    new_id = self._upload_file(parent_id, filename, new_bytes)
                    if new_id:
                        tree.files[rel] = new_id
                elif is_text_doc(rel, new_bytes):
                    doc_id = self._create_doc(parent_id, filename)
                    tree.docs[rel] = doc_id
                    new_text = new_bytes.decode('utf-8').replace('\r\n', '\n')
                    lines, version = sock.join_doc(doc_id)
                    ops = compute_ot_ops('\n'.join(lines), new_text)
                    if ops:
                        sock.apply_ot_update(doc_id, version, ops)
                    sock.leave_doc(doc_id)
                else:
                    file_id = self._upload_file(parent_id, filename, new_bytes)
                    if file_id:
                        tree.files[rel] = file_id

            # 2. Deletions (only reached when allow_deletions=True in synchronize)
            for rel in sorted(set(live_remote) - set(files)):
                if rel in tree.docs:
                    self._delete_entity('doc', tree.docs[rel], rel)
                elif rel in tree.files:
                    self._delete_entity('file', tree.files[rel], rel)

        # 3. Re-read via a fresh real-time join to verify what Overleaf actually holds
        with OverleafSocket(self.session, self.project_id) as sock2:
            _, after_remote, after_commit = self._read_tree_and_files(sock2)
        # Update expected canonical bytes for any LF-normalized text docs.
        for rel in list(files):
            if rel in after_remote:
                files[rel] = after_remote[rel]
        return after_commit

    def compile_remote(self, *, root_doc: str | None = None, output_dir: Path | None = None) -> dict[str, Any]:
        self.session.refresh_project_csrf(self.project_id)
        with OverleafSocket(self.session, self.project_id) as sock:
            project, _ = sock.join_project()
            tree = flatten_project(project)
        root_doc_id = tree.root_doc_id
        resolved_main = None
        if root_doc:
            require(root_doc in tree.docs, f'Root doc not found on Overleaf: {root_doc}')
            root_doc_id = tree.docs[root_doc]
            resolved_main = root_doc
        else:
            for path, did in tree.docs.items():
                if did == root_doc_id:
                    resolved_main = path
                    break
        require(bool(root_doc_id), 'Could not determine rootDoc_id for remote compile.')

        status, _, _, body = self.session.request(
            'POST',
            f'/project/{self.project_id}/compile',
            json_body={
                'rootDoc_id': root_doc_id,
                'draft': False,
                'check': 'silent',
                'incrementalCompilesEnabled': True,
            },
            headers={
                'X-Csrf-Token': self.session.csrf or '',
                'Referer': f'{self.server}/project/{self.project_id}',
            },
            timeout=120,
        )
        require(status == 200, f'Remote Overleaf compile request failed (HTTP {status}).')
        result = json.loads(body.decode('utf-8'))
        compile_status = str(result.get('status', 'unknown'))
        output_files = result.get('outputFiles', []) or []

        build_id = identifier('OLBUILD')
        dest = output_dir or safe_path(self.store.root, f'.rw/builds/{build_id}', governed=False)
        dest.mkdir(parents=True, exist_ok=True)
        saved_pdf = None
        saved_log = None
        downloaded = []
        for item in output_files:
            url_path = item.get('url', '')
            out_path = str(item.get('path', ''))
            ftype = item.get('type', '')
            is_main_pdf = ftype == 'pdf' and out_path == 'output.pdf'
            is_main_log = ftype == 'log' and out_path == 'output.log'
            if (is_main_pdf or is_main_log) and isinstance(url_path, str) and url_path.startswith('/'):
                st, _, _, fbytes = self.session.request(
                    'GET',
                    url_path,
                    headers={'Referer': f'{self.server}/project/{self.project_id}'},
                    timeout=60,
                    max_bytes=MAX_DOWNLOAD,
                )
                if st == 200:
                    fname = 'output.pdf' if is_main_pdf else 'output.log'
                    target = dest / fname
                    target.write_bytes(fbytes)
                    downloaded.append({'type': ftype, 'remote_path': out_path, 'local_path': str(target), 'bytes': len(fbytes)})
                    if is_main_pdf:
                        saved_pdf = str(target)
                    elif is_main_log:
                        saved_log = str(target)
        return {
            'build_id': build_id,
            'compiled': compile_status == 'success' and saved_pdf is not None,
            'status': compile_status,
            'server': self.server,
            'project_id': self.project_id,
            'root_doc': resolved_main,
            'compiler': tree.compiler,
            'pdf': saved_pdf,
            'log': saved_log,
            'downloaded': downloaded,
        }


# ---------------------------------------------------------------------------
# Built-in one-shot live connectivity verification (read-only or roundtrip)
# ---------------------------------------------------------------------------

def verify_ce(
    store: Store,
    c: dict[str, Any],
    *,
    online: bool = False,
    roundtrip: bool = False,
    approve: bool = False,
    main: str | None = None,
    transport: CETransport | None = None,
) -> dict[str, Any]:
    """Verify real Overleaf CE connectivity directly (read-only or binary roundtrip probe)."""
    require(online, 'Overleaf CE verification requires --online.')
    require(c.get('mode') == 'ce', 'Built-in CE verification applies only to mode=ce configurations.')
    if roundtrip:
        require(approve, 'Roundtrip probe writes and deletes a temporary probe file on Overleaf; pass --approve.')

    folder = safe_path(store.root, c['directory'])
    local_before = tree_bytes(folder)
    before_hashes = {k: sha(v) for k, v in sorted(local_before.items())}

    ch = transport or CETransport(store, c)
    ch.session.refresh_project_csrf(ch.project_id)
    report: dict[str, Any] = {
        'version': 1,
        'transport': 'aiworkspace.builtin.ce',
        'server': ch.server,
        'project_id': ch.project_id,
        'directory': c['directory'],
        'mode': 'roundtrip' if roundtrip else 'read',
        'checked_at': now(),
        'status': 'not_verified',
        'verified': False,
        'metadata_matched': False,
        'local_to_remote': False,
        'remote_to_local': False,
        'cleanup': False,
        'before_hashes': before_hashes,
        'after_hashes': {},
    }

    with OverleafSocket(ch.session, ch.project_id) as sock:
        project, perms = sock.join_project()
        tree = flatten_project(project)
        require(tree.project_id == ch.project_id, 'Joined Overleaf project ID mismatch.')
        report['project_name'] = tree.name
        report['permissions'] = perms
        report['compiler'] = tree.compiler
        report['remote_docs'] = len(tree.docs)
        report['remote_files'] = len(tree.files)
        report['metadata_matched'] = True

        # Determine main .tex file to verify read path
        target_main = main
        if not target_main and tree.root_doc_id:
            for path, did in tree.docs.items():
                if did == tree.root_doc_id:
                    target_main = path
                    break
        if not target_main:
            tex_docs = sorted(p for p in tree.docs if p.endswith('.tex'))
            target_main = tex_docs[0] if tex_docs else None
        report['main'] = target_main
        if target_main and target_main in tree.docs:
            lines, version = sock.join_doc(tree.docs[target_main])
            sock.leave_doc(tree.docs[target_main])
            remote_main_bytes = '\n'.join(lines).encode('utf-8')
            report['remote_main_sha256'] = sha(remote_main_bytes)
            report['remote_main_version'] = version
            if target_main in local_before:
                report['local_main_matches'] = (sha(local_before[target_main]) == report['remote_main_sha256'])
        report['status'] = 'readable_via_ce'

        if roundtrip:
            probe_name = f'aiworkspace-sync-check-{uuid.uuid4().hex}.png'
            report['probe_file'] = probe_name
            payload_a = make_probe_png(secrets.token_hex(16))
            payload_b = make_probe_png(secrets.token_hex(16))
            require(probe_name not in tree.files and probe_name not in tree.docs, 'Probe filename collision.')
            try:
                def fresh_tree() -> ProjectTree:
                    with OverleafSocket(ch.session, ch.project_id) as fresh_sock:
                        p_fresh, _ = fresh_sock.join_project()
                        return flatten_project(p_fresh)

                # 1. Local -> Remote upload + verify server holds exact bytes A
                fid_a = ch._upload_file(tree.root_folder_id, probe_name, payload_a)
                tree2 = fresh_tree()
                require(probe_name in tree2.files, 'Uploaded probe file did not appear in remote Overleaf tree.')
                file_id = tree2.files[probe_name] or fid_a
                st, _, _, read_a = ch.session.request('GET', f'/project/{ch.project_id}/file/{file_id}')
                require(st == 200 and sha(read_a) == sha(payload_a), 'Remote probe bytes A mismatch.')
                report['local_to_remote'] = True

                # 2. Remote overwrite B -> Local read back & verify exact bytes B
                ch._upload_file(tree2.root_folder_id, probe_name, payload_b)
                tree3 = fresh_tree()
                require(probe_name in tree3.files, 'Updated probe file missing in remote tree.')
                file_id_b = tree3.files[probe_name]
                st2, _, _, read_b = ch.session.request('GET', f'/project/{ch.project_id}/file/{file_id_b}')
                require(st2 == 200 and sha(read_b) == sha(payload_b), 'Remote probe bytes B mismatch.')
                report['remote_to_local'] = True

                # 3. Cleanup & confirm gone from remote tree
                ch._delete_entity('file', file_id_b, probe_name)
                tree4 = fresh_tree()
                require(probe_name not in tree4.files, 'Probe file still present after deletion.')
                report['cleanup'] = True

                # 4. Confirm local manuscript files untouched during probe
                local_after = tree_bytes(folder)
                after_hashes = {k: sha(v) for k, v in sorted(local_after.items())}
                report['after_hashes'] = after_hashes
                require(before_hashes == after_hashes, 'Local manuscript changed during probe.')
                report['status'] = 'roundtrip_verified'
                report['verified'] = True
            except Exception as exc:
                report['status'] = 'incomplete'
                report['verified'] = False
                report['error'] = str(exc)

    report['finished_at'] = now()
    report['note'] = 'Time-scoped local observation via built-in Overleaf CE transport; does not certify future uptime or scientific readiness.'
    out_path = safe_path(store.root, VERIFY_FILE, governed=False)
    atomic_write(out_path, pretty(report))
    try:
        out_path.chmod(0o600)
    except OSError:
        pass
    return report
