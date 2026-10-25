"""
AI Training Loop — orchestrates the full suggest → validate → store cycle.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_engine.heuristic_db import create_rule
from app.ai_engine.nlp_classifier import SuggestionResult, classify_syntax
from app.database.models import MappingRule, RuleType, User
from app.database.mongo import pending_review_col


# ── Suggest ───────────────────────────────────────────────────────────────────

async def suggest(raw_line: str) -> list[SuggestionResult]:
    """
    Pass raw_line through the NLP classifier and return top suggestions.
    This is a read-only operation — no DB writes.
    """
    return classify_syntax(raw_line, top_k=3)


# ── Validate & Store ──────────────────────────────────────────────────────────

async def validate_and_store(
    db: AsyncSession,
    raw_line: str,
    accepted_param: str,
    confidence: float,
    user: User,
    store_as_regex: bool = False,
) -> MappingRule:
    """
    Admin confirms (or overrides) the AI suggestion.
    Stores the mapping as a new rule in the heuristic DB.
    Also marks the pending_review MongoDB document as resolved.
    """
    rule_type = RuleType.REGEX if store_as_regex else RuleType.SEMANTIC
    rule = await create_rule(
        db=db,
        raw_pattern=raw_line,
        mapped_param=accepted_param,
        rule_type=rule_type,
        confidence=confidence,
        created_by=user,
    )
    # Mark resolved in MongoDB
    await pending_review_col().update_many(
        {"raw_line": raw_line},
        {"$set": {"resolved": True, "resolved_at": datetime.now(timezone.utc), "mapped_to": accepted_param}},
    )
    return rule


# ── Pending Review ────────────────────────────────────────────────────────────

async def get_pending_review(limit: int = 50) -> list[dict]:
    """
    Return unresolved flagged syntax lines from MongoDB.
    Each item includes the raw_line, job context, and any prior AI suggestion.
    """
    cursor = (
        pending_review_col()
        .find({"resolved": {"$ne": True}})
        .sort("created_at", -1)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    # Convert ObjectId to string for JSON serialisation
    for doc in docs:
        doc["_id"] = str(doc["_id"])
    return docs


async def queue_for_review(job_id: str, flagged_lines: list[str]) -> None:
    """
    Save newly flagged lines from a job into the pending_review collection.
    Also pre-fetches AI suggestions and embeds them in the document.
    """
    if not flagged_lines:
        return
    docs = []
    for line in flagged_lines:
        suggestions = classify_syntax(line, top_k=3)
        docs.append({
            "job_id": job_id,
            "raw_line": line,
            "suggestions": [
                {"label": s.label, "score": s.score} for s in suggestions
            ],
            "resolved": False,
            "created_at": datetime.now(timezone.utc),
        })
    if docs:
        await pending_review_col().insert_many(docs)
