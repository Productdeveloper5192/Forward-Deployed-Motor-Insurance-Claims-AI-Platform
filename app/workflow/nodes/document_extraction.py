from app.workflow.claude_client import call_structured, file_to_content_block
from app.workflow.state import ClaimWorkflowState

SCHEMA = {
    "type": "object",
    "properties": {
        "claimant_name": {"type": ["string", "null"]},
        "claimant_contact": {"type": ["string", "null"]},
        "vehicle_vin": {"type": ["string", "null"]},
        "vehicle_description": {"type": ["string", "null"]},
        "police_report_number": {"type": ["string", "null"]},
        "incident_summary": {"type": "string"},
        "reported_damages": {"type": "array", "items": {"type": "string"}},
        "repair_estimate_amount": {"type": ["number", "null"]},
        "documents_reviewed": {"type": "array", "items": {"type": "string"}},
        "extraction_notes": {"type": "string"},
    },
    "required": [
        "claimant_name",
        "claimant_contact",
        "vehicle_vin",
        "vehicle_description",
        "police_report_number",
        "incident_summary",
        "reported_damages",
        "repair_estimate_amount",
        "documents_reviewed",
        "extraction_notes",
    ],
    "additionalProperties": False,
}

SYSTEM = """You are a document extraction specialist for a motor insurance claims system.
Extract structured facts from the claim documents provided (police reports, ID proofs,
repair estimates). Only extract what is explicitly stated in the documents — never
invent a VIN, name, or amount. Use null for anything not present. Damage photos are
analyzed separately, so ignore image content beyond noting the document was reviewed."""

# Document types handled by this node — damage photos go to the damage-analysis node instead.
EXTRACTABLE_TYPES = {"police_report", "id_proof", "repair_estimate", "other"}


def run(state: ClaimWorkflowState) -> dict:
    docs = [d for d in state["documents"] if d["doc_type"] in EXTRACTABLE_TYPES]

    content: list[dict] = [
        {
            "type": "text",
            "text": (
                f"Claim incident description (as reported by claimant): "
                f"{state['incident_description']}\n\n"
                f"Incident date: {state['incident_date']}\n"
                f"Incident location: {state['incident_location']}\n\n"
                "Review the attached documents and extract the structured claim facts."
            ),
        }
    ]
    for doc in docs:
        content.append(file_to_content_block(doc["file_path"], doc["mime_type"]))
        content.append({"type": "text", "text": f"(Document above: {doc['original_filename']}, type={doc['doc_type']})"})

    if not docs:
        content.append({"type": "text", "text": "No supporting documents were uploaded for this claim."})

    result = call_structured(system=SYSTEM, content=content, schema=SCHEMA, effort="medium")
    return {"extraction": result}
