"""
Heuristic database CRUD — manages the active mapping rule table.

Rules are hot-reloaded at runtime (no restart needed) by re-querying
the DB on every normalization run.
"""
from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import MappingRule, RuleType, User


# ── CRUD ──────────────────────────────────────────────────────────────────────

async def create_rule(
    db: AsyncSession,
    raw_pattern: str,
    mapped_param: str,
    rule_type: RuleType,
    confidence: float,
    created_by: User | None = None,
) -> MappingRule:
    """Persist a new validated mapping rule."""
    rule = MappingRule(
        raw_pattern=raw_pattern,
        mapped_param=mapped_param,
        rule_type=rule_type,
        confidence=confidence,
        created_by_id=created_by.id if created_by else None,
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return rule


async def get_all_active_rules(db: AsyncSession) -> list[MappingRule]:
    """Fetch all active rules for runtime matching."""
    result = await db.execute(
        select(MappingRule).where(MappingRule.is_active == True)  # noqa: E712
    )
    return list(result.scalars().all())


async def deactivate_rule(db: AsyncSession, rule_id: uuid.UUID) -> bool:
    result = await db.execute(
        update(MappingRule)
        .where(MappingRule.id == rule_id)
        .values(is_active=False)
        .returning(MappingRule.id)
    )
    return result.scalar_one_or_none() is not None


# ── Runtime matcher ───────────────────────────────────────────────────────────

def apply_heuristic_rules(
    raw_line: str,
    rules: list[MappingRule],
) -> str | None:
    """
    Check a raw CLI line against stored heuristic rules.
    Returns the mapped_param of the first matching rule, or None.

    Regex rules are tried first (deterministic), then semantic (substring).
    """
    regex_rules = [r for r in rules if r.rule_type == RuleType.REGEX]
    semantic_rules = [r for r in rules if r.rule_type == RuleType.SEMANTIC]

    for rule in sorted(regex_rules, key=lambda r: -r.confidence):
        try:
            if re.search(rule.raw_pattern, raw_line, re.IGNORECASE):
                return rule.mapped_param
        except re.error:
            continue

    for rule in sorted(semantic_rules, key=lambda r: -r.confidence):
        if rule.raw_pattern.lower() in raw_line.lower():
            return rule.mapped_param

    return None
