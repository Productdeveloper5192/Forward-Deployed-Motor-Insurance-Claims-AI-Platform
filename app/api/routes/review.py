from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.database import get_db
from app.models.claim import Claim, ClaimStatus
from app.models.user import User, UserRole
from app.schemas.claim import ClaimOut, ReviewDecision
from app.services import audit_log, notifications

router = APIRouter(prefix="/review", tags=["review"])

_ADJUSTER_ROLES = (UserRole.ADJUSTER, UserRole.ADMIN)


@router.get("/queue", response_model=list[ClaimOut])
def review_queue(user: User = Depends(require_roles(*_ADJUSTER_ROLES)), db: Session = Depends(get_db)):
    claims = (
        db.query(Claim)
        .filter(Claim.status == ClaimStatus.NEEDS_REVIEW)
        .order_by(Claim.created_at.asc())
        .all()
    )
    return [ClaimOut.model_validate(c) for c in claims]


@router.post("/{claim_id}/decision", response_model=ClaimOut)
def submit_decision(
    claim_id: int,
    payload: ReviewDecision,
    user: User = Depends(require_roles(*_ADJUSTER_ROLES)),
    db: Session = Depends(get_db),
):
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Claim not found")
    if claim.status != ClaimStatus.NEEDS_REVIEW:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Claim is not awaiting review")
    if payload.decision not in ("approved", "denied"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "decision must be 'approved' or 'denied'")

    claim.status = ClaimStatus.APPROVED if payload.decision == "approved" else ClaimStatus.DENIED
    claim.approved_amount = payload.approved_amount if payload.decision == "approved" else 0.0
    claim.reviewed_by_id = user.id
    claim.review_notes = payload.notes
    db.commit()
    db.refresh(claim)

    audit_log.record(
        db,
        "claim_reviewed",
        claim_id=claim_id,
        user_id=user.id,
        details=f"decision={payload.decision} amount={payload.approved_amount} notes={payload.notes}",
    )
    notifications.notify(
        db,
        f"Claim {claim.claim_number} has been {payload.decision} by an adjuster.",
        claim_id=claim_id,
        user_id=claim.customer_id,
    )
    return ClaimOut.model_validate(claim)
