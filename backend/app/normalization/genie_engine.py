"""
Genie (pyATS) fallback parser.

Used when TextFSM returns no structured data.
Wraps genie.libs.parser for ios/nxos/junos platforms.
pyATS/Genie is an optional heavy dependency; import is guarded.
"""
from __future__ import annotations

from typing import Any

from app.normalization.vendor_map import get_genie_platform


def genie_parse(text: str, vendor: str) -> tuple[dict[str, Any], list[str]]:
    """
    Attempt Genie parsing for supported platforms (ios, nxos, junos).

    Returns:
        (parsed_dict, unknown_lines)
    """
    platform = get_genie_platform(vendor)
    if not platform:
        return {}, []

    try:
        from genie.libs.parser.utils import get_parser  # type: ignore
        from genie.conf.base import Device              # type: ignore

        # Build a mock Device context required by Genie parsers
        device = Device("mock", os=platform)
        device.custom.setdefault("abstraction", {})["order"] = ["os"]

        # Genie parses "show running-config" output
        parser_cls = get_parser("show running-config", device)
        parser_obj = parser_cls(device=device)
        output = parser_obj.cli(output=text)
        parsed = dict(output) if output else {}
        return parsed, []

    except Exception:
        # Genie not installed or parser not found for this platform/command
        return {}, []
