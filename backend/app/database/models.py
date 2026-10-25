"""
SQLAlchemy ORM models for PostgreSQL (relational data).
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    AUDITOR = "auditor"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    NORMALIZED = "normalized"         # Normalization done, awaiting compliance run
    REVIEW_REQUIRED = "review_required"  # Unknown syntax flagged for AI training
    COMPLETED = "completed"
    FAILED = "failed"


class VendorType(str, enum.Enum):
    CISCO_IOS = "cisco_ios"
    CISCO_NXOS = "cisco_nxos"
    PALOALTO = "paloalto"
    JUNOS = "junos"
    SONIC = "sonic"
    UNKNOWN = "unknown"


class RuleType(str, enum.Enum):
    REGEX = "regex"
    SEMANTIC = "semantic"


class FrameworkType(str, enum.Enum):
    CIS = "cis"
    NIST = "nist"
    STIG = "stig"


# ─────────────────────────────────────────────────────────────────────────────
# User
# ─────────────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.AUDITOR, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    scan_jobs: Mapped[list["ScanJob"]] = relationship("ScanJob", back_populates="owner")
    mapping_rules: Mapped[list["MappingRule"]] = relationship("MappingRule", back_populates="created_by_user")


# ─────────────────────────────────────────────────────────────────────────────
# Scan Job
# ─────────────────────────────────────────────────────────────────────────────

class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor: Mapped[VendorType] = mapped_column(Enum(VendorType), default=VendorType.UNKNOWN)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.PENDING)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    compliance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    framework: Mapped[FrameworkType | None] = mapped_column(Enum(FrameworkType), nullable=True)
    # MongoDB document IDs
    mongo_raw_id: Mapped[str | None] = mapped_column(String(24), nullable=True)
    mongo_normalized_id: Mapped[str | None] = mapped_column(String(24), nullable=True)
    mongo_scan_id: Mapped[str | None] = mapped_column(String(24), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="scan_jobs")


# ─────────────────────────────────────────────────────────────────────────────
# AI Mapping Rule (heuristic DB)
# ─────────────────────────────────────────────────────────────────────────────

class MappingRule(Base):
    __tablename__ = "mapping_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    raw_pattern: Mapped[str] = mapped_column(Text, nullable=False)
    mapped_param: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_type: Mapped[RuleType] = mapped_column(Enum(RuleType), default=RuleType.SEMANTIC)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    created_by_user: Mapped["User | None"] = relationship("User", back_populates="mapping_rules")
