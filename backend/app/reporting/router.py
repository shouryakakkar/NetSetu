"""
Reporting router: /api/v1/report
  GET /pdf/{job_id}?framework=cis — stream a compliance PDF report
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_auth
from app.database.models import ScanJob, User
from app.database.mongo import compliance_scans_col, normalized_configs_col
from app.database.postgres import get_db
from app.reporting.pdf_builder import build_pdf

router = APIRouter(prefix="/report", tags=["Reporting"])


@router.get("/pdf/{job_id}")
async def download_pdf(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Generate and stream a PDF compliance report for a completed scan job."""
    result = await db.execute(
        select(ScanJob).where(ScanJob.id == job_id, ScanJob.owner_id == user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if not job.mongo_scan_id:
        raise HTTPException(status_code=422, detail="No compliance scan available. Run a compliance check first.")

    from bson import ObjectId  # type: ignore

    # Load compliance scan from MongoDB
    scan_doc = await compliance_scans_col().find_one({"_id": ObjectId(job.mongo_scan_id)})
    if not scan_doc:
        raise HTTPException(status_code=404, detail="Compliance scan not found.")

    # Load normalized JSON (optional — for appendix)
    normalized_json = None
    if job.mongo_normalized_id:
        norm_doc = await normalized_configs_col().find_one({"_id": ObjectId(job.mongo_normalized_id)})
        if norm_doc:
            normalized_json = norm_doc.get("normalized")

    findings = scan_doc.get("findings", [])
    passed = sum(1 for f in findings if f["status"] == "PASS")
    failed = sum(1 for f in findings if f["status"] == "FAIL")
    warned = sum(1 for f in findings if f["status"] == "WARN")
    na = sum(1 for f in findings if f["status"] == "N/A")

    meta = {
        "hostname": None,  # Will be filled from normalized JSON if available
        "vendor": job.vendor.value if job.vendor else "unknown",
        "framework": scan_doc.get("framework", job.framework.value if job.framework else ""),
        "scan_date": scan_doc.get("created_at", datetime.utcnow()).strftime("%Y-%m-%d %H:%M UTC")
        if hasattr(scan_doc.get("created_at", ""), "strftime")
        else str(scan_doc.get("created_at", datetime.utcnow())),
        "score": scan_doc.get("score", 0.0),
        "total_controls": len(findings),
        "passed": passed,
        "failed": failed,
        "warned": warned,
        "not_applicable": na,
        "audited_by": user.username,
    }

    # Extract hostname from normalized config
    if normalized_json:
        meta["hostname"] = normalized_json.get("hostname", job.original_filename)
    else:
        meta["hostname"] = job.original_filename

    # Build PDF bytes
    pdf_bytes = build_pdf(
        meta=meta,
        findings=findings,
        normalized_json=normalized_json,
    )

    filename = f"compliance_report_{job_id}_{meta['framework']}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )
