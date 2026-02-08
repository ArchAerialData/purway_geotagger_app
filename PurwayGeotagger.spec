# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import os


ROOT = Path(__file__).resolve().parent
VENDOR_ROOT = ROOT / "scripts" / "macos" / "vendor"
DEFAULT_BUNDLE_ID = "com.archaerial.purwaygeotagger"


def _latest_vendored_exiftool() -> tuple[Path | None, Path | None]:
    if not VENDOR_ROOT.exists():
        return None, None
    dirs = sorted(VENDOR_ROOT.glob("Image-ExifTool-*"))
    for directory in reversed(dirs):
        exiftool = directory / "exiftool"
        exiftool_lib = directory / "lib"
        if exiftool.is_file() and exiftool_lib.is_dir():
            return exiftool, exiftool_lib
    return None, None


def _resolve_exiftool() -> tuple[Path, Path]:
    override = os.environ.get("EXIFTOOL_PATH", "").strip()
    if override:
        exiftool = Path(override).expanduser().resolve()
        exiftool_lib = exiftool.parent / "lib"
        if not exiftool.is_file():
            raise SystemExit(f"EXIFTOOL_PATH does not exist: {exiftool}")
        if not exiftool_lib.is_dir():
            raise SystemExit(
                f"Portable ExifTool build requires adjacent lib directory: {exiftool_lib}"
            )
        return exiftool, exiftool_lib

    vendored_exiftool, vendored_lib = _latest_vendored_exiftool()
    if vendored_exiftool is None or vendored_lib is None:
        raise SystemExit(
            "No vendored ExifTool found. Expected scripts/macos/vendor/Image-ExifTool-*/ "
            "with exiftool and lib/."
        )
    return vendored_exiftool, vendored_lib


EXIFTOOL_PATH, EXIFTOOL_LIB = _resolve_exiftool()
BUNDLE_ID = os.environ.get("BUNDLE_ID", DEFAULT_BUNDLE_ID)

datas = [
    (str(ROOT / "config" / "default_templates.json"), "config"),
    (str(ROOT / "config" / "wind_templates"), "config/wind_templates"),
    (str(ROOT / "config" / "exiftool_config.txt"), "config"),
    (str(ROOT / "assets"), "assets"),
    (str(EXIFTOOL_LIB), "bin/lib"),
]
binaries = [(str(EXIFTOOL_PATH), "bin")]


a = Analysis(
    ["src/purway_geotagger/app.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PurwayGeotagger",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PurwayGeotagger",
)
app = BUNDLE(
    coll,
    name="PurwayGeotagger.app",
    icon=None,
    bundle_identifier=BUNDLE_ID,
)
