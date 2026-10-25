"""
Universal schema mapper.

Takes:
  ast    : raw AST dict from ast_builder
  parsed : structured dict from TextFSM / Genie
  vendor : vendor string

Returns:
  (SecurityBaselineModel, flagged_lines: list[str])

Flagged lines are those not mapped by either parser — queued for AI review.
"""
from __future__ import annotations

import re
from typing import Any

from app.normalization.universal_schema import (
    AAAModel,
    BGPSecurityModel,
    InterfaceSecurityModel,
    LoggingModel,
    NTPModel,
    SNMPModel,
    SecurityBaselineModel,
)


# ── Helper utilities ──────────────────────────────────────────────────────────

def _get(d: dict, *keys: str, default=None):
    """Safe nested dict getter."""
    node = d
    for k in keys:
        if not isinstance(node, dict):
            return default
        node = node.get(k, default)
        if node is None:
            return default
    return node


def _bool_flag(val) -> bool | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    s = str(val).lower().strip()
    if s in ("true", "yes", "enabled", "1", "enable"):
        return True
    if s in ("false", "no", "disabled", "0", "disable"):
        return False
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Vendor-specific mapping functions
# ─────────────────────────────────────────────────────────────────────────────

def _map_cisco(ast: dict, parsed: dict) -> SecurityBaselineModel:
    """Extract security parameters from a Cisco IOS / NX-OS config AST."""

    # SSH
    ssh_version_raw = (
        parsed.get("SSH_VERSION")
        or _get(ast, "ip", "ssh", "version")
    )
    ssh_version = int(ssh_version_raw) if ssh_version_raw else None

    # Telnet: present if 'transport input telnet' found in any VTY block
    telnet_enabled = False
    vty_acl_applied = False
    vty_ssh_only = False
    console_timeout = None
    vty_timeout = None

    line_section = ast.get("line") or {}
    if isinstance(line_section, dict):
        for key, val in line_section.items():
            if "vty" in str(key).lower():
                block = val if isinstance(val, dict) else {}
                ti = block.get("transport", {})
                if isinstance(ti, dict):
                    inp = ti.get("input", "")
                else:
                    inp = str(block.get("transport", ""))
                if "telnet" in str(inp).lower():
                    telnet_enabled = True
                if "ssh" in str(inp).lower() and "telnet" not in str(inp).lower():
                    vty_ssh_only = True
                if block.get("access-class"):
                    vty_acl_applied = True
                if block.get("exec-timeout"):
                    try:
                        vty_timeout = int(str(block["exec-timeout"]).split()[0])
                    except (ValueError, IndexError):
                        pass
            if "console" in str(key).lower():
                block = val if isinstance(val, dict) else {}
                if block.get("exec-timeout"):
                    try:
                        console_timeout = int(str(block["exec-timeout"]).split()[0])
                    except (ValueError, IndexError):
                        pass

    # SNMP
    snmp_block = ast.get("snmp-server") or {}
    snmp_version = None
    comm_public = False
    comm_private = False
    if isinstance(snmp_block, dict):
        communities = snmp_block.get("community") or {}
        if isinstance(communities, str):
            communities = {communities: {}}
        elif isinstance(communities, list):
            communities = {c: {} for c in communities}
        comm_public = "public" in str(communities).lower()
        comm_private = "private" in str(communities).lower()
        if snmp_block.get("group") or snmp_block.get("user"):
            snmp_version = "v3"
        elif communities:
            snmp_version = "v2c"

    snmp = SNMPModel(
        version=snmp_version,
        community_public_ro=comm_public,
        community_private_rw=comm_private,
    )

    # AAA
    aaa_block = ast.get("aaa") or {}
    aaa = AAAModel(
        enabled=bool(aaa_block),
        new_model="new-model" in str(aaa_block),
        authentication_login_local="local" in str(aaa_block).lower(),
        authentication_login_radius="radius" in str(aaa_block).lower(),
        authentication_login_tacacs="tacacs" in str(aaa_block).lower(),
        accounting_enabled="accounting" in str(aaa_block).lower(),
    )

    # NTP
    ntp_block = ast.get("ntp") or {}
    ntp_servers = [k for k in (ntp_block if isinstance(ntp_block, dict) else {}) if "server" in k.lower()]
    ntp = NTPModel(
        configured=bool(ntp_block),
        server_count=len(ntp_servers) if ntp_servers else (1 if ntp_block else 0),
        authentication_enabled="authentication" in str(ntp_block).lower(),
        trusted_key_configured="trusted-key" in str(ntp_block).lower(),
    )

    # Logging
    logging_block = ast.get("logging") or {}
    log_host = None
    if isinstance(logging_block, dict):
        for k in logging_block:
            if re.match(r"\d+\.\d+\.\d+\.\d+", k):
                log_host = k
                break
    logging_m = LoggingModel(
        enabled=bool(logging_block),
        buffered_enabled="buffered" in str(logging_block).lower(),
        remote_host=log_host,
        timestamps_enabled="timestamps" in str(ast).lower(),
    )

    # Passwords / secrets
    pw_encrypt = "service" in str(ast.get("service", "")).lower() and \
                 "password-encryption" in str(ast).lower()
    enable_secret = "secret" in str(ast.get("enable", "")).lower()

    # HTTP
    http_block = ast.get("ip", {})
    http_server = isinstance(http_block, dict) and "http" in http_block
    https_server = isinstance(http_block, dict) and "http" in str(http_block).lower() and \
                   "secure" in str(http_block).lower()

    # Banners
    banner = ast.get("banner") or {}
    banner_motd = bool(banner and "motd" in str(banner).lower())
    banner_login = bool(banner and "login" in str(banner).lower())

    # CDP / LLDP
    cdp_enabled = "no cdp run" not in str(ast).lower()
    lldp_enabled = "lldp run" in str(ast).lower()

    # BGP
    bgp_block = ast.get("router", {})
    bgp_data = None
    if isinstance(bgp_block, dict) and "bgp" in str(bgp_block).lower():
        bgp_data = BGPSecurityModel(
            md5_auth_enabled="password" in str(bgp_block).lower(),
            prefix_list_inbound="prefix-list" in str(bgp_block).lower(),
        )

    # Interfaces
    ifaces: list[InterfaceSecurityModel] = []
    for key, val in ast.items():
        if key.lower().startswith("interface"):
            iname = key.replace("interface", "").strip()
            block = val if isinstance(val, dict) else {}
            ifaces.append(InterfaceSecurityModel(
                name=iname,
                shutdown=block.get("shutdown") is not None,
                port_security_enabled="port-security" in str(block).lower(),
                spanning_tree_portfast="portfast" in str(block).lower(),
                spanning_tree_bpduguard="bpduguard" in str(block).lower(),
            ))

    return SecurityBaselineModel(
        vendor="cisco",
        hostname=parsed.get("HOSTNAME") or ast.get("hostname"),
        ssh_version=ssh_version,
        ssh_enabled=ssh_version is not None,
        telnet_enabled=telnet_enabled,
        vty_acl_applied=vty_acl_applied,
        vty_transport_input_ssh_only=vty_ssh_only,
        console_timeout=console_timeout,
        vty_timeout=vty_timeout,
        snmp=snmp,
        aaa=aaa,
        ntp=ntp,
        logging=logging_m,
        password_encryption_service=pw_encrypt,
        enable_secret_set=enable_secret,
        http_server_enabled=http_server,
        https_server_enabled=https_server,
        banner_motd_set=banner_motd,
        banner_login_set=banner_login,
        cdp_enabled_globally=cdp_enabled,
        lldp_enabled_globally=lldp_enabled,
        bgp=bgp_data,
        interfaces=ifaces,
        raw_line_count=len(str(ast).splitlines()),
    )


