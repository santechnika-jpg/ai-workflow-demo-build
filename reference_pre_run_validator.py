
"""
Reference pre-run validator for AI Workflow Control Tower MVP v0.3-002.

Changes from v0.3-001:
- Full DOC-002 schema gate before DOC-003 rule evaluation
- Required field enforcement
- Type validation
- Top-level unknown field rejection
- ISO 8601 UTC timestamp validation
- Non-empty validation for default v1 required arrays
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence
import json
import uuid


class ValidationError(ValueError):
    pass


REQUIRED_RUNTIME_CONTEXT_FIELDS_V1 = {
    "WORKFLOW_ID",
    "EXECUTION_ID",
    "WORKFLOW_VERSION",
    "EXECUTION_MODE",
    "REQUESTED_ACTION",
    "INPUT_ARTIFACTS",
    "REQUIRED_INVARIANTS",
    "ENVIRONMENT_TAG",
    "POLICY_SET_VERSION",
    "TIMESTAMP",
}

OPTIONAL_RUNTIME_CONTEXT_FIELDS_V1 = {
    "OPTIONAL_METADATA",
}

RUNTIME_CONTEXT_FIELDS_V1 = REQUIRED_RUNTIME_CONTEXT_FIELDS_V1 | OPTIONAL_RUNTIME_CONTEXT_FIELDS_V1

SUPPORTED_OPERATORS_V1 = {
    "exists",
    "equals",
    "not_equals",
    "in_list",
    "not_empty",
}

SEVERITY_MODEL_V1 = {
    "BLOCKING",
    "WARNING",
}

ALLOWED_RULE_FIELDS_V1 = {
    "rule_id",
    "rule_name",
    "description",
    "target_field",
    "operator",
    "expected_value",
    "severity",
    "failure_message",
    "enabled",
}


@dataclass(frozen=True)
class Rule:
    rule_id: str
    rule_name: str
    description: str
    target_field: str
    operator: str
    expected_value: Any
    severity: str
    failure_message: str
    enabled: bool

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rule":
        unknown = set(data.keys()) - ALLOWED_RULE_FIELDS_V1
        missing = ALLOWED_RULE_FIELDS_V1 - set(data.keys())
        if unknown:
            raise ValidationError(f"Unknown rule fields: {sorted(unknown)}")
        if missing:
            raise ValidationError(f"Missing rule fields: {sorted(missing)}")

        if data["operator"] not in SUPPORTED_OPERATORS_V1:
            raise ValidationError(f"Unsupported operator: {data['operator']}")
        if data["severity"] not in SEVERITY_MODEL_V1:
            raise ValidationError(f"Unsupported severity: {data['severity']}")
        if data["target_field"] not in RUNTIME_CONTEXT_FIELDS_V1:
            raise ValidationError(
                f"Unsupported target_field for Runtime Context Schema v1: {data['target_field']}"
            )
        if not isinstance(data["enabled"], bool):
            raise ValidationError("enabled must be boolean")
        if not isinstance(data["rule_id"], str) or not data["rule_id"]:
            raise ValidationError("rule_id must be non-empty string")
        if not isinstance(data["rule_name"], str) or not data["rule_name"]:
            raise ValidationError("rule_name must be non-empty string")
        if not isinstance(data["description"], str):
            raise ValidationError("description must be string")
        if not isinstance(data["target_field"], str) or not data["target_field"]:
            raise ValidationError("target_field must be non-empty string")
        if not isinstance(data["failure_message"], str) or not data["failure_message"]:
            raise ValidationError("failure_message must be non-empty string")

        if data["operator"] == "in_list" and not isinstance(data["expected_value"], list):
            raise ValidationError("expected_value must be a list when operator is in_list")

        return cls(**data)


@dataclass(frozen=True)
class Violation:
    rule_id: str
    rule_name: str
    severity: str
    failure_message: str

    @classmethod
    def from_rule(cls, rule: Rule) -> "Violation":
        return cls(
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            severity=rule.severity,
            failure_message=rule.failure_message,
        )


@dataclass(frozen=True)
class DecisionOutput:
    decision: str
    violated_rules: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    evaluation_timestamp: str


@dataclass(frozen=True)
class AuditTrace:
    trace_id: str
    workflow_id: str
    execution_id: str
    decision: str
    violated_rules: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    evaluation_timestamp: str


def current_utc_iso8601() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def field_exists(runtime_context: Dict[str, Any], field_name: str) -> bool:
    return field_name in runtime_context


def is_not_empty(value: Any) -> bool:
    return value is not None and value != "" and value != []


def parse_iso8601_utc(value: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValidationError("TIMESTAMP must be non-empty ISO 8601 UTC string")
    if not value.endswith("Z"):
        raise ValidationError("TIMESTAMP must end with 'Z'")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError("TIMESTAMP must be valid ISO 8601 UTC string") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValidationError("TIMESTAMP must be UTC")


def validate_runtime_context_schema_v1(runtime_context: Dict[str, Any]) -> None:
    if not isinstance(runtime_context, dict):
        raise ValidationError("runtime_context must be an object/dict")

    unknown_top_level_fields = set(runtime_context.keys()) - RUNTIME_CONTEXT_FIELDS_V1
    if unknown_top_level_fields:
        raise ValidationError(f"Unknown top-level runtime_context fields: {sorted(unknown_top_level_fields)}")

    missing_required_fields = REQUIRED_RUNTIME_CONTEXT_FIELDS_V1 - set(runtime_context.keys())
    if missing_required_fields:
        raise ValidationError(f"Missing required runtime_context fields: {sorted(missing_required_fields)}")

    if not isinstance(runtime_context["WORKFLOW_ID"], str) or runtime_context["WORKFLOW_ID"] == "":
        raise ValidationError("WORKFLOW_ID must be non-empty string")

    if not isinstance(runtime_context["EXECUTION_ID"], str) or runtime_context["EXECUTION_ID"] == "":
        raise ValidationError("EXECUTION_ID must be non-empty string")

    if not isinstance(runtime_context["WORKFLOW_VERSION"], str) or runtime_context["WORKFLOW_VERSION"] == "":
        raise ValidationError("WORKFLOW_VERSION must be non-empty string")

    if not isinstance(runtime_context["EXECUTION_MODE"], str) or runtime_context["EXECUTION_MODE"] == "":
        raise ValidationError("EXECUTION_MODE must be non-empty string")

    if not isinstance(runtime_context["REQUESTED_ACTION"], str) or runtime_context["REQUESTED_ACTION"] == "":
        raise ValidationError("REQUESTED_ACTION must be non-empty string")

    if not isinstance(runtime_context["INPUT_ARTIFACTS"], list):
        raise ValidationError("INPUT_ARTIFACTS must be array/list")
    if runtime_context["INPUT_ARTIFACTS"] == []:
        raise ValidationError("INPUT_ARTIFACTS must be non-empty in v1 default schema gate")
    if not all(isinstance(item, dict) for item in runtime_context["INPUT_ARTIFACTS"]):
        raise ValidationError("INPUT_ARTIFACTS items must be objects/dicts")

    if not isinstance(runtime_context["REQUIRED_INVARIANTS"], list):
        raise ValidationError("REQUIRED_INVARIANTS must be array/list")
    if runtime_context["REQUIRED_INVARIANTS"] == []:
        raise ValidationError("REQUIRED_INVARIANTS must be non-empty in v1 default schema gate")
    if not all(isinstance(item, str) and item != "" for item in runtime_context["REQUIRED_INVARIANTS"]):
        raise ValidationError("REQUIRED_INVARIANTS items must be non-empty strings")

    if not isinstance(runtime_context["ENVIRONMENT_TAG"], str) or runtime_context["ENVIRONMENT_TAG"] == "":
        raise ValidationError("ENVIRONMENT_TAG must be non-empty string")

    if not isinstance(runtime_context["POLICY_SET_VERSION"], str) or runtime_context["POLICY_SET_VERSION"] == "":
        raise ValidationError("POLICY_SET_VERSION must be non-empty string")

    parse_iso8601_utc(runtime_context["TIMESTAMP"])

    if "OPTIONAL_METADATA" in runtime_context and not isinstance(runtime_context["OPTIONAL_METADATA"], dict):
        raise ValidationError("OPTIONAL_METADATA must be object/dict when provided")


def evaluate_rule(rule: Rule, runtime_context: Dict[str, Any]) -> bool:
    exists = field_exists(runtime_context, rule.target_field)

    if rule.operator == "exists":
        return exists

    if not exists:
        return False

    value = runtime_context[rule.target_field]

    if rule.operator == "not_empty":
        return is_not_empty(value)

    if rule.operator == "equals":
        return value == rule.expected_value

    if rule.operator == "not_equals":
        return value != rule.expected_value

    if rule.operator == "in_list":
        return value in rule.expected_value

    raise ValidationError(f"Unsupported operator at evaluation time: {rule.operator}")


def load_active_rules(rules_registry: Sequence[Dict[str, Any]]) -> List[Rule]:
    if not isinstance(rules_registry, Sequence) or isinstance(rules_registry, (str, bytes, bytearray)):
        raise ValidationError("rules_registry must be a sequence of rule objects")

    parsed: List[Rule] = []
    for raw_rule in rules_registry:
        if not isinstance(raw_rule, dict):
            raise ValidationError("Each rule must be an object/dict")
        rule = Rule.from_dict(raw_rule)
        if rule.enabled:
            parsed.append(rule)
    return parsed


def evaluate_rules(
    runtime_context: Dict[str, Any],
    rules_registry: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    validate_runtime_context_schema_v1(runtime_context)
    active_rules = load_active_rules(rules_registry)

    violated_rules: List[Violation] = []
    warnings: List[Violation] = []

    for rule in active_rules:
        result = evaluate_rule(rule, runtime_context)
        if result is False:
            violation = Violation.from_rule(rule)
            violated_rules.append(violation)
            if rule.severity == "WARNING":
                warnings.append(violation)

    blocking_found = any(item.severity == "BLOCKING" for item in violated_rules)
    decision = "FAIL" if blocking_found else "PASS"
    evaluation_timestamp = current_utc_iso8601()

    decision_output = DecisionOutput(
        decision=decision,
        violated_rules=[asdict(v) for v in violated_rules],
        warnings=[asdict(v) for v in warnings],
        evaluation_timestamp=evaluation_timestamp,
    )

    trace_id = f"TRACE-{uuid.uuid4()}"
    audit_trace = AuditTrace(
        trace_id=trace_id,
        workflow_id=str(runtime_context["WORKFLOW_ID"]),
        execution_id=str(runtime_context["EXECUTION_ID"]),
        decision=decision,
        violated_rules=[asdict(v) for v in violated_rules],
        warnings=[asdict(v) for v in warnings],
        evaluation_timestamp=evaluation_timestamp,
    )

    return {
        "decision_output": asdict(decision_output),
        "audit_trace": asdict(audit_trace),
    }


EXAMPLE_RUNTIME_CONTEXT_V1 = {
    "WORKFLOW_ID": "wf_content_release",
    "EXECUTION_ID": "exec_2026_04_15_001",
    "WORKFLOW_VERSION": "1.4.2",
    "EXECUTION_MODE": "staged",
    "REQUESTED_ACTION": "start_execution",
    "INPUT_ARTIFACTS": [
        {"artifact_id": "doc_17", "artifact_type": "spec"}
    ],
    "REQUIRED_INVARIANTS": [
        "schema_valid",
        "policy_version_pinned",
        "executor_not_bypassed"
    ],
    "ENVIRONMENT_TAG": "staging",
    "POLICY_SET_VERSION": "policy_v1.0.0",
    "TIMESTAMP": "2026-04-15T09:30:00Z",
    "OPTIONAL_METADATA": {
        "requestor": "orchestrator",
        "change_ticket": "CHG-142"
    }
}

EXAMPLE_RULESET_V1 = [
    {
        "rule_id": "RULE-001",
        "rule_name": "workflow_id_exists",
        "description": "WORKFLOW_ID privalo egzistuoti",
        "target_field": "WORKFLOW_ID",
        "operator": "exists",
        "expected_value": None,
        "severity": "BLOCKING",
        "failure_message": "WORKFLOW_ID nerastas",
        "enabled": True,
    },
    {
        "rule_id": "RULE-002",
        "rule_name": "execution_id_not_empty",
        "description": "EXECUTION_ID negali būti tuščias",
        "target_field": "EXECUTION_ID",
        "operator": "not_empty",
        "expected_value": None,
        "severity": "BLOCKING",
        "failure_message": "EXECUTION_ID tuščias arba nerastas",
        "enabled": True,
    },
    {
        "rule_id": "RULE-003",
        "rule_name": "execution_mode_allowed",
        "description": "EXECUTION_MODE turi būti leidžiamų reikšmių sąraše",
        "target_field": "EXECUTION_MODE",
        "operator": "in_list",
        "expected_value": ["dry_run", "staged", "live"],
        "severity": "BLOCKING",
        "failure_message": "EXECUTION_MODE reikšmė neleistina arba laukas nerastas",
        "enabled": True,
    },
    {
        "rule_id": "RULE-004",
        "rule_name": "policy_set_version_exists",
        "description": "POLICY_SET_VERSION privalo egzistuoti",
        "target_field": "POLICY_SET_VERSION",
        "operator": "exists",
        "expected_value": None,
        "severity": "BLOCKING",
        "failure_message": "POLICY_SET_VERSION nerastas",
        "enabled": True,
    },
    {
        "rule_id": "RULE-005",
        "rule_name": "environment_tag_not_empty",
        "description": "ENVIRONMENT_TAG neturi būti tuščias",
        "target_field": "ENVIRONMENT_TAG",
        "operator": "not_empty",
        "expected_value": None,
        "severity": "WARNING",
        "failure_message": "ENVIRONMENT_TAG tuščias arba nerastas",
        "enabled": True,
    },
]


if __name__ == "__main__":
    result = evaluate_rules(EXAMPLE_RUNTIME_CONTEXT_V1, EXAMPLE_RULESET_V1)
    print(json.dumps(result, indent=2, ensure_ascii=False))
