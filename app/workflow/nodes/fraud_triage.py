from app.core.config import settings
from app.tools.claims_tools import FRAUD_TRIAGE_TOOLS
from app.workflow.claude_client import call_structured, get_client
from app.workflow.state import ClaimWorkflowState

INVESTIGATION_SYSTEM = """You are a fraud-risk investigator for a motor insurance claims
system. You have tools to look up the policy record and the policyholder's claim history.
Investigate this claim for fraud indicators: inconsistent statements, damage that doesn't
match the narrative, repair estimates far above what the visible damage would cost, a
pattern of frequent claims shortly after policy inception, or documents that appear
contradictory. Use the tools to check the policy and claim history, then write a concise
plain-language fraud-risk assessment covering what you found and how concerning it is.
This is an investigative assessment, not a final decision — a human adjuster makes the
final call."""

SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        "fraud_score": {"type": "integer"},
        "risk_factors": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
    },
    "required": ["fraud_score", "risk_factors", "reasoning"],
    "additionalProperties": False,
}

SCORE_SYSTEM = """Convert the fraud investigation write-up below into a fraud_score from 0
(no fraud indicators) to 100 (overwhelming evidence of fraud). Most legitimate claims should
score under 30. Only score above 60 when there are multiple concrete, named risk factors."""


def run(state: ClaimWorkflowState) -> dict:
    extraction = state.get("extraction", {})
    damage = state.get("damage_analysis", {})
    cross_val = state.get("cross_validation", {})

    briefing = (
        f"Policy number: {state.get('policy_number')}\n"
        f"Incident description: {state.get('incident_description')}\n"
        f"Incident date: {state.get('incident_date')}\n"
        f"Extracted claim facts: {extraction}\n"
        f"Damage analysis: {damage}\n"
        f"Cross-document validation findings: {cross_val}\n\n"
        "Investigate this claim using the available tools, then summarize your fraud-risk findings."
    )

    client = get_client()
    runner = client.beta.messages.tool_runner(
        model=settings.claude_model,
        max_tokens=4096,
        tools=FRAUD_TRIAGE_TOOLS,
        messages=[{"role": "user", "content": briefing}],
        system=INVESTIGATION_SYSTEM,
    )

    final_message = None
    for message in runner:
        final_message = message

    investigation_text = ""
    if final_message is not None:
        investigation_text = "\n".join(
            block.text for block in final_message.content if getattr(block, "type", None) == "text"
        )
    if not investigation_text:
        investigation_text = "No fraud indicators could be assessed (investigation produced no output)."

    scored = call_structured(
        system=SCORE_SYSTEM,
        content=f"Fraud investigation write-up:\n\n{investigation_text}",
        schema=SCORE_SCHEMA,
        effort="medium",
    )
    scored["investigation_notes"] = investigation_text
    scored["fraud_score"] = max(0, min(100, int(scored["fraud_score"])))
    return {"fraud_triage": scored}