def _map_junos(ast: dict, parsed: dict) -> SecurityBaselineModel:
    """Extract security parameters from a Junos config AST."""
    system = ast.get("system") or {}
    services = _get(system, "services") or {}
    ssh_block = _get(services, "ssh") or {}

    ssh_ver_raw = ssh_block.get("protocol-version", "")
    ssh_version = 2 if "v2" in str(ssh_ver_raw).lower() else (1 if "v1" in str(ssh_ver_raw).lower() else None)

    telnet_enabled = bool(_get(services, "telnet"))

    # SNMP
    snmp_block = ast.get("snmp") or {}
    snmp_comm = _get(snmp_block, "community") or {}
    snmp = SNMPModel(
        version="v3" if _get(snmp_block, "v3") else ("v2c" if snmp_comm else None),
        community_public_ro="public" in str(snmp_comm).lower(),
    )

    # AAA → Junos uses 'system login'
    login_block = _get(system, "login") or {}
    aaa = AAAModel(
        enabled=bool(login_block),
        authentication_login_radius="radius" in str(ast).lower(),
        authentication_login_tacacs="tacacs" in str(ast).lower(),
    )

    # NTP
    ntp_block = ast.get("ntp") or {}
    ntp = NTPModel(
        configured=bool(ntp_block),
        authentication_enabled="authentication-key" in str(ntp_block).lower(),
    )

    # Logging
    syslog = _get(system, "syslog") or {}
    log_host = None
    if isinstance(syslog, dict):
        for k in syslog:
            if re.match(r"\d+\.\d+\.\d+\.\d+", k):
                log_host = k
                break
    logging_m = LoggingModel(enabled=bool(syslog), remote_host=log_host)

    return SecurityBaselineModel(
        vendor="junos",
        hostname=_get(system, "host-name"),
        ssh_version=ssh_version,
        ssh_enabled=bool(ssh_block),
        telnet_enabled=telnet_enabled,
        snmp=snmp,
        aaa=aaa,
        ntp=ntp,
        logging=logging_m,
        banner_motd_set=bool(_get(system, "login", "message")),
    )


