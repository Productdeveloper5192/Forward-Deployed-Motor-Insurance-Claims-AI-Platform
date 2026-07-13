import random
import string

from sqlalchemy.orm import Session

from app.models.claim import Claim, ClaimStatus
from app.models.policy import Policy


def generate_claim_number() -> str:
    return "CLM-" + "".join(random.choices(string.digits, k=8))


def create_claim(db: Session, *, customer_id: int, policy_number: str, incident_date, incident_description: str, incident_location: str) -> Claim:
    policy = db.query(Policy).filter(Policy.policy_number == policy_number).first()
    if policy is None:
        raise ValueError(f"No policy found with number {policy_number}")

    claim = Claim(
        claim_number=generate_claim_number(),
        policy_id=policy.id,
        customer_id=customer_id,
        status=ClaimStatus.DRAFT,
        incident_date=incident_date,
        incident_description=incident_description,
        incident_location=incident_location,
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim
