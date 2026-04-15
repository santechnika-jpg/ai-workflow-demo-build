from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parent
VALIDATOR_PATH = ROOT / "reference_pre_run_validator.py"
SCHEMAS_DIR = ROOT / "schemas"


@dataclass(frozen=True)
class CliStructuredError(Exception):
    error_code: str
    error_type: str
    field_path: str
    message: str

    def to_payload(self) -> dict:
        return {"error": asdict(self)}


def build_parser():
    parser = argparse.ArgumentParser(
        prog="reference-pre-run-validator-cli",
        description=(
            "CLI sluoksnis reference pre-run validatoriui su JSON Schema validacija "
            "ir stabiliu machine-readable klaidų modeliu."
        ),
    )
    parser.add_argument("--runtime-context", required=True, help="Kelias iki runtime_context JSON failo")
    parser.add_argument("--ruleset", required=True, help="Kelias iki ruleset JSON failo")
    parser.add_argument("--pretty", action="store_true", help="Gražiau suformatuoti JSON išvestį")
    return parser


def load_json(path: Path, label: str):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CliStructuredError(
            error_code="CLI_FILE_NOT_FOUND",
            error_type="file_not_found",
            field_path=label,
            message=f"Failas nerastas: {path}",
        ) from exc
    except json.JSONDecodeError as exc:
        raise CliStructuredError(
            error_code="CLI_INVALID_JSON",
            error_type="invalid_json",
            field_path=label,
            message=f"Neteisingas JSON formatas faile: {path}",
        ) from exc


def load_validator_module():
    module_name = "reference_pre_run_validator_v0_3_009_runtime"
    spec = importlib.util.spec_from_file_location(module_name, VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise CliStructuredError(
            error_code="CLI_VALIDATOR_IMPORT_ERROR",
            error_type="import_error",
            field_path="validator_module",
            message="Nepavyko užkrauti reference validatoriaus modulio",
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_schema(schema_name: str):
    schema_path = SCHEMAS_DIR / schema_name
    return load_json(schema_path, f"schemas.{schema_name}")


def format_json_path(label: str, parts: list) -> str:
    if not parts:
        return label
    out = label
    for part in parts:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out += f".{part}"
    return out


def extract_required_property(message: str) -> str | None:
    match = re.search(r"'([^']+)' is a required property", message)
    return match.group(1) if match else None


def extract_additional_property(message: str) -> str | None:
    match = re.search(r"'([^']+)' was unexpected", message)
    return match.group(1) if match else None


def make_schema_error_code(label: str) -> str:
    mapping = {
        "runtime_context": "RUNTIME_CONTEXT_SCHEMA_VALIDATION_ERROR",
        "ruleset": "RULESET_SCHEMA_VALIDATION_ERROR",
        "decision_output": "DECISION_OUTPUT_SCHEMA_VALIDATION_ERROR",
        "audit_trace": "AUDIT_TRACE_SCHEMA_VALIDATION_ERROR",
    }
    return mapping.get(label, "CLI_RUNTIME_ERROR")


def validate_against_schema(instance, schema_name: str, label: str):
    schema = load_schema(schema_name)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    if not errors:
        return

    first = errors[0]
    path_parts = list(first.path)
    field_path = format_json_path(label, path_parts)

    if first.validator == "required":
        missing = extract_required_property(first.message)
        if missing:
            field_path = f"{field_path}.{missing}" if field_path else missing
    elif first.validator == "additionalProperties":
        extra = extract_additional_property(first.message)
        if extra:
            field_path = f"{field_path}.{extra}" if field_path else extra

    raise CliStructuredError(
        error_code=make_schema_error_code(label),
        error_type="schema_validation_error",
        field_path=field_path,
        message=first.message,
    )


def emit_json(payload, pretty: bool) -> None:
    if pretty:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(payload, ensure_ascii=False))


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        validator_module = load_validator_module()

        runtime_context = load_json(Path(args.runtime_context), "runtime_context")
        ruleset = load_json(Path(args.ruleset), "ruleset")

        validate_against_schema(runtime_context, "runtime_context.schema.json", "runtime_context")
        validate_against_schema(ruleset, "ruleset.schema.json", "ruleset")

        result = validator_module.evaluate_rules(runtime_context, ruleset)

        validate_against_schema(result["decision_output"], "decision_output.schema.json", "decision_output")
        validate_against_schema(result["audit_trace"], "audit_trace.schema.json", "audit_trace")

        emit_json(result, args.pretty)
        return 0

    except CliStructuredError as exc:
        print(json.dumps(exc.to_payload(), ensure_ascii=False), file=sys.stderr)
        return 1
    except Exception as exc:
        payload = {
            "error": {
                "error_code": "CLI_RUNTIME_ERROR",
                "error_type": "runtime_error",
                "field_path": "$",
                "message": str(exc),
            }
        }
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
