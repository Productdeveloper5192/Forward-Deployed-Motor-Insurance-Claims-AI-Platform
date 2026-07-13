"""Claims-system tools exposed to the LangGraph agents via Claude tool use.

Each tool opens its own short-lived DB session rather than sharing the
request-scoped session, since these run inside the Anthropic tool-runner's
synchronous call loop from a background worker thread.
"""

import json

from anthropic import beta_tool

from app.db.database import SessionLocal
from app.models.claim import Claim
from app.models.policy import Policy


@beta_tool
def policy_lookup(policy_number: str) -> str:
    """Look up a policy record by its policy number in the claims system.

    Args:
        policy_number: The policy number to look up, e.g. POL-10001.
    """
    db = SessionLocal()
    try:
        policy = db.query(Policy).filter(Policy.policy_number == policy_number).first()
        if policy is None:
            return json.dumps({"found": False})
        return json.dumps(
            {
                "found": True,
                "holder_name": policy.holder_name,
                "vehicle": f"{policy.vehicle_year} {policy.vehicle_make} {policy.vehicle_model}",
                "vehicle_vin": policy.vehicle_vin,
                "coverage_type": policy.coverage_type,
                "coverage_limit": policy.coverage_limit,
                "deductible": policy.deductible,
                "status": policy.status.value,
                "effective_date": policy.effective_date.isoformat(),
                "expiration_date": policy.expiration_date.isoformat(),
            }
        )
    finally:
        db.close()


@beta_tool
def claims_history_lookup(policy_number: str) -> str:
    """Look up recent claim history for a policy to check for repeat or suspicious filing patterns.

    Args:
        policy_number: The policy number whose claim history should be checked.
    """
    db = SessionLocal()
    try:
        policy = db.query(Policy).filter(Policy.policy_number == policy_number).first()
        if policy is None:
            return json.dumps({"found": False})
        claims = db.query(Claim).filter(Claim.policy_id == policy.id).all()
        history = [
            {
                "claim_number": c.claim_number,
                "status": c.status.value,
                "incident_date": c.incident_date.isoformat(),
                "estimated_amount": c.estimated_amount,
                "fraud_score": c.fraud_score,
            }
            for c in claims
        ]
        return json.dumps({"found": True, "claim_count": len(history), "claims": history})
    finally:
        db.close()


FRAUD_TRIAGE_TOOLS = [policy_lookup, claims_history_lookup]
