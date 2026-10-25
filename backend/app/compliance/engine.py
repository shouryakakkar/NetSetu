"""
Compliance Engine — diffs a SecurityBaselineModel against a selected framework.

Supported operators: eq, ne, is_true, is_false, gte, lte, in, not_in, not_null
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from app.normalization.universal_schema import SecurityBaselineModel

logger = logging.getLogger(__name__)
FRAMEWORKS_DIR = Path(__file__).parent / "frameworks"


class ComplianceStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    NOT_APPLICABLE = "N/A"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class ComplianceFinding:
    control_id: str
    title: str
    description: str
    severity: str
    status: ComplianceStatus
    expected: Any
    actual: Any
    remediation_hint: str
    param_path: str   # dot-notation path into SecurityBaselineModel


def _resolve_path(model: SecurityBaselineModel, path: str) -> Any:
    """
    Resolve a dot-notation path like 'snmp.version' from the baseline model.
    Returns None if any segment is missing.
    """
    obj: Any = model.model_dump()
    for part in path.split("."):
        if isinstance(obj, dict):
            obj = obj.get(part)
        else:
            return None
    return obj


def _evaluate(actual: Any, operator: str, expected: Any) -> bool:
    """Apply a rule operator and return True if the value is compliant."""
    try:
        match operator:
            case "eq":        return actual == expected
            case "ne":        return actual != expected
            case "is_true":   return actual is True
            case "is_false":  return actual is False
            case "gte":       return actual is not None and actual >= expected
            case "lte":       return actual is not None and actual <= expected
            case "in":        return actual in expected
            case "not_in":    return actual not in (expected or [])
            case "not_null":  return actual is not None
            case "is_null":   return actual is None
            case _:
                logger.warning("Unknown operator: %s", operator)
                return False
    except TypeError:
        return False


def _load_framework(name: str) -> list[dict]:
    path = FRAMEWORKS_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Framework '{name}' not found at {path}")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def run_compliance_check(
    model: SecurityBaselineModel,
    framework: str,
) -> tuple[list[ComplianceFinding], float]:
    """
    Compare a normalized model against a compliance framework.

    Returns:
        (findings, score)
        score: 0.0–100.0 percentage of controls that PASS
    """
    rules = _load_framework(framework)
    findings: list[ComplianceFinding] = []
    pass_count = 0
    applicable_count = 0

    for rule in rules:
        param_path: str = rule["param"]
        actual = _resolve_path(model, param_path)

        # If the param wasn't found at all → N/A
        if actual is None and rule.get("skip_if_null", False):
            findings.append(ComplianceFinding(
                control_id=rule["control_id"],
                title=rule["title"],
                description=rule["description"],
                severity=rule.get("severity", "INFO"),
                status=ComplianceStatus.NOT_APPLICABLE,
                expected=rule.get("value"),
                actual=actual,
                remediation_hint=rule.get("remediation", ""),
                param_path=param_path,
            ))
            continue

        applicable_count += 1
        compliant = _evaluate(actual, rule["operator"], rule.get("value"))

        if compliant:
            status = ComplianceStatus.PASS
            pass_count += 1
        elif rule.get("severity") in ("CRITICAL", "HIGH"):
            status = ComplianceStatus.FAIL
        else:
            status = ComplianceStatus.WARN

        findings.append(ComplianceFinding(
            control_id=rule["control_id"],
            title=rule["title"],
            description=rule["description"],
            severity=rule.get("severity", "MEDIUM"),
            status=status,
            expected=rule.get("value"),
            actual=actual,
            remediation_hint=rule.get("remediation", ""),
            param_path=param_path,
        ))

    score = (pass_count / applicable_count * 100) if applicable_count else 0.0
    return findings, round(score, 2)
