from app.workflow.claude_client import call_structured
from app.workflow.retrieval import retrieve
from app.workflow.state import ClaimWorkflowState

SCHEMA = {
    "type": "object",
    "properties": {
        "is_likely_covered": {"type": "boolean"},
        "applicable_clauses": {"type": "array", "items": {"type": "string"}},
        "deductible_note": {"type": "string"},
        "exclusions_flagged": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
    },
    "required": [
        "is_likely_covered",
        "applicable_clauses",
        "deductible_note",
        "exclusions_flagged",
        "rationale",
    ],
    "additionalProperties": False,
}

SYSTEM = """You are a policy coverage analyst. You are given excerpts retrieved from the
motor insurance policy handbook plus facts about a specific claim. Determine whether the
described damage/incident is likely covered, cite the specific clauses you relied on, note
any exclusions that might apply, and explain the deductible treatment. Only rely on the
provided excerpts — do not invent policy terms that are not in the excerpts."""


def run(state: ClaimWorkflowState) -> dict:
    extraction = state.get("extraction", {})
    query = " ".join(
        filter(
            None,
            [
                state.get("incident_description", ""),
                " ".join(extraction.get("reported_damages", [])),
                state.get("policy_verification", {}).get("coverage_type", ""),
            ],
        )
    )
    chunks = retrieve(query, top_k=4)
    excerpts = "\n\n".join(f"### {c.title}\n{c.text}" for c in chunks)

    content = (
        f"Policy handbook excerpts:\n\n{excerpts}\n\n"
        f"---\n\nClaim details:\n"
        f"Incident description: {state.get('incident_description')}\n"
        f"Reported damages: {extraction.get('reported_damages')}\n"
        f"Coverage type on file: {state.get('policy_verification', {}).get('coverage_type')}\n"
        f"Deductible on file: {state.get('policy_verification', {}).get('deductible')}\n\n"
        "Assess likely coverage for this claim based only on the excerpts above."
    )

    result = call_structured(system=SYSTEM, content=content, schema=SCHEMA, effort="medium")
    result["retrieved_sections"] = [c.title for c in chunks]
    return {"policy_rag": result}
