"""
Abstract Syntax Tree (AST) builder for network device configurations.

Two parsing strategies:
  1. IndentationParser  — Cisco IOS / NX-OS / SONiC (whitespace-depth tree)
  2. BraceParser        — Juniper JunOS / PAN-OS (recursive {} descent)

Output is a unified nested dict that downstream normalizers can traverse.
"""
from __future__ import annotations

import re
from typing import Any

from app.ingestion.sanitizer import VendorType


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _indent_depth(line: str) -> int:
    """Count leading spaces (tabs expanded to 1)."""
    return len(line) - len(line.lstrip(" \t"))


# ─────────────────────────────────────────────────────────────────────────────
# Indentation Parser (Cisco IOS, NX-OS, SONiC)
# ─────────────────────────────────────────────────────────────────────────────

class IndentationParser:
    """
    Builds a tree from indented config text.

    Structure: Dict[str, Any] where values are either:
      - str  : leaf value
      - dict : nested sub-section
      - list : repeated keys (e.g. multiple 'neighbor' statements)
    """

    def parse(self, text: str) -> dict[str, Any]:
        lines = [
            ln for ln in text.splitlines()
            if ln.strip() and not ln.strip().startswith("!")
        ]
        root: dict[str, Any] = {}
        self._parse_block(lines, 0, len(lines), 0, root)
        return root

    def _parse_block(
        self,
        lines: list[str],
        start: int,
        end: int,
        base_depth: int,
        parent: dict[str, Any],
    ) -> None:
        i = start
        while i < end:
            line = lines[i]
            depth = _indent_depth(line)
            stripped = line.strip()

            if depth < base_depth:
                # Dedent — caller handles continuation
                return

            # Look ahead: does the next line go deeper? → this is a section header
            next_depth = _indent_depth(lines[i + 1]) if i + 1 < end else -1

            if next_depth > depth:
                # Section header
                key = stripped
                child: dict[str, Any] = {}
                # Find end of block (next line at same or lesser indent)
                j = i + 1
                while j < end and _indent_depth(lines[j]) > depth:
                    j += 1
                self._parse_block(lines, i + 1, j, depth + 1, child)
                self._insert(parent, key, child)
                i = j
            else:
                # Leaf statement
                parts = stripped.split(None, 1)
                key = parts[0]
                val = parts[1] if len(parts) > 1 else True
                self._insert(parent, key, val)
                i += 1

    @staticmethod
    def _insert(node: dict, key: str, value: Any) -> None:
        """Insert key; if key already exists, promote to list."""
        if key not in node:
            node[key] = value
        elif isinstance(node[key], list):
            node[key].append(value)
        else:
            node[key] = [node[key], value]


# ─────────────────────────────────────────────────────────────────────────────
# Brace Parser (Junos, PAN-OS)
# ─────────────────────────────────────────────────────────────────────────────

class BraceParser:
    """
    Recursive descent parser for brace-delimited config syntax.

    Handles:
      key { ... }        → nested dict
      key value;         → leaf
      key value1 value2; → leaf with multi-word value
    """

    _TOKEN = re.compile(r'[{};\n]|[^\s{};\n]+')

    def parse(self, text: str) -> dict[str, Any]:
        # Remove comments (JunOS uses /* */ and #)
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        text = re.sub(r'#[^\n]*', '', text)
        tokens = self._TOKEN.findall(text)
        tokens = [t for t in tokens if t.strip() and t != '\n']
        pos, root = self._parse_block(tokens, 0)
        return root

    def _parse_block(self, tokens: list[str], pos: int) -> tuple[int, dict[str, Any]]:
        node: dict[str, Any] = {}
        while pos < len(tokens):
            tok = tokens[pos]
            if tok == '}':
                return pos + 1, node
            if tok == ';':
                pos += 1
                continue

            # Collect key + value tokens up to { ; or }
            key_parts: list[str] = [tok]
            pos += 1
            while pos < len(tokens) and tokens[pos] not in ('{', ';', '}'):
                key_parts.append(tokens[pos])
                pos += 1

            key = key_parts[0]
            value_parts = key_parts[1:]

            if pos < len(tokens) and tokens[pos] == '{':
                # Nested block
                pos, child = self._parse_block(tokens, pos + 1)
                # Merge value parts as sub-key '_name' if present
                if value_parts:
                    child['_name'] = ' '.join(value_parts)
                _brace_insert(node, key, child)
            elif pos < len(tokens) and tokens[pos] == ';':
                val = ' '.join(value_parts) if value_parts else True
                _brace_insert(node, key, val)
                pos += 1
            else:
                val = ' '.join(value_parts) if value_parts else True
                _brace_insert(node, key, val)

        return pos, node


def _brace_insert(node: dict, key: str, value: Any) -> None:
    if key not in node:
        node[key] = value
    elif isinstance(node[key], list):
        node[key].append(value)
    else:
        node[key] = [node[key], value]


# ─────────────────────────────────────────────────────────────────────────────
# Public factory
# ─────────────────────────────────────────────────────────────────────────────

def build_ast(text: str, vendor: str) -> dict[str, Any]:
    """
    Select the correct parser strategy based on vendor and return the AST dict.
    """
    if vendor in (VendorType.JUNOS, VendorType.PALOALTO):
        return BraceParser().parse(text)
    else:
        return IndentationParser().parse(text)
