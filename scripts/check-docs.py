#!/usr/bin/env python3
"""Check tracked JSON and simple inline Markdown file links; no network access."""
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit


def check(root: Path, paths: list[str]) -> list[str]:
    errors = []
    for name in paths:
        path = root / name
        if path.suffix == '.json':
            try:
                json.loads(path.read_text(encoding='utf-8'))
            except (ValueError, UnicodeError) as exc:
                errors.append(f'{name}: invalid JSON: {exc}')
        if path.suffix != '.md':
            continue
        # This checks inline targets, not heading anchors, reference-style links
        # or remote URLs. Do not present it as a complete Markdown validator.
        for target in re.findall(r'\]\(([^\s)]+)\)', path.read_text(encoding='utf-8')):
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            destination = path.parent / unquote(parsed.path)
            if not destination.exists():
                errors.append(f'{name}: missing local link target: {target}')
    return errors


if __name__ == '__main__':
    root = Path(__file__).resolve().parent.parent
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    errors = check(root, [name for name in names if name])
    for error in errors:
        print(error, file=sys.stderr)
    print(f'Document checks: {len(errors)} error(s)')
    raise SystemExit(bool(errors))
