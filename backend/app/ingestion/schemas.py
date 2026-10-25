"""Pydantic schemas for ingestion endpoints."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    job_id: uuid.UUID
    message: str
    detected_vendor: str
    original_filename: str
    original_lines: int
    clean_lines: int
    redacted_secrets: int


class JobStatusResponse(BaseModel):
    job_id: uuid.UUID = Field(validation_alias="id")
    status: str
    vendor: str
    original_filename: str
    compliance_score: float | None
    framework: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class JobListResponse(BaseModel):
    total: int
    jobs: list[JobStatusResponse]
