"""Bounded publication downloads and archive handling. Never execute downloaded content."""
from __future__ import annotations
import hashlib
import ipaddress
import json
import os
import re
import shutil
import socket
import stat
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path, PurePosixPath
from .model import WorkspaceError, require
from .store import safe_path

MAX_DOWNLOAD = 32 * 1024 * 1024
MAX_FILES = 2000
MAX_EXPANDED = 96 * 1024 * 1024
SOURCE_EXTENSIONS = {'.tex', '.ltx', '.bib', '.cls', '.sty', '.bst', '.bbx', '.cbx', '.def', '.clo', '.cfg', '.fd', '.dtx', '.ins', '.txt', '.md', '.pdf', '.png', '.jpg', '.jpeg', '.eps', '.ps', '.svg', '.csv', '.dat', '.json', '.xml'}
GENERATED = {'.aux', '.log', '.out', '.fls', '.fdb_latexmk', '.synctex', '.gz', '.toc', '.blg', '.bcf', '.run.xml', '.bbl'}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def public_url(url: str, allowed_hosts: set[str], *, resolve: bool = True) -> str:
    """Exact host allowlist; HTTPS, no userinfo/query credentials, no private addresses."""
    require(isinstance(url, str) and len(url) < 4000 and not any(c in url for c in '\r\n\x00'), 'Invalid URL.')
    u = urllib.parse.urlsplit(url)
    require(u.scheme == 'https' and u.hostname in allowed_hosts and not u.username and not u.password, 'URL must use HTTPS and an explicitly allowed host.')
    require(u.port in (None, 443), 'Public template downloads require standard HTTPS.')
    require(not any(k.lower() in {'token','access_token','password','auth','key','secret'} for k, _ in urllib.parse.parse_qsl(u.query)), 'Do not put credentials in publication URLs.')
    if resolve:
        try:
            addresses = socket.getaddrinfo(u.hostname, 443, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise WorkspaceError('Cannot resolve public source host: ' + str(u.hostname)) from exc
        require(addresses and all(ipaddress.ip_address(x[4][0]).is_global for x in addresses), 'Private/network-local addresses are not publication download sources.')
    return urllib.parse.urlunsplit((u.scheme, u.netloc, u.path, u.query, ''))


class RedirectGuard(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts: set[str]):
        self.hosts, self.hops = hosts, []
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        require(len(self.hops) < 5, 'Too many redirects.')
        target = public_url(urllib.parse.urljoin(req.full_url, newurl), self.hosts)
        self.hops.append(target)
        return super().redirect_request(req, fp, code, msg, headers, target)


def download(url: str, hosts: set[str], *, online: bool, transport=None, limit: int = MAX_DOWNLOAD) -> tuple[bytes, dict]:
    require(online, 'Network download requires --online; use --archive/--sources-dir for offline material.')
    public_url(url, hosts, resolve=transport is None)
    if transport:
        payload, meta = transport(url)
        require(isinstance(payload, bytes) and len(payload) <= limit, 'Invalid/oversized transport response.')
        public_url(meta.get('url', url), hosts, resolve=False)
        return payload, {**meta, 'sha256': sha(payload)}
    redirects = RedirectGuard(hosts)
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'AIResearchWorkspace/0.3 (user-initiated source retrieval)', 'Accept': '*/*'})
        with urllib.request.build_opener(redirects).open(request, timeout=30) as response:
            final = public_url(response.url, hosts)
            body = response.read(limit + 1)
            require(len(body) <= limit, 'Download exceeds configured size limit.')
            return body, {'url': final, 'redirects': redirects.hops, 'content_type': response.headers.get('Content-Type', ''), 'sha256': sha(body)}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise WorkspaceError('Download failed; no successful source verification recorded: ' + urllib.parse.urlsplit(url).hostname) from exc


def archive_path(name: str) -> str:
    require(isinstance(name, str) and name and '\\' not in name and ':' not in name and not any(ord(c)<32 or ord(c)==127 for c in name), 'Unsafe archive path.')
    p = PurePosixPath(name)
    require(not p.is_absolute() and '..' not in p.parts and all(x not in ('', '.', '..') for x in name.split('/')), 'Archive traversal refused.')
    require(all(not x.endswith((' ', '.')) and not re.fullmatch(r'(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', x, re.I) for x in p.parts), 'Nonportable archive filename.')
    return p.as_posix()


