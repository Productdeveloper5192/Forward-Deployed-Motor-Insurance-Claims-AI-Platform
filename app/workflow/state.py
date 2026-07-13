from typing import Any, TypedDict


class DocumentRef(TypedDict):
    id: int
    doc_type: str
    file_path: str
    mime_type: str
    original_filename: str


class ClaimWorkflowState(TypedDict, total=False):
    claim_id: int
    workflow_run_id: int
    policy_number: str
    incident_date: str
    incident_description: str
    incident_location: str
    documents: list[DocumentRef]

    extraction: dict[str, Any]
    policy_verification: dict[str, Any]
    policy_rag: dict[str, Any]
    cross_validation: dict[str, Any]
    damage_analysis: dict[str, Any]
    fraud_triage: dict[str, Any]
    decision_support: dict[str, Any]
    rules_engine: dict[str, Any]

    errors: list[str]
