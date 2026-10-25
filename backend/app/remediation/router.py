"""
Remediation router: /api/v1/remediation
  POST /generate — generate remediation runbook for a completed scan
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_auth
from app.compliance.engine import ComplianceFinding, ComplianceStatus
from app.database.models import ScanJob, User
from app.database.mongo import compliance_scans_col, normalized_configs_col
from app.database.postgres import get_db
from app.normalization.universal_schema import SecurityBaselineModel
from app.remediation.generator import RemediationItem, generate_remediation

router = APIRouter(prefix="/remediation", tags=["Remediation"])


class RemediationRequest(BaseModel):
    job_id: uuid.UUID


class RemediationItemOut(BaseModel):
    control_id: str
    title: str
    severity: str
    param_path: str
    cli_commands: str
    expected: object
    actual: object


class RemediationResponse(BaseModel):
    job_id: uuid.UUID
    vendor: str
    framework: str
    total_issues: int
    critical_count: int
    high_count: int
    items: list[RemediationItemOut]


@router.post("/generate", response_model=RemediationResponse)
async def generate(
    body: RemediationRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Generate a prioritized remediation runbook for all FAIL/WARN findings."""
    result = await db.execute(
        select(ScanJob).where(ScanJob.id == body.job_id, ScanJob.owner_id == user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if not job.mongo_scan_id:
        raise HTTPException(status_code=422, detail="No compliance scan found. Run /compliance/check first.")

    from bson import ObjectId  # type: ignore
    scan_doc = await compliance_scans_col().find_one({"_id": ObjectId(job.mongo_scan_id)})
    if not scan_doc:
        raise HTTPException(status_code=404, detail="Compliance scan document not found.")

    # Reconstruct ComplianceFinding objects from stored scan data
    findings: list[ComplianceFinding] = []
    for f in scan_doc.get("findings", []):
        findings.append(ComplianceFinding(
            control_id=f["control_id"],
            title=f["title"],
            description=f["description"],
            severity=f["severity"],
            status=ComplianceStatus(f["status"]),
            expected=f["expected"],
            actual=f["actual"],
            remediation_hint=f["remediation_hint"],
            param_path=f["param_path"],
        ))

    vendor = job.vendor.value
    items = generate_remediation(findings, vendor)

    return RemediationResponse(
        job_id=body.job_id,
        vendor=vendor,
        framework=scan_doc["framework"],
        total_issues=len(items),
        critical_count=sum(1 for i in items if i.severity == "CRITICAL"),
        high_count=sum(1 for i in items if i.severity == "HIGH"),
        items=[
            RemediationItemOut(
                control_id=i.control_id,
                title=i.title,
                severity=i.severity,
                param_path=i.param_path,
                cli_commands=i.cli_commands,
                expected=i.expected,
                actual=i.actual,
            )
            for i in items
        ],
    )
