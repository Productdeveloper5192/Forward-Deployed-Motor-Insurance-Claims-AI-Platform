from datetime import date, datetime

from pydantic import BaseModel

from app.models.claim import ClaimStatus
from app.models.document import DocumentType


class ClaimCreate(BaseModel):
    policy_number: str
    incident_date: date
    incident_description: str
    incident_location: str = ""


class DocumentOut(BaseModel):
    id: int
    doc_type: DocumentType
    original_filename: str
    mime_type: str
    extracted_data: str | None = None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class ClaimOut(BaseModel):
    id: int
    claim_number: str
    status: ClaimStatus
    incident_date: date
    incident_description: str
    incident_location: str
    estimated_amount: float | None
    approved_amount: float | None
    ai_recommendation: str | None
    ai_rationale: str | None
    fraud_score: int | None
    rules_decision: str | None
    rules_rationale: str | None
    review_notes: str | None
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime
    documents: list[DocumentOut] = []

    model_config = {"from_attributes": True}


class ReviewDecision(BaseModel):
    decision: str  # approved | denied
    approved_amount: float | None = None
    notes: str = ""


class NodeExecutionOut(BaseModel):
    node_name: str
    output_json: str | None
    duration_ms: int

    model_config = {"from_attributes": True}


class WorkflowRunOut(BaseModel):
    id: int
    status: str
    current_node: str | None
    error: str | None
    node_executions: list[NodeExecutionOut] = []

    model_config = {"from_attributes": True}
