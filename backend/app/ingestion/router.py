"""
Ingestion router: /api/v1/upload
  POST /upload        — upload a raw config file → returns job_id
  GET  /jobs          — list all jobs for current user
  GET  /jobs/{job_id} — poll job status
"""
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_auth
from app.config import get_settings
from app.database.models import JobStatus, ScanJob, User, VendorType
from app.database.postgres import get_db
from app.ingestion.sanitizer import sanitize
from app.ingestion.schemas import JobListResponse, JobStatusResponse, UploadResponse

router = APIRouter(prefix="/upload", tags=["Ingestion"])
settings = get_settings()


# ── Background processing task ────────────────────────────────────────────────

async def _process_job(job_id: uuid.UUID, raw_text: str, vendor: str) -> None:
    """
    Full async normalization pipeline run as a background task.
    Imports are deferred to avoid circular deps at import time.
    """
    from app.database.mongo import normalized_configs_col, raw_configs_col
    from app.database.postgres import AsyncSessionLocal
    from app.normalization.ast_builder import build_ast
    from app.normalization.genie_engine import genie_parse
    from app.normalization.textfsm_engine import textfsm_parse
    from app.normalization.normalizer import map_to_universal_schema

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ScanJob).where(ScanJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return

        try:
            job.status = JobStatus.PROCESSING
            await db.flush()

            # 1. Store raw sanitized text in MongoDB
            raw_doc = await raw_configs_col().insert_one({
                "job_id": str(job_id),
                "vendor": vendor,
                "content": raw_text,
                "created_at": datetime.now(timezone.utc),
            })
            job.mongo_raw_id = str(raw_doc.inserted_id)

            # 2. Build AST
            ast = build_ast(raw_text, vendor)

            # 3. Attempt TextFSM parse → fallback to Genie → flag unknowns
            parsed, unknown_lines = textfsm_parse(raw_text, vendor)
            if not parsed:
                parsed, unknown_lines = genie_parse(raw_text, vendor)

            # 4. Map to universal schema (merges AST + structured parsed data)
            normalized, flagged = map_to_universal_schema(ast, parsed, vendor)

            # Combine flagged lines with unmatched unknown lines
            all_review_lines = list(dict.fromkeys((flagged or []) + [l for l in (unknown_lines or []) if len(l.strip()) > 6]))[:50]

            # 5. Store normalized JSON in MongoDB
            norm_doc = await normalized_configs_col().insert_one({
                "job_id": str(job_id),
                "vendor": vendor,
                "normalized": normalized.model_dump(),
                "flagged_lines": all_review_lines,
                "created_at": datetime.now(timezone.utc),
            })
            job.mongo_normalized_id = str(norm_doc.inserted_id)

            # Queue unknown syntax lines into pending_review collection for AI training loop
            if all_review_lines:
                from app.ai_engine.training_loop import queue_for_review
                await queue_for_review(str(job_id), all_review_lines[:20])

            # 6. Update job status
            if all_review_lines:
                job.status = JobStatus.REVIEW_REQUIRED
            else:
                job.status = JobStatus.NORMALIZED
            job.completed_at = datetime.now(timezone.utc)

        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            job.completed_at = datetime.now(timezone.utc)

        await db.commit()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_config(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """
    Upload a raw network device config file (.txt / .cfg).
    Returns a job_id to poll for processing status.
    """
    # Size check
    contents = await file.read()
    if len(contents) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {settings.max_upload_size_mb} MB.",
        )

    raw_text = contents.decode("utf-8", errors="replace")

    # Sanitize
    result = sanitize(raw_text)

    # Persist raw file to disk (audit trail)
    upload_path = Path(settings.upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4()
    save_path = upload_path / f"{file_id}.cfg"
    save_path.write_text(result.clean_text, encoding="utf-8")

    # Create ScanJob in PostgreSQL
    job = ScanJob(
        owner_id=user.id,
        original_filename=file.filename or "unknown.cfg",
        vendor=VendorType(result.vendor.value),
        status=JobStatus.PENDING,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    # Kick off background normalization
    background_tasks.add_task(_process_job, job.id, result.clean_text, result.vendor.value)

    return UploadResponse(
        job_id=job.id,
        message="File accepted and queued for processing.",
        detected_vendor=result.vendor.value,
        original_filename=file.filename or "unknown.cfg",
        original_lines=result.original_line_count,
        clean_lines=result.clean_line_count,
        redacted_secrets=result.redacted_count,
    )


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """List all scan jobs belonging to the current user."""
    result = await db.execute(
        select(ScanJob)
        .where(ScanJob.owner_id == user.id)
        .order_by(ScanJob.created_at.desc())
    )
    jobs = result.scalars().all()
    return JobListResponse(total=len(jobs), jobs=jobs)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Poll the status and metadata of a specific scan job."""
    result = await db.execute(
        select(ScanJob).where(ScanJob.id == job_id, ScanJob.owner_id == user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job
