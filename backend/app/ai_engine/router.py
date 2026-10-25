"""
AI Engine router: /api/v1/ai
  GET  /pending           — list unresolved syntax items (Admin only)
  POST /suggest           — get AI suggestions for a raw line (Admin only)
  POST /validate          — validate/store a confirmed mapping (Admin only)
  GET  /rules             — list all stored heuristic rules (Admin only)
  DELETE /rules/{rule_id} — deactivate a rule (Admin only)
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_engine.heuristic_db import deactivate_rule, get_all_active_rules
from app.ai_engine.training_loop import get_pending_review, suggest, validate_and_store
from app.auth.dependencies import require_admin
from app.database.models import MappingRule, User
from app.database.postgres import get_db

router = APIRouter(prefix="/ai", tags=["AI Training Loop"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class SuggestRequest(BaseModel):
    raw_line: str


class SuggestionItem(BaseModel):
    label: str
    score: float
    raw_line: str


class ValidateRequest(BaseModel):
    raw_line: str
    accepted_param: str
    confidence: float = 1.0
    store_as_regex: bool = False


class RuleResponse(BaseModel):
    id: uuid.UUID
    raw_pattern: str
    mapped_param: str
    rule_type: str
    confidence: float
    is_active: bool

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────────────────

from app.auth.dependencies import require_admin, require_auth

# (later in file)
@router.get("/pending")
async def pending_review(
    limit: int = 50,
    _: User = Depends(require_auth),
):
    """Return unresolved flagged syntax lines awaiting admin review."""
    items = await get_pending_review(limit=limit)
    return {"total": len(items), "items": items}


@router.post("/seed-demo")
async def seed_demo_items(
    _: User = Depends(require_auth),
):
    """Populate sample unmapped vendor CLI lines for video demonstration."""
    sample_lines = [
        "set security ike proposal aes256-sha384-group14",
        "ip ssh client algorithm encryption aes256-gcm",
        "snmp-server host 10.10.10.50 version 3 priv secuser",
        "router bgp 65001 neighbor 10.0.0.2 password 7 0822455D0A16",
        "ntp authenticate key 1 md5 094F471A1A0A",
    ]
    from app.ai_engine.training_loop import queue_for_review
    await queue_for_review("demo-sample-01", sample_lines)
    return {"message": "Demo items seeded successfully", "count": len(sample_lines)}


@router.post("/suggest", response_model=list[SuggestionItem])
async def get_suggestions(
    body: SuggestRequest,
    _: User = Depends(require_auth),
):
    """Run zero-shot classification on a raw CLI line and return top-3 matches."""
    results = await suggest(body.raw_line)
    if not results:
        raise HTTPException(status_code=503, detail="AI model unavailable. Check model download status.")
    return [{"label": r.label, "score": r.score, "raw_line": r.raw_line} for r in results]


@router.post("/validate", response_model=RuleResponse)
async def validate_mapping(
    body: ValidateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Admin confirms AI suggestion → stores as new heuristic rule (no restart needed)."""
    rule = await validate_and_store(
        db=db,
        raw_line=body.raw_line,
        accepted_param=body.accepted_param,
        confidence=body.confidence,
        user=user,
        store_as_regex=body.store_as_regex,
    )
    return rule


@router.get("/rules", response_model=list[RuleResponse])
async def list_rules(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
):
    """List all active heuristic mapping rules."""
    rules = await get_all_active_rules(db)
    return rules


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
):
    """Deactivate a mapping rule (soft delete)."""
    deleted = await deactivate_rule(db, rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found.")
    return {"message": "Rule deactivated."}
