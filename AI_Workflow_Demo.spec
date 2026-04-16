# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

block_cipher = None
root = Path.cwd()

datas = [
    (str(root / "reference_pre_run_validator.py"), "."),
    (str(root / "reference_pre_run_validator_cli.py"), "."),
    (str(root / "example_runtime_context.json"), "."),
    (str(root / "example_ruleset.json"), "."),
    (str(root / "runtime_context.schema.json"), "schemas"),
    (str(root / "ruleset.schema.json"), "schemas"),
    (str(root / "decision_output.schema.json"), "schemas"),
    (str(root / "audit_trace.schema.json"), "schemas"),
    (str(root / "error_output.schema.json"), "schemas"),
]

a = Analysis(
    ['demo_smoke_launcher.py'],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=['jsonschema'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AI_Workflow_Demo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
