from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def record(db: Session, action: str, *, claim_id: int | None = None, user_id: int | None = None, details: str = "") -> None:
    db.add(AuditLog(claim_id=claim_id, user_id=user_id, action=action, details=details))
    db.commit()
