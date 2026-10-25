"""
TextFSM-based structured parser.

Dispatches the correct .textfsm template based on vendor, runs the parse,
and returns a dict of extracted fields + a list of unmatched lines.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

try:
    import textfsm
    _TEXTFSM_AVAILABLE = True
except ImportError:  # not installed outside Docker
    textfsm = None  # type: ignore[assignment]
    _TEXTFSM_AVAILABLE = False

from app.normalization.vendor_map import get_template_key

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"



def textfsm_parse(text: str, vendor: str) -> tuple[dict[str, Any], list[str]]:
    """
    Run TextFSM template against config text.

    Returns:
        (parsed_dict, unknown_lines)
        parsed_dict   : merged dict of all extracted field values
        unknown_lines : lines that didn't match any TextFSM rule
    """
    if not _TEXTFSM_AVAILABLE:
        logger.debug("textfsm not installed — skipping TextFSM parse for vendor '%s'", vendor)
        return {}, []

    template_key = get_template_key(vendor)
    if not template_key:
        return {}, []

    template_path = TEMPLATES_DIR / f"{template_key}.textfsm"
    if not template_path.exists():
        return {}, []

    try:
        # Keep file handle open for the entire TextFSM lifecycle:
        # TextFSM reads the template in __init__, then ParseText uses the
        # already-parsed internal state — both must happen inside the with block
        # to guarantee the handle stays valid on all platforms.
        with open(template_path, "r", encoding="utf-8") as fh:
            fsm = textfsm.TextFSM(fh)
            records = fsm.ParseText(text)
            headers = fsm.header

        # Merge all records into a single flat dict.
        # Single-value fields: keep last non-empty value.
        # List-type fields (TextFSM "List" keyword): accumulate across records.
        parsed: dict[str, Any] = {h: None for h in headers}
        for record in records:
            for header, value in zip(headers, record):
                if value not in (None, "", []):
                    if isinstance(value, list):
                        existing = parsed.get(header) or []
                        parsed[header] = existing + value
                    else:
                        parsed[header] = value

        # Build set of values that were successfully extracted.
        matched_values: set[str] = set()
        for v in parsed.values():
            if isinstance(v, list):
                matched_values.update(str(i) for i in v if i)
            elif v is not None:
                matched_values.add(str(v))

        # If nothing was extracted, every non-trivial line is unknown.
        if not matched_values:
            unknown_lines = [
                line.strip()
                for line in text.splitlines()
                if line.strip() and not line.strip().startswith("!")
            ]
            return parsed, unknown_lines

        # Otherwise flag lines that contain none of the matched values.
        significant = {mv for mv in matched_values if len(mv) > 3}
        unknown_lines = [
            stripped
            for line in text.splitlines()
            if (stripped := line.strip())
            and not stripped.startswith("!")
            and not any(mv in stripped for mv in significant)
        ]

        return parsed, unknown_lines

    except textfsm.TextFSMError as exc:
        # Template syntax error — surface it rather than silently swallowing
        logger.warning("TextFSM template error for vendor '%s': %s", vendor, exc)
        return {}, []
    except Exception:
        return {}, []