def _map_paloalto(ast: dict, parsed: dict) -> SecurityBaselineModel:
    """Extract security parameters from a PAN-OS config AST."""
    deviceconfig = ast.get("deviceconfig") or {}
    system_block = _get(deviceconfig, "system") or {}
    services_block = _get(system_block, "service") or {}

    ssh_enabled = "ssh" in str(services_block).lower()
    telnet_enabled = "telnet" in str(services_block).lower()

    snmp_block = _get(system_block, "snmp-setting") or {}
    snmp = SNMPModel(
        version="v3" if _get(snmp_block, "access-setting", "version", "v3") else None,
    )

    ntp_servers = _get(system_block, "ntp-servers") or {}
    ntp = NTPModel(configured=bool(ntp_servers), server_count=len(ntp_servers) if isinstance(ntp_servers, dict) else 0)

    return SecurityBaselineModel(
        vendor="paloalto",
        hostname=_get(system_block, "hostname"),
        ssh_enabled=ssh_enabled,
        telnet_enabled=telnet_enabled,
        snmp=snmp,
        ntp=ntp,
        banner_motd_set=bool(_get(system_block, "motd-and-banner", "banner")),
    )


def _map_sonic(ast: dict, parsed: dict) -> SecurityBaselineModel:
    """Extract security parameters from a SONiC config AST."""
    # SONiC uses FRR (Quagga-based) config format similar to Cisco IOS
    return _map_cisco(ast, parsed)


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

_VENDOR_MAPPERS = {
    "cisco_ios": _map_cisco,
    "cisco_nxos": _map_cisco,
    "junos": _map_junos,
    "paloalto": _map_paloalto,
    "sonic": _map_sonic,
}


def map_to_universal_schema(
    ast: dict,
    parsed: dict,
    vendor: str,
) -> tuple[SecurityBaselineModel, list[str]]:
    """
    Map AST + TextFSM/Genie parsed data to the SecurityBaselineModel.

    Returns:
        (model, flagged_lines)
        flagged_lines: lines that were not mapped (empty for known vendors)
    """
    mapper = _VENDOR_MAPPERS.get(vendor)
    if mapper:
        model = mapper(ast, parsed)
        flagged: list[str] = []
    else:
        # Unknown vendor — return empty model, flag all non-trivial lines
        model = SecurityBaselineModel(vendor=vendor)
        flagged = [
            line.strip()
            for line in str(ast).splitlines()
            if line.strip() and len(line.strip()) > 5
        ][:200]  # Cap at 200 lines for AI review

    model.unknown_syntax_count = len(flagged)
    return model, flagged
