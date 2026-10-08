#!/usr/bin/env python3
"""Read-only check that the README's architecture images and sources ship together."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
ASSET_DIR = 'aiworkspace/docs/architecture'
NAMES = ('architecture', 'workflow', 'maintenance')
NS = '{http://www.w3.org/2000/svg}'


def check(root: Path = ROOT) -> dict:
    errors: list[str] = []
    details: list[dict] = []
    readme = (root / 'README.md').read_text(encoding='utf-8')
    images = re.findall(r'!\[[^\]]*\]\(([^\s)]+)\)', readme)
    folder = root / ASSET_DIR
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    if 'sandbox:' in readme or '/mnt/data/' in readme:
        errors.append('README contains a conversation/local-only path.')
    expected_images = {f'{ASSET_DIR}/{name}.svg' for name in NAMES}
    if not expected_images.issubset(images):
        errors.append('README must embed all three architecture SVGs as images.')
    if len(images) != len(set(images)):
        errors.append('Duplicate image embed; inspect the README layout.')
    if readme.find(f'{ASSET_DIR}/architecture.svg') > readme.find('## 目录与职责'):
        errors.append('Place the architecture image before the directory reference.')
    for name in NAMES:
        entry: dict = {'name': name, 'embedded': f'{ASSET_DIR}/{name}.svg' in images}
        for suffix in ('mmd', 'svg'):
            path = folder / f'{name}.{suffix}'
            if not path.is_file() or path.is_symlink():
                errors.append('Missing/unsafe asset: ' + path.name)
                continue
            raw = path.read_bytes()
            actual = hashlib.sha256(raw).hexdigest()
            if manifest.get('files', {}).get(path.name) != actual:
                errors.append('Source/export hash mismatch: ' + path.name)
            entry[suffix + '_sha256'] = actual
            if suffix == 'mmd':
                if not raw.lstrip().startswith(b'flowchart '):
                    errors.append('Expected an editable Mermaid flowchart: ' + path.name)
                continue
            if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
                errors.append('SVG contains external-capable XML declarations: ' + path.name)
                continue
            svg = ET.fromstring(raw)
            if svg.tag != NS + 'svg' or not svg.get('viewBox'):
                errors.append('Invalid SVG root or missing viewBox: ' + path.name)
            if not list(svg.iter(NS + 'text')):
                errors.append('SVG labels must use portable text: ' + path.name)
            if svg.find(NS + 'title') is None or svg.find(NS + 'desc') is None:
                errors.append('Missing SVG text description: ' + path.name)
            for item in svg.iter():
                tag = item.tag.rsplit('}', 1)[-1]
                if tag in ('foreignObject', 'script', 'image', 'style', 'use'):
                    errors.append('Nonportable/active SVG element: ' + path.name + '/' + tag)
                for key, value in item.attrib.items():
                    local = key.rsplit('}', 1)[-1]
                    if local.lower().startswith('on') or local == 'href':
                        errors.append('Active/reference SVG attribute: ' + path.name)
                    if re.search(r'url\(\s*(?!#)[^)]', value):
                        errors.append('Nonlocal SVG resource: ' + path.name)
        details.append(entry)
    return {'passed': not errors, 'images': details, 'errors': errors,
            'boundary': 'File/reference checks only; no live GitHub UI, scientific or integration certification.'}


def main() -> int:
    try:
        result = check()
    except (OSError, ValueError, TypeError, ET.ParseError) as exc:
        result = {'passed': False, 'errors': [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
