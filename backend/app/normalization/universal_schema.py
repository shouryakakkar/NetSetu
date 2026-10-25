"""
Universal Security Baseline Model — the canonical JSON schema that all
vendor-specific configs are normalized into before compliance checking.

Every field is Optional because not every vendor exposes every parameter.
None means "not found in config" (distinct from False = explicitly disabled).
"""
from typing import Optional
from pydantic import BaseModel, Field


class InterfaceSecurityModel(BaseModel):
    """Per-interface security settings."""
    name: str
    shutdown: Optional[bool] = None
    port_security_enabled: Optional[bool] = None
    port_security_max_mac: Optional[int] = None
    storm_control_broadcast: Optional[bool] = None
    spanning_tree_portfast: Optional[bool] = None
    spanning_tree_bpduguard: Optional[bool] = None
    ip_access_group_in: Optional[str] = None
    ip_access_group_out: Optional[str] = None
    dhcp_snooping_trust: Optional[bool] = None
    dynamic_arp_inspection: Optional[bool] = None


class SNMPModel(BaseModel):
    """SNMP configuration security parameters."""
    version: Optional[str] = None          # "v1", "v2c", "v3"
    community_public_ro: Optional[bool] = None   # True = dangerous default community
    community_private_rw: Optional[bool] = None  # True = dangerous default community
    v3_auth_protocol: Optional[str] = None       # MD5, SHA, SHA-256
    v3_priv_protocol: Optional[str] = None       # DES, AES-128, AES-256
    trap_host: Optional[str] = None


class AAAModel(BaseModel):
    """Authentication, Authorization, Accounting."""
    enabled: Optional[bool] = None
    new_model: Optional[bool] = None       # Cisco: 'aaa new-model'
    authentication_login_local: Optional[bool] = None
    authentication_login_radius: Optional[bool] = None
    authentication_login_tacacs: Optional[bool] = None
    authorization_commands: Optional[bool] = None
    accounting_enabled: Optional[bool] = None


class NTPModel(BaseModel):
    """NTP security configuration."""
    configured: Optional[bool] = None
    server_count: Optional[int] = None
    authentication_enabled: Optional[bool] = None
    trusted_key_configured: Optional[bool] = None


class LoggingModel(BaseModel):
    """Syslog / logging configuration."""
    enabled: Optional[bool] = None
    console_enabled: Optional[bool] = None
    buffered_enabled: Optional[bool] = None
    remote_host: Optional[str] = None        # Syslog server IP
    log_level: Optional[str] = None          # informational, warning, etc.
    timestamps_enabled: Optional[bool] = None


class BGPSecurityModel(BaseModel):
    """BGP routing security."""
    md5_auth_enabled: Optional[bool] = None
    prefix_list_inbound: Optional[bool] = None
    prefix_list_outbound: Optional[bool] = None
    max_prefix_configured: Optional[bool] = None


class SecurityBaselineModel(BaseModel):
    """
    Universal Security Baseline Model — vendor-agnostic canonical schema.
    All compliance checks operate on this model.
    """
    # ── Device Identity ───────────────────────────────────────────────────────
    hostname: Optional[str] = Field(None, description="Device hostname")
    vendor: Optional[str] = Field(None, description="Detected vendor string")
    os_version: Optional[str] = Field(None, description="OS/firmware version")

    # ── Remote Access ─────────────────────────────────────────────────────────
    ssh_version: Optional[int] = Field(None, description="SSH protocol version (1 or 2)")
    ssh_enabled: Optional[bool] = Field(None, description="SSH service active")
    telnet_enabled: Optional[bool] = Field(None, description="Telnet enabled (dangerous)")
    vty_acl_applied: Optional[bool] = Field(None, description="ACL on VTY lines")
    vty_transport_input_ssh_only: Optional[bool] = Field(None, description="VTY restricted to SSH")
    console_timeout: Optional[int] = Field(None, description="Console exec-timeout (minutes)")
    vty_timeout: Optional[int] = Field(None, description="VTY exec-timeout (minutes)")

    # ── SNMP ──────────────────────────────────────────────────────────────────
    snmp: Optional[SNMPModel] = None

    # ── AAA ───────────────────────────────────────────────────────────────────
    aaa: Optional[AAAModel] = None

    # ── NTP ───────────────────────────────────────────────────────────────────
    ntp: Optional[NTPModel] = None

    # ── Logging ───────────────────────────────────────────────────────────────
    logging: Optional[LoggingModel] = None

    # ── Password & Encryption ─────────────────────────────────────────────────
    password_encryption_service: Optional[bool] = Field(
        None, description="Global password encryption enabled"
    )
    enable_secret_set: Optional[bool] = Field(None, description="Enable secret configured")
    min_password_length: Optional[int] = Field(None, description="Minimum password length policy")

    # ── Web Services ──────────────────────────────────────────────────────────
    http_server_enabled: Optional[bool] = Field(None, description="HTTP server running")
    https_server_enabled: Optional[bool] = Field(None, description="HTTPS server running")

    # ── Banner ────────────────────────────────────────────────────────────────
    banner_motd_set: Optional[bool] = Field(None, description="MOTD banner configured")
    banner_login_set: Optional[bool] = Field(None, description="Login banner configured")

    # ── BGP ───────────────────────────────────────────────────────────────────
    bgp: Optional[BGPSecurityModel] = None

    # ── CDP / LLDP (discovery protocols) ─────────────────────────────────────
    cdp_enabled_globally: Optional[bool] = None
    lldp_enabled_globally: Optional[bool] = None

    # ── Spanning Tree ─────────────────────────────────────────────────────────
    spanning_tree_mode: Optional[str] = None        # rapid-pvst, mstp, etc.
    bpduguard_global: Optional[bool] = None

    # ── Interfaces ────────────────────────────────────────────────────────────
    interfaces: list[InterfaceSecurityModel] = Field(default_factory=list)

    # ── Metadata ──────────────────────────────────────────────────────────────
    raw_line_count: Optional[int] = None
    unknown_syntax_count: Optional[int] = None
