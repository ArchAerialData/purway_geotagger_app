"""Install, verify, launch and uninstall the exact distribution installer on Windows."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
import winreg

from smoke_test import smoke_test


def main() -> None:
    repo = Path(__file__).resolve().parents[2]
    source = repo / "dist/windows/PurwayGeotagger"
    info = json.loads((source / "build-info.json").read_text(encoding="utf-8-sig"))
    installer = repo / "dist/windows-installer" / (
        f"PurwayGeotagger-Setup-{info['app_version']}-{info['build_id']}.exe"
    )
    # Never replace an existing registered installation while testing.
    key = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{52F7D0A1-EC98-40C3-9BB1-3F8F5E3F9B1B}_is1"
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
            try:
                with winreg.OpenKey(hive, key, 0, winreg.KEY_READ | view):
                    raise RuntimeError("Existing registered app found; verify installer in a clean Windows account.")
            except FileNotFoundError:
                pass
    with tempfile.TemporaryDirectory(prefix="Purway installer test ") as folder:
        target = Path(folder) / "Installed App"
        try:
            subprocess.run([
                str(installer), "/CURRENTUSER", "/VERYSILENT", "/SUPPRESSMSGBOXES",
                "/NORESTART", "/NOICONS", "/TASKS=", f"/DIR={target}",
                f"/LOG={repo / 'build/windows-installer-install.log'}",
            ], check=True, timeout=180)
            count = 0
            for original in source.rglob("*"):
                if original.is_file():
                    installed = target / original.relative_to(source)
                    if hashlib.sha256(original.read_bytes()).digest() != hashlib.sha256(installed.read_bytes()).digest():
                        raise RuntimeError(f"Installed payload differs: {original.relative_to(source)}")
                    count += 1
            result = smoke_test(target)
            result.update(payload_files=count, installer_sha256=hashlib.sha256(installer.read_bytes()).hexdigest())
        finally:
            uninstaller = target / "unins000.exe"
            if uninstaller.exists():
                subprocess.run([
                    str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
                    f"/LOG={repo / 'build/windows-installer-uninstall.log'}",
                ], check=True, timeout=120)
                deadline = time.monotonic() + 15
                while uninstaller.exists() and time.monotonic() < deadline:
                    time.sleep(0.2)
                if uninstaller.exists():
                    raise RuntimeError("Test installation did not uninstall cleanly")
    result["uninstall_verified"] = True
    (repo / "build/windows-installer-smoke.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