def unpack(data: bytes) -> tuple[dict[str, bytes], list[str]]:
    """Return source files; preserve original ZIP separately, skip execution settings."""
    require(len(data) <= MAX_DOWNLOAD and zipfile.is_zipfile(BytesIO(data)), 'Expected a ZIP template, not an HTML login page.')
    files, skipped, seen = {}, [], set()
    try:
        with zipfile.ZipFile(BytesIO(data)) as z:
            infos = z.infolist()
            require(len(infos) <= MAX_FILES and sum(i.file_size for i in infos) <= MAX_EXPANDED, 'Archive expansion limit exceeded.')
            for item in infos:
                name = archive_path(item.filename.rstrip('/'))
                require(name.casefold() not in seen, 'Duplicate/case-colliding ZIP path: ' + name)
                seen.add(name.casefold())
                mode = item.external_attr >> 16
                require(stat.S_IFMT(mode) not in (stat.S_IFLNK, stat.S_IFCHR, stat.S_IFBLK, stat.S_IFIFO, stat.S_IFSOCK), 'Archive links/devices refused.')
                require(not item.flag_bits & 1, 'Encrypted ZIP files are unsupported.')
                if item.is_dir(): continue
                parts = PurePosixPath(name).parts
                if any(x.startswith('.') or x in {'__MACOSX','node_modules','__pycache__'} for x in parts) or (Path(name).suffix.lower() not in SOURCE_EXTENSIONS and Path(name).name not in {'LICENSE','README','COPYING'}):
                    skipped.append(name); continue
                require(item.file_size <= MAX_DOWNLOAD, 'Individual file is too large.')
                files[name] = z.read(item)
    except (zipfile.BadZipFile, RuntimeError) as exc:
        raise WorkspaceError('Corrupt or unsupported template ZIP.') from exc
    require(files and any(n.endswith('.tex') for n in files), 'No LaTeX source found in template.')
    # Strip one common archive wrapper while preserving all relative subpaths.
    heads = {PurePosixPath(p).parts[0] for p in files}
    if len(heads) == 1 and all(len(PurePosixPath(p).parts) > 1 for p in files):
        prefix = next(iter(heads)) + '/'
        files = {p[len(prefix):]: v for p, v in files.items()}
    return files, skipped


def tree_bytes(root: Path) -> dict[str, bytes]:
    require(root.is_dir() and not root.is_symlink(), 'Source tree is missing or linked.')
    out, total = {}, 0
    for p in sorted(root.rglob('*')):
        rel = p.relative_to(root).as_posix()
        require(not p.is_symlink(), 'Symlink in source tree: ' + rel)
        if not p.is_file(): continue
        if any(x.startswith('.') or x in {'__pycache__','node_modules','build'} for x in p.relative_to(root).parts): continue
        if p.suffix.lower() not in SOURCE_EXTENSIONS and p.name not in {'LICENSE','README','COPYING'}: continue
        data = p.read_bytes(); total += len(data)
        require(len(data) <= MAX_DOWNLOAD and total <= MAX_EXPANDED and len(out) < MAX_FILES, 'Source tree exceeds safe size limits.')
        out[archive_path(rel)] = data
    return out


def new_tree(root: Path, relative: str, files: dict[str, bytes]) -> Path:
    """Publish a fully staged new directory. Never overwrite an existing manuscript."""
    dest = safe_path(root, relative)
    require(not dest.exists(), 'Destination already exists; choose a new version: ' + relative)
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix='.rw-stage-', dir=dest.parent))
    try:
        for name, data in files.items():
            target = safe_path(temp, archive_path(name), governed=False)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        require(not dest.exists(), 'Destination appeared during preparation; nothing overwritten.')
        # rename of a nonempty directory cannot replace a nonempty user directory.
        temp.rename(dest)
    finally:
        if temp.exists(): shutil.rmtree(temp)
    return dest


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text, self.links, self.ignore = [], [], 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style','noscript'): self.ignore += 1
        d = dict(attrs)
        if tag == 'a' and d.get('href'): self.links.append(d['href'])
        if tag in ('p','div','li','h1','h2','h3','tr','br'): self.text.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script','style','noscript'): self.ignore = max(0, self.ignore - 1)
        if tag in ('p','div','li','h1','h2','h3','tr'): self.text.append('\n')
    def handle_data(self, text):
        if not self.ignore: self.text.append(text)
    def normalized(self):
        return '\n'.join(x for x in (' '.join(line.split()) for line in ''.join(self.text).splitlines()) if x)


def page_text(data: bytes, content_type: str = '') -> tuple[str, list[str]]:
    require(not data.startswith(b'%PDF'), 'PDF rule source needs a reviewed text extraction; keep original PDF and locator separately.')
    try: text = data.decode('utf-8-sig')
    except UnicodeError as exc: raise WorkspaceError('Source must be UTF-8; convert explicitly with provenance.') from exc
    if 'html' in content_type or re.search(r'<(?:html|body|!doctype)', text[:2000], re.I):
        p = Page(); p.feed(text); return p.normalized(), p.links
    return text, []
