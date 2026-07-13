from dataclasses import asdict
from datetime import date

from app.core.config import settings
from app.rules_engine.engine import RulesEngineInput, evaluate
from app.workflow.state import ClaimWorkflowState


def run(state: ClaimWorkflowState) -> dict:
    policy = state.get("policy_verification", {})
    damage = state.get("damage_analysis", {})
    fraud = state.get("fraud_triage", {})
    cross_val = state.get("cross_validation", {})
    extraction = state.get("extraction", {})

    if not policy.get("found"):
        estimated_amount = 0.0
    else:
        estimated_amount = (
            extraction.get("repair_estimate_amount")
            or damage.get("estimated_repair_cost_high")
            or 0.0
        )

    validation_issues = list(cross_val.get("issues", []))

    inp = RulesEngineInput(
        policy_active=bool(policy.get("active", False)),
        policy_effective_date=date.fromisoformat(policy["effective_date"]) if policy.get("effective_date") else date.min,
        policy_expiration_date=date.fromisoformat(policy["expiration_date"]) if policy.get("expiration_date") else date.min,
        incident_date=date.fromisoformat(state["incident_date"]),
        coverage_limit=policy.get("coverage_limit", 0.0) or 0.0,
        deductible=policy.get("deductible", 0.0) or 0.0,
        estimated_amount=float(estimated_amount),
        fraud_score=int(fraud.get("fraud_score", 0)),
        validation_issues=validation_issues,
        auto_approve_max_amount=settings.auto_approve_max_amount,
        fraud_review_threshold=settings.fraud_review_threshold,
        fraud_deny_threshold=settings.fraud_deny_threshold,
    )
    result = evaluate(inp)
    payload = asdict(result)
    payload["estimated_amount"] = float(estimated_amount)
    return {"rules_engine": payload}
