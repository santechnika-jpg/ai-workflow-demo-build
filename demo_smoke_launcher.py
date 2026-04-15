from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


def bundle_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def load_cli_module(cli_path: Path):
    module_name = "reference_pre_run_validator_cli_v0_3_009_runtime"
    spec = importlib.util.spec_from_file_location(module_name, cli_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Nepavyko užkrauti CLI modulio: {cli_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="ai-workflow-demo",
        description="Windows no-install smoke test launcher for PASS and ERROR scenarios."
    )
    parser.add_argument(
        "mode",
        nargs="?",
        default="pass",
        choices=["pass", "error"],
        help="Smoke test mode: pass arba error",
    )
    args = parser.parse_args()

    root = bundle_root()
    cli_path = root / "reference_pre_run_validator_cli.py"
    runtime_path = root / "example_runtime_context.json"
    ruleset_path = root / "example_ruleset.json"

    cli_module = load_cli_module(cli_path)

    argv_backup = sys.argv[:]
    temp_path = None

    try:
        if args.mode == "pass":
            sys.argv = [
                str(cli_path),
                "--runtime-context", str(runtime_path),
                "--ruleset", str(ruleset_path),
                "--pretty",
            ]
            return int(cli_module.main())

        # error mode
        with runtime_path.open("r", encoding="utf-8") as fh:
            runtime = json.load(fh)
        runtime.pop("EXECUTION_ID", None)

        tmpdir = Path(tempfile.mkdtemp(prefix="ai_workflow_demo_"))
        temp_path = tmpdir / "temp_bad_runtime_context.json"
        temp_path.write_text(json.dumps(runtime, ensure_ascii=False, indent=2), encoding="utf-8")

        sys.argv = [
            str(cli_path),
            "--runtime-context", str(temp_path),
            "--ruleset", str(ruleset_path),
            "--pretty",
        ]
        return int(cli_module.main())

    finally:
        sys.argv = argv_backup
        if temp_path is not None:
            try:
                shutil.rmtree(temp_path.parent, ignore_errors=True)
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
