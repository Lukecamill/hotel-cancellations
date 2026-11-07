"""Repair this checkout's local venv when macOS hides editable .pth files."""
from pathlib import Path
import sys
import sysconfig

root = Path(__file__).resolve().parents[1]
if Path(sys.prefix).resolve() != (root / '.venv').resolve():
    raise SystemExit('Run using this checkout’s .venv/bin/python.')
source = root / 'src/hotel_cancel'
link = Path(sysconfig.get_path('purelib')) / 'hotel_cancel'
if link.is_symlink():
    if link.resolve() != source:
        raise SystemExit(f'Refusing to replace a link to another source: {link}')
elif link.exists():
    raise SystemExit(f'Refusing to overwrite an existing installation: {link}')
else:
    import os
    link.symlink_to(os.path.relpath(source, link.parent), target_is_directory=True)
# Remove only the extra diagnostic path file created while investigating.
extra = link.parent / 'hotel_cancel_source.pth'
if extra.exists() and extra.read_text().strip() == str(root / 'src'):
    extra.unlink()
print(f'Local package link ready: {link} -> {link.readlink()}')
