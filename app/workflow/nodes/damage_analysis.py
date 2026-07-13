from app.workflow.claude_client import call_structured, file_to_content_block
from app.workflow.state import ClaimWorkflowState

SCHEMA = {
    "type": "object",
    "properties": {
        "photos_provided": {"type": "boolean"},
        "damage_severity": {
            "type": "string",
            "enum": ["none", "minor", "moderate", "severe", "total_loss"],
        },
        "damage_areas": {"type": "array", "items": {"type": "string"}},
        "estimated_repair_cost_low": {"type": "number"},
        "estimated_repair_cost_high": {"type": "number"},
        "total_loss_likely": {"type": "boolean"},
        "analysis_notes": {"type": "string"},
    },
    "required": [
        "photos_provided",
        "damage_severity",
        "damage_areas",
        "estimated_repair_cost_low",
        "estimated_repair_cost_high",
        "total_loss_likely",
        "analysis_notes",
    ],
    "additionalProperties": False,
}

SYSTEM = """You are a vehicle damage assessor for an auto insurance claims system. Examine
the provided damage photographs and estimate the severity, affected areas, and a plausible
US repair-cost range in USD. Base the range on typical body-shop labor and parts costs for
the damage visible — do not guess a company-specific quote. If photos show damage
inconsistent with the reported incident narrative, note that in analysis_notes (the
cross-validation stage handles the formal consistency check, but flag anything visually
suspicious here, e.g. damage that looks old/rusted rather than fresh)."""


def run(state: ClaimWorkflowState) -> dict:
    photos = [d for d in state["documents"] if d["doc_type"] == "damage_photo"]

    if not photos:
        return {
            "damage_analysis": {
                "photos_provided": False,
                "damage_severity": "none",
                "damage_areas": [],
                "estimated_repair_cost_low": 0,
                "estimated_repair_cost_high": 0,
                "total_loss_likely": False,
                "analysis_notes": "No damage photographs were uploaded with this claim.",
            }
        }

    content: list[dict] = [
        {
            "type": "text",
            "text": (
                f"Incident description: {state.get('incident_description')}\n"
                f"Reported damages: {state.get('extraction', {}).get('reported_damages')}\n\n"
                "Assess vehicle damage from the following photo(s)."
            ),
        }
    ]
    for photo in photos:
        content.append(file_to_content_block(photo["file_path"], photo["mime_type"]))

    result = call_structured(system=SYSTEM, content=content, schema=SCHEMA, effort="medium")
    result["photos_provided"] = True
    return {"damage_analysis": result}
