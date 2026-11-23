"""Package the stable Windows app with verified file hashes and launch instructions."""
from pathlib import Path
import hashlib
import json
import os
import zipfile


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    app = root / 'dist/windows/PurwayGeotagger'
    info = json.loads((app / 'build-info.json').read_text(encoding='utf-8-sig'))
    if digest((app / 'PurwayGeotagger.exe').read_bytes()) != info['executable_sha256']:
        raise RuntimeError('EXE does not match its build record')
    embedded = json.loads((app / '_internal/build-info.json').read_text(encoding='utf-8-sig'))
    if embedded['build_id'] != info['build_id'] or embedded['input_sha256'] != info['input_sha256']:
        raise RuntimeError('Embedded identity does not match the build record')
    output = root / 'dist/share'
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"PurwayGeotagger-Windows-{info['app_version']}-{info['build_id']}.zip"
    if archive.exists():
        raise FileExistsError(archive)
    temporary = archive.with_suffix('.zip.partial')
    checksums = {}
    notes = f'''Purway Geotagger v{info['app_version']}
Build: {info['build_id']}
Built UTC: {info['built_at_utc']}
Base commit: {info['git_revision']}
Includes local source changes: {info['source_modified']}

Windows setup:
1. Right-click this ZIP and choose Extract All to a writable local folder.
2. Open PurwayGeotagger and double-click PurwayGeotagger.exe.
3. Optionally create a desktop shortcut to that EXE.

Keep _internal beside the EXE. Do not run inside the ZIP or copy only the EXE.
Python, Git Bash and a separate ExifTool installation are not required.
Configure input/output paths and settings on each workstation.
Verify the version/build in the window title; hover over the header version
for the base commit, build timestamp and fingerprint.
This is a Windows application, not a macOS package.
'''
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for path in sorted(p for p in app.rglob('*') if p.is_file()):
                name = 'PurwayGeotagger/' + path.relative_to(app).as_posix()
                data = path.read_bytes()
                checksums[name] = digest(data)
                z.writestr(name, data)
            z.writestr('START-HERE.txt', notes)
            z.writestr('PACKAGE-SHA256.json', json.dumps(checksums, indent=2))
        with zipfile.ZipFile(temporary) as z:
            if z.testzip() is not None:
                raise RuntimeError('ZIP integrity check failed')
            for name, checksum in checksums.items():
                if digest(z.read(name)) != checksum:
                    raise RuntimeError(f'ZIP content mismatch: {name}')
        os.replace(temporary, archive)
    finally:
        temporary.unlink(missing_ok=True)
    archive.with_suffix('.zip.sha256').write_text(digest(archive.read_bytes()) + '  ' + archive.name + '\n', encoding='utf-8')
    print(f'Verified {len(checksums)} files; {archive.stat().st_size / 1024**2:.1f} MiB: {archive}')


if __name__ == '__main__':
    main()
