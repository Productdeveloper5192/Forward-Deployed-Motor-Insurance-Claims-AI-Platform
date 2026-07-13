from app.workflow.claude_client import call_structured
from app.workflow.state import ClaimWorkflowState

SCHEMA = {
    "type": "object",
    "properties": {
        "consistent": {"type": "boolean"},
        "issues": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"},
    },
    "required": ["consistent", "issues", "notes"],
    "additionalProperties": False,
}

SYSTEM = """You are a claims data-consistency auditor. Compare the facts extracted from
the claimant's submitted documents against the policy record on file. Flag genuine
discrepancies (mismatched VIN, mismatched name beyond minor spelling/formatting
differences, incident date inconsistent with what was filed, damages inconsistent with the
narrative). Do NOT flag trivial formatting differences (e.g. "Bob Smith" vs "Robert Smith"
should be flagged as a possible mismatch worth a human look, but "J. Smith" vs "J Smith" is
not an issue). Be conservative — only list an issue if it could plausibly affect the claim
decision."""


def run(state: ClaimWorkflowState) -> dict:
    extraction = state.get("extraction", {})
    policy = state.get("policy_verification", {})

    content = (
        "Facts extracted from claim documents:\n"
        f"- Claimant name: {extraction.get('claimant_name')}\n"
        f"- Vehicle VIN: {extraction.get('vehicle_vin')}\n"
        f"- Vehicle description: {extraction.get('vehicle_description')}\n"
        f"- Police report number: {extraction.get('police_report_number')}\n"
        f"- Incident summary: {extraction.get('incident_summary')}\n\n"
        "Policy record on file:\n"
        f"- Policy holder name: {policy.get('holder_name')}\n"
        f"- Vehicle VIN: {policy.get('vehicle_vin')}\n"
        f"- Vehicle description: {policy.get('vehicle_description')}\n\n"
        "Claim submission (as filed by the claimant):\n"
        f"- Incident date: {state.get('incident_date')}\n"
        f"- Incident description: {state.get('incident_description')}\n\n"
        "Identify any inconsistencies between these three sources."
    )

    result = call_structured(system=SYSTEM, content=content, schema=SCHEMA, effort="medium")
    return {"cross_validation": result}
