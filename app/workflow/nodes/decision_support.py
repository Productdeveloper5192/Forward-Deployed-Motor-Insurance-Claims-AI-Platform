from app.workflow.claude_client import call_structured
from app.workflow.state import ClaimWorkflowState

SCHEMA = {
    "type": "object",
    "properties": {
        "recommendation": {"type": "string", "enum": ["approve", "deny", "manual_review"]},
        "rationale": {"type": "string"},
        "suggested_payout": {"type": ["number", "null"]},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    },
    "required": ["recommendation", "rationale", "suggested_payout", "confidence"],
    "additionalProperties": False,
}

SYSTEM = """You are a claims decision-support analyst. You synthesize the outputs of the
upstream analysis stages (document extraction, policy verification, policy coverage
research, cross-document validation, damage analysis, and fraud triage) into a single
recommendation for a human adjuster: approve, deny, or manual_review. This is advisory
only — a deterministic rules engine and a human adjuster make the binding decision, so
favor manual_review whenever there is meaningful uncertainty, a validation issue, or an
elevated fraud score. Explain your reasoning referencing the specific upstream findings
that drove it."""


def run(state: ClaimWorkflowState) -> dict:
    content = (
        f"Policy verification: {state.get('policy_verification')}\n\n"
        f"Policy coverage research: {state.get('policy_rag')}\n\n"
        f"Cross-document validation: {state.get('cross_validation')}\n\n"
        f"Damage analysis: {state.get('damage_analysis')}\n\n"
        f"Fraud risk triage: {state.get('fraud_triage')}\n\n"
        "Produce your recommendation."
    )
    result = call_structured(system=SYSTEM, content=content, schema=SCHEMA, effort="high", use_thinking=True)
    return {"decision_support": result}
