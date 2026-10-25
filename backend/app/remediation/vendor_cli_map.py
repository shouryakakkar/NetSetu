"""
Vendor CLI remediation command templates.

Structure: {vendor: {param_path: CLI_command_string}}
Multi-line commands use \\n as separator.
{PLACEHOLDER} tokens should be filled in by the remediation generator
with actual device context where available.
"""

CLI_REMEDIATION: dict[str, dict[str, str]] = {
    "cisco_ios": {
        "ssh_version":                  "ip ssh version 2",
        "telnet_enabled":               "line vty 0 15\n transport input ssh",
        "vty_transport_input_ssh_only": "line vty 0 15\n transport input ssh",
        "vty_acl_applied":              "ip access-list standard MGMT-ACCESS\n permit {MGMT_SUBNET}\n deny any log\n!\nline vty 0 15\n access-class MGMT-ACCESS in",
        "vty_timeout":                  "line vty 0 15\n exec-timeout 10 0",
        "console_timeout":              "line con 0\n exec-timeout 10 0",
        "snmp.version":                 "snmp-server group SECURE-GROUP v3 priv\nsnmp-server user SECURE-USER SECURE-GROUP v3 auth sha {AUTH_PW} priv aes 128 {PRIV_PW}",
        "snmp.community_public_ro":     "no snmp-server community public",
        "snmp.community_private_rw":    "no snmp-server community private",
        "aaa.enabled":                  "aaa new-model",
        "aaa.new_model":                "aaa new-model",
        "aaa.authentication_login_tacacs": "aaa authentication login default group tacacs+ local",
        "ntp.configured":               "ntp server {NTP_PRIMARY_IP}\nntp server {NTP_SECONDARY_IP}",
        "ntp.authentication_enabled":   "ntp authenticate\nntp authentication-key 1 md5 {NTP_KEY}\nntp trusted-key 1\nntp server {NTP_IP} key 1",
        "password_encryption_service":  "service password-encryption",
        "enable_secret_set":            "enable secret {ENABLE_SECRET}",
        "http_server_enabled":          "no ip http server",
        "banner_motd_set":              "banner motd ^\n WARNING: Authorized access only.\n Unauthorized access is prohibited and subject to prosecution.\n^\n",
        "logging.enabled":              "logging on",
        "logging.remote_host":          "logging host {SYSLOG_IP}\nlogging trap informational\nlogging source-interface {MGMT_INTERFACE}",
        "cdp_enabled_globally":         "no cdp run",
        "bgp.md5_auth_enabled":         "router bgp {AS_NUMBER}\n neighbor {NEIGHBOR_IP} password {BGP_PASSWORD}",
        "spanning_tree_bpduguard":      "spanning-tree portfast bpduguard default",
    },

    "cisco_nxos": {
        "ssh_version":                  "ssh version 2",
        "telnet_enabled":               "no feature telnet",
        "vty_transport_input_ssh_only": "line vty\n transport input ssh",
        "vty_timeout":                  "line vty\n exec-timeout 10",
        "snmp.community_public_ro":     "no snmp-server community public",
        "aaa.enabled":                  "feature tacacs+\naaa authentication login default group tacacs+ local",
        "password_encryption_service":  "no password strength-check\nservice password-encryption",
        "http_server_enabled":          "no feature http-server",
        "logging.remote_host":          "logging server {SYSLOG_IP} 5 use-vrf management",
        "ntp.configured":               "ntp server {NTP_IP} use-vrf management",
        "banner_motd_set":              "banner motd #\n Authorized access only.\n#",
    },

    "junos": {
        "ssh_version":                  "set system services ssh protocol-version v2",
        "telnet_enabled":               "delete system services telnet",
        "vty_timeout":                  "set system login retry-options backoff-threshold 1\nset system login retry-options backoff-factor 5\nset system login retry-options maximum-time 300",
        "snmp.version":                 "set snmp v3 usm local-engine user {USER} authentication-sha authentication-password {AUTH_PW}\nset snmp v3 usm local-engine user {USER} privacy-aes128 privacy-password {PRIV_PW}",
        "snmp.community_public_ro":     "delete snmp community public",
        "aaa.enabled":                  "set system authentication-order [radius password]",
        "ntp.configured":               "set ntp server {NTP_IP}",
        "ntp.authentication_enabled":   "set ntp authentication-key {KEY_ID} type md5 value {KEY_VALUE}\nset ntp trusted-key {KEY_ID}",
        "password_encryption_service":  "set system login password format sha512",
        "enable_secret_set":            "set system root-authentication encrypted-password '{HASHED_PW}'",
        "http_server_enabled":          "delete system services web-management http",
        "banner_motd_set":              "set system login message \"Authorized access only. Unauthorized access is prohibited.\"",
        "logging.remote_host":          "set system syslog host {SYSLOG_IP} any info",
        "cdp_enabled_globally":         "delete protocols lldp",
    },

    "paloalto": {
        "ssh_version":                  "set deviceconfig system ssh service-enable yes",
        "telnet_enabled":               "delete deviceconfig system service telnet",
        "snmp.version":                 "set deviceconfig system snmp-setting access-setting version v3\nset deviceconfig system snmp-setting access-setting version v3 views {VIEW} oid 1.3.6.1 option include mask 0xff",
        "aaa.enabled":                  "set deviceconfig system authentication-profile {PROFILE}",
        "ntp.configured":               "set deviceconfig system ntp-servers primary-ntp-server ntp-server-address {NTP_IP}",
        "banner_motd_set":              "set deviceconfig system motd-and-banner banner \"Authorized access only.\"",
        "logging.remote_host":          "set shared log-forwarding {PROFILE} match-list {LIST} send-syslog {SYSLOG_PROFILE}",
        "http_server_enabled":          "set deviceconfig system service disable-http yes",
        "password_encryption_service":  "set mgt-config password-complexity enabled yes",
    },

    "sonic": {
        "ssh_version":                  "# SSH v2 is default in SONiC OpenSSH\necho 'Protocol 2' >> /etc/ssh/sshd_config && systemctl restart sshd",
        "telnet_enabled":               "sudo systemctl disable telnetd --now",
        "aaa.enabled":                  "# Configure TACACS+ in /etc/pam.d/common-auth\nconfig tacacs add {TACACS_IP}",
        "ntp.configured":               "config ntp add {NTP_IP}",
        "logging.remote_host":          "config syslog add {SYSLOG_IP}",
        "password_encryption_service":  "# Ensure PAM password hashing uses sha512\ngrep sha512 /etc/pam.d/common-password",
        "banner_motd_set":              "echo 'Authorized access only.' > /etc/motd",
    },
}


def get_remediation_commands(vendor: str, failing_params: list[str]) -> dict[str, str]:
    """
    Look up vendor-specific CLI remediation commands for a list of failing params.

    Returns dict of {param_path: cli_command} for all matched params.
    """
    vendor_map = CLI_REMEDIATION.get(vendor, {})
    result: dict[str, str] = {}
    for param in failing_params:
        cmd = vendor_map.get(param)
        if cmd:
            result[param] = cmd
        else:
            # Try parent key (e.g. 'snmp.version' → 'snmp')
            parent = param.split(".")[0]
            parent_cmd = vendor_map.get(parent)
            if parent_cmd:
                result[param] = parent_cmd
    return result
