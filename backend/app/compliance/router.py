"""
Compliance router: /api/v1/compliance
  POST /check    — run compliance check on a completed job
  GET  /{job_id} — retrieve cached compliance results
"""
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_auth
from app.compliance.engine import ComplianceFinding, run_compliance_check
from app.database.models import FrameworkType, JobStatus, ScanJob, User
from app.database.mongo import compliance_scans_col, normalized_configs_col
from app.database.postgres import get_db
from app.normalization.universal_schema import SecurityBaselineModel

router = APIRouter(prefix="/compliance", tags=["Compliance"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class ComplianceCheckRequest(BaseModel):
    job_id: uuid.UUID
    framework: Literal["cis", "nist", "stig"]


class FindingOut(BaseModel):
    control_id: str
    title: str
    description: str
    severity: str
    status: str
    expected: object
    actual: object
    remediation_hint: str
    param_path: str


class ComplianceCheckResponse(BaseModel):
    job_id: uuid.UUID
    framework: str
    score: float
    total_controls: int
    passed: int
    failed: int
    warned: int
    not_applicable: int
    findings: list[FindingOut]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/check", response_model=ComplianceCheckResponse)
async def run_check(
    body: ComplianceCheckRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Run a compliance check against the normalized config for a completed job."""
    result = await db.execute(
        select(ScanJob).where(ScanJob.id == body.job_id, ScanJob.owner_id == user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status not in (JobStatus.NORMALIZED, JobStatus.COMPLETED, JobStatus.REVIEW_REQUIRED):
        raise HTTPException(
            status_code=422,
            detail=f"Job status is '{job.status.value}'. Must be normalized before compliance check.",
        )

    # Load normalized JSON from MongoDB
    if not job.mongo_normalized_id:
        raise HTTPException(status_code=422, detail="Normalized config not found in document store.")

    from bson import ObjectId  # type: ignore
    norm_doc = await normalized_configs_col().find_one({"_id": ObjectId(job.mongo_normalized_id)})
    if not norm_doc:
        raise HTTPException(status_code=404, detail="Normalized config document not found.")

    model = SecurityBaselineModel(**norm_doc["normalized"])

    # Run compliance engine
    findings, score = run_compliance_check(model, body.framework)

    # Persist findings to MongoDB
    scan_doc = {
        "job_id": str(body.job_id),
        "framework": body.framework,
        "score": score,
        "findings": [
            {
                "control_id": f.control_id,
                "title": f.title,
                "description": f.description,
                "severity": f.severity,
                "status": f.status.value,
                "expected": f.expected,
                "actual": str(f.actual),
                "remediation_hint": f.remediation_hint,
                "param_path": f.param_path,
            }
            for f in findings
        ],
        "created_at": datetime.now(timezone.utc),
    }
    scan_result = await compliance_scans_col().insert_one(scan_doc)

    # Update PostgreSQL job record
    job.compliance_score = score
    job.framework = FrameworkType(body.framework)
    job.status = JobStatus.COMPLETED
    job.mongo_scan_id = str(scan_result.inserted_id)
    await db.flush()

    # Build response
    passed = sum(1 for f in findings if f.status.value == "PASS")
    failed = sum(1 for f in findings if f.status.value == "FAIL")
    warned = sum(1 for f in findings if f.status.value == "WARN")
    na = sum(1 for f in findings if f.status.value == "N/A")

    return ComplianceCheckResponse(
        job_id=body.job_id,
        framework=body.framework,
        score=score,
        total_controls=len(findings),
        passed=passed,
        failed=failed,
        warned=warned,
        not_applicable=na,
        findings=[
            FindingOut(
                control_id=f.control_id,
                title=f.title,
                description=f.description,
                severity=f.severity,
                status=f.status.value,
                expected=f.expected,
                actual=f.actual,
                remediation_hint=f.remediation_hint,
                param_path=f.param_path,
            )
            for f in findings
        ],
    )


@router.get("/{job_id}", response_model=ComplianceCheckResponse)
async def get_compliance_results(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Retrieve cached compliance scan results for a job."""
    result = await db.execute(
        select(ScanJob).where(ScanJob.id == job_id, ScanJob.owner_id == user.id)
    )
    job = result.scalar_one_or_none()
    if not job or not job.mongo_scan_id:
        raise HTTPException(status_code=404, detail="Compliance scan not found.")

    from bson import ObjectId  # type: ignore
    scan_doc = await compliance_scans_col().find_one({"_id": ObjectId(job.mongo_scan_id)})
    if not scan_doc:
        raise HTTPException(status_code=404, detail="Compliance scan document not found.")

    findings_raw = scan_doc.get("findings", [])
    passed = sum(1 for f in findings_raw if f["status"] == "PASS")
    failed = sum(1 for f in findings_raw if f["status"] == "FAIL")
    warned = sum(1 for f in findings_raw if f["status"] == "WARN")
    na = sum(1 for f in findings_raw if f["status"] == "N/A")

    return ComplianceCheckResponse(
        job_id=job_id,
        framework=scan_doc["framework"],
        score=scan_doc["score"],
        total_controls=len(findings_raw),
        passed=passed,
        failed=failed,
        warned=warned,
        not_applicable=na,
        findings=[FindingOut(**f) for f in findings_raw],
    )
