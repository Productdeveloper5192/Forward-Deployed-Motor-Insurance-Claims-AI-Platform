from datetime import date

from app.db.database import SessionLocal
from app.models.policy import Policy, PolicyStatus
from app.workflow.state import ClaimWorkflowState


def run(state: ClaimWorkflowState) -> dict:
    """Deterministic policy lookup — no LLM call needed for a straight DB read."""
    db = SessionLocal()
    try:
        policy = db.query(Policy).filter(Policy.policy_number == state["policy_number"]).first()
        if policy is None:
            return {
                "policy_verification": {
                    "found": False,
                    "active": False,
                    "issues": ["Policy number not found in claims system."],
                }
            }

        incident_date = date.fromisoformat(state["incident_date"])
        within_period = policy.effective_date <= incident_date <= policy.expiration_date
        active = policy.status == PolicyStatus.ACTIVE

        issues = []
        if not active:
            issues.append(f"Policy status is '{policy.status.value}', not active.")
        if not within_period:
            issues.append("Incident date falls outside the policy's coverage period.")

        return {
            "policy_verification": {
                "found": True,
                "active": active and within_period,
                "policy_status": policy.status.value,
                "holder_name": policy.holder_name,
                "vehicle_vin": policy.vehicle_vin,
                "vehicle_description": f"{policy.vehicle_year} {policy.vehicle_make} {policy.vehicle_model}",
                "coverage_type": policy.coverage_type,
                "coverage_limit": policy.coverage_limit,
                "deductible": policy.deductible,
                "effective_date": policy.effective_date.isoformat(),
                "expiration_date": policy.expiration_date.isoformat(),
                "issues": issues,
            }
        }
    finally:
        db.close()
