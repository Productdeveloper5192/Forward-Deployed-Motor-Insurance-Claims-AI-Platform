from sqlalchemy.orm import Session

from app.models.audit import Notification


def notify(db: Session, message: str, *, user_id: int | None = None, claim_id: int | None = None, channel: str = "in_app") -> None:
    """Send a notification. MVP substitute for a real email/SMS provider: persists
    to the notifications table so it can be polled by the frontend or listed via API."""
    db.add(Notification(user_id=user_id, claim_id=claim_id, channel=channel, message=message))
    db.commit()
