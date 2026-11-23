"""Verify and launch only the requested packaged Windows app, then close it cleanly."""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


def smoke_test(app: Path) -> dict:
    app = app.resolve()
    exe = app / "PurwayGeotagger.exe"
    info = json.loads((app / "build-info.json").read_text(encoding="utf-8-sig"))
    if hashlib.sha256(exe.read_bytes()).hexdigest().upper() != info["executable_sha256"]:
        raise RuntimeError("Executable hash mismatch")
    embedded = json.loads((app / "_internal/build-info.json").read_text(encoding="utf-8-sig"))
    if embedded["input_sha256"] != info["input_sha256"] or embedded["build_id"] != info["build_id"]:
        raise RuntimeError("Embedded build identity mismatch")
    version = subprocess.check_output([str(app / "_internal/bin/exiftool.exe"), "-ver"], text=True).strip()
    if version != info["exiftool_version"]:
        raise RuntimeError("Bundled ExifTool version mismatch")
    user32 = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    startup = subprocess.STARTUPINFO()
    startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    with tempfile.TemporaryDirectory(prefix="purway-smoke-") as profile:
        env = dict(os.environ, APPDATA=profile, LOCALAPPDATA=profile)
        for key in ("QT_QPA_PLATFORM", "PYTHONPATH", "PURWAY_EXIFTOOL_PATH"):
            env.pop(key, None)
        process = subprocess.Popen([str(exe)], cwd=profile, env=env, startupinfo=startup)
        windows = []

        @callback_type
        def inspect(hwnd, _):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == process.pid:
                title = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(hwnd, title, 512)
                if "Purway Geotagger" in title.value:
                    windows.append((hwnd, title.value))
            return True

        try:
            deadline = time.monotonic() + 30
            while not windows and process.poll() is None and time.monotonic() < deadline:
                user32.EnumWindows(inspect, 0)
                time.sleep(0.2)
            expected = f"v{info['app_version']}"
            if not windows or info["build_id"] not in windows[0][1] or expected not in windows[0][1]:
                raise RuntimeError(f"Packaged window/identity not verified; exit={process.poll()}, windows={windows}")
            for hwnd, _ in windows:
                user32.PostMessageW(hwnd, 0x0010, 0, 0)
            if process.wait(timeout=15) != 0:
                raise RuntimeError("Packaged app did not exit cleanly")
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
    return dict(build_id=info["build_id"], app_version=info["app_version"], title=windows[0][1], exit_code=0,
                executable_sha256=info["executable_sha256"], exiftool_version=version)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-dir", type=Path, default=Path("dist/windows/PurwayGeotagger"))
    parser.add_argument("--report", type=Path, default=Path("build/windows-smoke.json"))
    args = parser.parse_args()
    result = smoke_test(args.app_dir)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))
