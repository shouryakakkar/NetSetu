"""
Remediation generator: groups compliance findings by severity and
maps each FAIL/WARN finding to vendor-specific CLI fix commands.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.compliance.engine import ComplianceFinding, ComplianceStatus
from app.remediation.vendor_cli_map import get_remediation_commands


@dataclass
class RemediationItem:
    control_id: str
    title: str
    severity: str
    param_path: str
    cli_commands: str   # May be multi-line
    expected: object
    actual: object


def generate_remediation(
    findings: list[ComplianceFinding],
    vendor: str,
) -> list[RemediationItem]:
    """
    For every FAIL or WARN finding, look up the vendor-specific remediation
    command and return an ordered list of RemediationItems.

    Items are sorted CRITICAL → HIGH → MEDIUM → LOW.
    """
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}

    actionable = [
        f for f in findings
        if f.status in (ComplianceStatus.FAIL, ComplianceStatus.WARN)
    ]

    failing_params = [f.param_path for f in actionable]
    cli_map = get_remediation_commands(vendor, failing_params)

    items: list[RemediationItem] = []
    for finding in actionable:
        cli = cli_map.get(finding.param_path) or finding.remediation_hint or "Manual remediation required. Consult vendor documentation."
        items.append(RemediationItem(
            control_id=finding.control_id,
            title=finding.title,
            severity=finding.severity,
            param_path=finding.param_path,
            cli_commands=cli,
            expected=finding.expected,
            actual=finding.actual,
        ))

    items.sort(key=lambda x: severity_order.get(x.severity, 99))
    return items
