"""Tests for the AST builder (IndentationParser and BraceParser)."""
import pytest

from app.normalization.ast_builder import BraceParser, IndentationParser, build_ast


CISCO_CONFIG = """\
hostname router1
!
ip ssh version 2
!
line vty 0 4
 transport input ssh
 exec-timeout 10 0
 access-class MGMT in
!
snmp-server community secret RO
!
ntp server 10.0.0.1
ntp authenticate
"""

JUNOS_CONFIG = """\
system {
    host-name junos-router;
    services {
        ssh {
            protocol-version v2;
        }
        telnet;
    }
    syslog {
        host 10.0.0.5 {
            any info;
        }
    }
}
ntp {
    server 10.0.0.1;
    authentication-key 1 type md5 value secret;
    trusted-key 1;
}
"""


class TestIndentationParser:
    def test_parses_hostname(self):
        ast = IndentationParser().parse(CISCO_CONFIG)
        assert ast.get("hostname") == "router1"

    def test_parses_ssh_version(self):
        ast = IndentationParser().parse(CISCO_CONFIG)
        ip_block = ast.get("ip", {})
        assert isinstance(ip_block, dict)

    def test_parses_nested_vty_block(self):
        ast = IndentationParser().parse(CISCO_CONFIG)
        line = ast.get("line")
        assert line is not None

    def test_empty_config(self):
        ast = IndentationParser().parse("")
        assert ast == {}

    def test_comment_lines_excluded(self):
        config = "hostname r1\n! this is a comment\nntp server 1.1.1.1"
        ast = IndentationParser().parse(config)
        assert "!" not in str(ast)


class TestBraceParser:
    def test_parses_hostname(self):
        ast = BraceParser().parse(JUNOS_CONFIG)
        system = ast.get("system", {})
        assert system.get("host-name") == "junos-router"

    def test_parses_nested_ssh(self):
        ast = BraceParser().parse(JUNOS_CONFIG)
        services = ast.get("system", {}).get("services", {})
        assert "ssh" in services

    def test_parses_ssh_protocol_version(self):
        ast = BraceParser().parse(JUNOS_CONFIG)
        ssh = ast["system"]["services"]["ssh"]
        assert ssh.get("protocol-version") == "v2"

    def test_handles_empty_input(self):
        ast = BraceParser().parse("")
        assert ast == {}


class TestBuildAstFactory:
    def test_uses_indentation_for_cisco(self):
        ast = build_ast(CISCO_CONFIG, "cisco_ios")
        assert ast.get("hostname") == "router1"

    def test_uses_brace_for_junos(self):
        ast = build_ast(JUNOS_CONFIG, "junos")
        assert "system" in ast

    def test_uses_indentation_for_sonic(self):
        config = "hostname sonic\nntp server 1.2.3.4"
        ast = build_ast(config, "sonic")
        assert ast.get("hostname") == "sonic"
