from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.security import hash_password
from app.db.database import get_db
from app.models.audit import AuditLog
from app.models.claim import Claim, ClaimStatus
from app.models.policy import Policy
from app.models.user import User, UserRole
from app.schemas.auth import StaffUserCreate, UserOut
from app.schemas.policy import PolicyCreate, PolicyOut

router = APIRouter(prefix="/admin", tags=["admin"])


class AuditLogOut(BaseModel):
    id: int
    claim_id: int | None
    user_id: int | None
    action: str
    details: str | None
    created_at: str

    model_config = {"from_attributes": True}


@router.post("/policies", response_model=PolicyOut, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: PolicyCreate,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    if db.query(Policy).filter(Policy.policy_number == payload.policy_number).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Policy number already exists")
    policy = Policy(**payload.model_dump())
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return PolicyOut.model_validate(policy)


@router.get("/policies", response_model=list[PolicyOut])
def list_policies(_: User = Depends(require_roles(UserRole.ADMIN)), db: Session = Depends(get_db)):
    return [PolicyOut.model_validate(p) for p in db.query(Policy).all()]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_staff_user(
    payload: StaffUserCreate,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Provision an adjuster or admin account. Deliberately separate from the
    public /auth/register endpoint — only an existing admin can grant staff
    roles, closing the self-service privilege-escalation path."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.get("/users", response_model=list[UserOut])
def list_users(_: User = Depends(require_roles(UserRole.ADMIN)), db: Session = Depends(get_db)):
    return [UserOut.model_validate(u) for u in db.query(User).order_by(User.created_at.desc()).all()]


@router.get("/audit-log", response_model=list[AuditLogOut])
def list_audit_log(
    claim_id: int | None = None,
    limit: int = 200,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if claim_id is not None:
        query = query.filter(AuditLog.claim_id == claim_id)
    entries = query.order_by(AuditLog.created_at.desc()).limit(min(limit, 500)).all()
    return [
        AuditLogOut(
            id=e.id,
            claim_id=e.claim_id,
            user_id=e.user_id,
            action=e.action,
            details=e.details,
            created_at=e.created_at.isoformat(),
        )
        for e in entries
    ]


@router.get("/evaluation")
def evaluation_metrics(_: User = Depends(require_roles(UserRole.ADMIN)), db: Session = Depends(get_db)):
    """Continuous-evaluation view: how often the AI recommendation and the
    deterministic rules engine agreed, and — for claims a human has already
    reviewed — how often the human agreed with the AI recommendation."""
    total_claims = db.query(func.count(Claim.id)).scalar() or 0
    by_status = dict(
        db.query(Claim.status, func.count(Claim.id)).group_by(Claim.status).all()
    )

    processed = db.query(Claim).filter(Claim.ai_recommendation.isnot(None)).all()
    ai_rules_agree = sum(
        1
        for c in processed
        if (c.ai_recommendation == "approve" and c.rules_decision == "auto_approve")
        or (c.ai_recommendation == "deny" and c.rules_decision == "deny")
        or (c.ai_recommendation == "manual_review" and c.rules_decision == "manual_review")
    )

    reviewed = [
        c for c in processed if c.status in (ClaimStatus.APPROVED, ClaimStatus.DENIED) and c.reviewed_by_id
    ]
    ai_human_agree = sum(
        1
        for c in reviewed
        if (c.ai_recommendation == "approve" and c.status == ClaimStatus.APPROVED)
        or (c.ai_recommendation == "deny" and c.status == ClaimStatus.DENIED)
    )

    avg_fraud_score = db.query(func.avg(Claim.fraud_score)).filter(Claim.fraud_score.isnot(None)).scalar()

    return {
        "total_claims": total_claims,
        "claims_by_status": {status.value: count for status, count in by_status.items()},
        "workflow_processed_count": len(processed),
        "ai_rules_engine_agreement_rate": round(ai_rules_agree / len(processed), 3) if processed else None,
        "human_reviewed_count": len(reviewed),
        "ai_human_agreement_rate": round(ai_human_agree / len(reviewed), 3) if reviewed else None,
        "average_fraud_score": round(avg_fraud_score, 1) if avg_fraud_score is not None else None,
    }
