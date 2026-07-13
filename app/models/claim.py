import enum
from datetime import date, datetime, timezone

from sqlalchemy import DateTime, Date, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ClaimStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    DENIED = "denied"
    PAID = "paid"
    FAILED = "failed"


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("policies.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[ClaimStatus] = mapped_column(Enum(ClaimStatus), default=ClaimStatus.DRAFT)

    incident_date: Mapped[date] = mapped_column(Date)
    incident_description: Mapped[str] = mapped_column(Text)
    incident_location: Mapped[str] = mapped_column(String(255), default="")

    estimated_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    approved_amount: Mapped[float | None] = mapped_column(Float, nullable=True)

    ai_recommendation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ai_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    fraud_score: Mapped[int | None] = mapped_column(nullable=True)
    rules_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rules_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    policy: Mapped["Policy"] = relationship(back_populates="claims")
    customer: Mapped["User"] = relationship(back_populates="claims", foreign_keys=[customer_id])
    documents: Mapped[list["Document"]] = relationship(back_populates="claim", cascade="all, delete-orphan")
    workflow_runs: Mapped[list["WorkflowRun"]] = relationship(back_populates="claim", cascade="all, delete-orphan")
