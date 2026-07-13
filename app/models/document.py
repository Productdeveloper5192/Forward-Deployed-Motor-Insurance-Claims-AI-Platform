import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class DocumentType(str, enum.Enum):
    POLICE_REPORT = "police_report"
    DAMAGE_PHOTO = "damage_photo"
    ID_PROOF = "id_proof"
    REPAIR_ESTIMATE = "repair_estimate"
    OTHER = "other"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id"))
    doc_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType), default=DocumentType.OTHER)
    file_path: Mapped[str] = mapped_column(String(512))
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(128))
    extracted_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    claim: Mapped["Claim"] = relationship(back_populates="documents")
