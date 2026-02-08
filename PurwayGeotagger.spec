# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src/purway_geotagger/app.py'],
    pathex=['src'],
    binaries=[('/opt/homebrew/bin/exiftool', 'bin')],
    datas=[
        ('config/default_templates.json', 'config'),
        ('config/wind_templates', 'config/wind_templates'),
        ('assets', 'assets'),
    ],
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
    name='PurwayGeotagger',
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
    name='PurwayGeotagger',
)
app = BUNDLE(
    coll,
    name='PurwayGeotagger.app',
    icon=None,
    bundle_identifier='com.yourorg.PurwayGeotagger',
)
