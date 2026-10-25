"""Tests for the compliance engine."""
import pytest

from app.compliance.engine import ComplianceStatus, run_compliance_check
from app.normalization.universal_schema import (
    AAAModel,
    LoggingModel,
    NTPModel,
    SNMPModel,
    SecurityBaselineModel,
)


def _good_model() -> SecurityBaselineModel:
    """A fully compliant model."""
    return SecurityBaselineModel(
        hostname="test-router",
        vendor="cisco_ios",
        ssh_version=2,
        ssh_enabled=True,
        telnet_enabled=False,
        vty_acl_applied=True,
        vty_transport_input_ssh_only=True,
        vty_timeout=10,
        console_timeout=10,
        snmp=SNMPModel(version="v3", community_public_ro=False, community_private_rw=False),
        aaa=AAAModel(enabled=True, new_model=True, authentication_login_tacacs=True),
        ntp=NTPModel(configured=True, authentication_enabled=True),
        logging=LoggingModel(enabled=True, remote_host="10.0.0.5"),
        password_encryption_service=True,
        enable_secret_set=True,
        http_server_enabled=False,
        banner_motd_set=True,
        cdp_enabled_globally=False,
    )


def _bad_model() -> SecurityBaselineModel:
    """A maximally non-compliant model."""
    return SecurityBaselineModel(
        hostname="bad-router",
        vendor="cisco_ios",
        ssh_version=1,               # FAIL: should be v2
        telnet_enabled=True,         # FAIL: telnet must be disabled
        vty_acl_applied=False,
        vty_transport_input_ssh_only=False,
        snmp=SNMPModel(version="v2c", community_public_ro=True, community_private_rw=True),
        aaa=AAAModel(enabled=False, new_model=False),
        ntp=NTPModel(configured=False, authentication_enabled=False),
        logging=LoggingModel(enabled=False, remote_host=None),
        password_encryption_service=False,
        enable_secret_set=False,
        http_server_enabled=True,
        banner_motd_set=False,
        cdp_enabled_globally=True,
    )


class TestCISCompliance:
    def test_good_model_high_score(self):
        findings, score = run_compliance_check(_good_model(), "cis")
        assert score > 80.0

    def test_bad_model_low_score(self):
        findings, score = run_compliance_check(_bad_model(), "cis")
        assert score < 30.0

    def test_ssh_version_fail(self):
        model = _good_model()
        model.ssh_version = 1
        findings, _ = run_compliance_check(model, "cis")
        ssh_finding = next((f for f in findings if f.control_id == "CIS-L1-1.1"), None)
        assert ssh_finding is not None
        assert ssh_finding.status == ComplianceStatus.FAIL

    def test_ssh_version_pass(self):
        findings, _ = run_compliance_check(_good_model(), "cis")
        ssh_finding = next((f for f in findings if f.control_id == "CIS-L1-1.1"), None)
        assert ssh_finding is not None
        assert ssh_finding.status == ComplianceStatus.PASS

    def test_snmp_public_community_critical(self):
        model = _bad_model()
        findings, _ = run_compliance_check(model, "cis")
        snmp_finding = next((f for f in findings if f.control_id == "CIS-L1-2.2"), None)
        assert snmp_finding is not None
        assert snmp_finding.status == ComplianceStatus.FAIL
        assert snmp_finding.severity == "CRITICAL"

    def test_enable_secret_fail(self):
        model = _bad_model()
        findings, _ = run_compliance_check(model, "cis")
        secret_finding = next((f for f in findings if f.control_id == "CIS-L1-5.2"), None)
        assert secret_finding is not None
        assert secret_finding.status == ComplianceStatus.FAIL


class TestNISTCompliance:
    def test_good_model_nist(self):
        findings, score = run_compliance_check(_good_model(), "nist")
        assert score > 70.0

    def test_returns_findings_list(self):
        findings, score = run_compliance_check(_bad_model(), "nist")
        assert isinstance(findings, list)
        assert len(findings) > 0


class TestSTIGCompliance:
    def test_stig_findings_have_v_ids(self):
        findings, _ = run_compliance_check(_good_model(), "stig")
        v_ids = [f.control_id for f in findings]
        assert all(v.startswith("V-") for v in v_ids)
