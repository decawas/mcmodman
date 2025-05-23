# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['mcmodman.py', 'indexing.py', 'commons.py', 'modrinth.py', 'local.py', 'instance.py', 'cache.py'],
    pathex=[],
    binaries=[],
    datas=[('dataversion.json', 'dataversion.json'), ('config-template.toml', 'config-template.toml')],
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
    a.binaries,
    a.datas,
    [],
    name='mcmodman',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
