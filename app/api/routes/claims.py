from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.database import get_db
from app.models.claim import Claim, ClaimStatus
from app.models.document import Document, DocumentType
from app.models.user import User, UserRole
from app.schemas.claim import ClaimCreate, ClaimOut, WorkflowRunOut
from app.services import audit_log, claims_intake, notifications, storage
from app.workers.tasks import submit_claim_processing

router = APIRouter(prefix="/claims", tags=["claims"])


def _ensure_can_view(claim: Claim, user: User) -> None:
    if user.role == UserRole.CUSTOMER and claim.customer_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have access to this claim")


@router.post("", response_model=ClaimOut, status_code=status.HTTP_201_CREATED)
def create_claim(
    payload: ClaimCreate,
    user: User = Depends(require_roles(UserRole.CUSTOMER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    try:
        claim = claims_intake.create_claim(
            db,
            customer_id=user.id,
            policy_number=payload.policy_number,
            incident_date=payload.incident_date,
            incident_description=payload.incident_description,
            incident_location=payload.incident_location,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))

    audit_log.record(db, "claim_created", claim_id=claim.id, user_id=user.id)
    return ClaimOut.model_validate(claim)


@router.get("", response_model=list[ClaimOut])
def list_claims(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Claim)
    if user.role == UserRole.CUSTOMER:
        query = query.filter(Claim.customer_id == user.id)
    claims = query.order_by(Claim.created_at.desc()).all()
    return [ClaimOut.model_validate(c) for c in claims]


@router.get("/{claim_id}", response_model=ClaimOut)
def get_claim(claim_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Claim not found")
    _ensure_can_view(claim, user)
    return ClaimOut.model_validate(claim)


@router.post("/{claim_id}/documents", response_model=ClaimOut)
async def upload_document(
    claim_id: int,
    doc_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Claim not found")
    _ensure_can_view(claim, user)
    if claim.status != ClaimStatus.DRAFT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Documents can only be added while the claim is in draft")

    content = await file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file is empty")

    dest = storage.save_upload(claim_id, file.filename or "upload", content)
    doc = Document(
        claim_id=claim_id,
        doc_type=doc_type,
        file_path=str(dest),
        original_filename=file.filename or dest.name,
        mime_type=file.content_type or "application/octet-stream",
    )
    db.add(doc)
    db.commit()
    db.refresh(claim)

    audit_log.record(db, "document_uploaded", claim_id=claim_id, user_id=user.id, details=doc.original_filename)
    return ClaimOut.model_validate(claim)


@router.post("/{claim_id}/submit", response_model=ClaimOut)
def submit_claim(claim_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Claim not found")
    _ensure_can_view(claim, user)
    if claim.status != ClaimStatus.DRAFT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Claim has already been submitted")

    claim.status = ClaimStatus.SUBMITTED
    db.commit()
    db.refresh(claim)

    audit_log.record(db, "claim_submitted", claim_id=claim_id, user_id=user.id)
    notifications.notify(
        db, f"Claim {claim.claim_number} submitted and is being processed.", claim_id=claim_id, user_id=user.id
    )

    submit_claim_processing(claim_id)
    return ClaimOut.model_validate(claim)


@router.get("/{claim_id}/workflow", response_model=list[WorkflowRunOut])
def get_claim_workflow(claim_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Claim not found")
    _ensure_can_view(claim, user)
    return [WorkflowRunOut.model_validate(r) for r in claim.workflow_runs]


@router.post("/{claim_id}/pay", response_model=ClaimOut)
def pay_claim(
    claim_id: int,
    user: User = Depends(require_roles(UserRole.ADJUSTER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Claim not found")
    if claim.status != ClaimStatus.APPROVED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only an approved claim can be marked as paid")

    claim.status = ClaimStatus.PAID
    claim.paid_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(claim)

    audit_log.record(
        db, "claim_paid", claim_id=claim_id, user_id=user.id, details=f"amount={claim.approved_amount}"
    )
    notifications.notify(
        db,
        f"Claim {claim.claim_number} has been paid out (${claim.approved_amount:,.2f}).",
        claim_id=claim_id,
        user_id=claim.customer_id,
    )
    return ClaimOut.model_validate(claim)
