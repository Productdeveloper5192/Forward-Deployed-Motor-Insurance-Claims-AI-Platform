import json
import time
from datetime import datetime, timezone

from langgraph.graph import END, StateGraph

from app.db.database import SessionLocal
from app.models.workflow import NodeExecution, WorkflowRun, WorkflowStatus
from app.workflow.nodes import (
    cross_validation,
    damage_analysis,
    decision_support,
    document_extraction,
    fraud_triage,
    policy_rag,
    policy_verification,
    rules_engine_node,
)
from app.workflow.state import ClaimWorkflowState

NODE_SEQUENCE = [
    ("document_extraction", document_extraction.run),
    ("policy_verification", policy_verification.run),
    ("policy_rag", policy_rag.run),
    ("cross_document_validation", cross_validation.run),
    ("vehicle_damage_analysis", damage_analysis.run),
    ("fraud_risk_triage", fraud_triage.run),
    ("decision_support_recommendation", decision_support.run),
    ("rules_engine", rules_engine_node.run),
]


def _record_node(workflow_run_id: int, name: str, fn):
    def wrapped(state: ClaimWorkflowState) -> dict:
        db = SessionLocal()
        started = time.monotonic()
        started_at = datetime.now(timezone.utc)
        run = db.get(WorkflowRun, workflow_run_id)
        run.current_node = name
        db.commit()

        try:
            update = fn(state)
        except Exception as exc:
            db.add(
                NodeExecution(
                    workflow_run_id=workflow_run_id,
                    node_name=name,
                    output_json=json.dumps({"error": str(exc)}),
                    duration_ms=int((time.monotonic() - started) * 1000),
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                )
            )
            db.commit()
            db.close()
            raise

        output_value = next(iter(update.values())) if update else {}
        db.add(
            NodeExecution(
                workflow_run_id=workflow_run_id,
                node_name=name,
                output_json=json.dumps(output_value, default=str),
                duration_ms=int((time.monotonic() - started) * 1000),
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        db.close()
        return update

    return wrapped


def _route_after_policy_verification(state: ClaimWorkflowState) -> str:
    """Skip the four downstream LLM stages when the policy is already a hard
    deny — nothing they produce can change a missing/inactive policy outcome,
    so there's no reason to pay for the extra Claude calls."""
    policy = state.get("policy_verification", {})
    if policy.get("found") and policy.get("active"):
        return "policy_rag"
    return "rules_engine"


def build_graph(workflow_run_id: int):
    graph = StateGraph(ClaimWorkflowState)
    for name, fn in NODE_SEQUENCE:
        graph.add_node(name, _record_node(workflow_run_id, name, fn))

    graph.set_entry_point("document_extraction")
    graph.add_edge("document_extraction", "policy_verification")
    graph.add_conditional_edges(
        "policy_verification",
        _route_after_policy_verification,
        {"policy_rag": "policy_rag", "rules_engine": "rules_engine"},
    )
    graph.add_edge("policy_rag", "cross_document_validation")
    graph.add_edge("cross_document_validation", "vehicle_damage_analysis")
    graph.add_edge("vehicle_damage_analysis", "fraud_risk_triage")
    graph.add_edge("fraud_risk_triage", "decision_support_recommendation")
    graph.add_edge("decision_support_recommendation", "rules_engine")
    graph.add_edge("rules_engine", END)

    return graph.compile()


def execute_claim_workflow(claim_id: int) -> None:
    """Entry point invoked by the background worker. Loads the claim, runs the
    LangGraph pipeline, applies the rules engine, and persists the outcome."""
    from app.models.claim import Claim, ClaimStatus
    from app.models.document import DocumentType
    from app.services import audit_log, notifications

    db = SessionLocal()
    try:
        claim = db.get(Claim, claim_id)
        if claim is None:
            return

        claim.status = ClaimStatus.PROCESSING
        db.commit()

        documents = [
            {
                "id": d.id,
                "doc_type": d.doc_type.value,
                "file_path": d.file_path,
                "mime_type": d.mime_type,
                "original_filename": d.original_filename,
            }
            for d in claim.documents
        ]
        policy_number = claim.policy.policy_number

        run = WorkflowRun(claim_id=claim_id, status=WorkflowStatus.RUNNING)
        db.add(run)
        db.commit()
        db.refresh(run)

        initial_state: ClaimWorkflowState = {
            "claim_id": claim_id,
            "workflow_run_id": run.id,
            "policy_number": policy_number,
            "incident_date": claim.incident_date.isoformat(),
            "incident_description": claim.incident_description,
            "incident_location": claim.incident_location,
            "documents": documents,
            "errors": [],
        }

        graph = build_graph(run.id)
        try:
            final_state = graph.invoke(initial_state, config={"recursion_limit": 25})
        except Exception as exc:
            run.status = WorkflowStatus.FAILED
            run.error = str(exc)
            run.completed_at = datetime.now(timezone.utc)
            claim.status = ClaimStatus.FAILED
            db.commit()
            audit_log.record(db, "workflow_failed", claim_id=claim_id, details=str(exc))
            notifications.notify(
                db,
                f"Claim {claim.claim_number} processing failed: {exc}",
                claim_id=claim_id,
                user_id=claim.customer_id,
            )
            return

        run.status = WorkflowStatus.COMPLETED
        run.completed_at = datetime.now(timezone.utc)
        run.current_node = None
        db.commit()

        rules = final_state.get("rules_engine", {})
        decision = final_state.get("decision_support", {})
        fraud = final_state.get("fraud_triage", {})
        extraction = final_state.get("extraction", {})
        damage = final_state.get("damage_analysis", {})

        for doc in claim.documents:
            if doc.doc_type == DocumentType.DAMAGE_PHOTO:
                if damage:
                    doc.extracted_data = json.dumps(damage, default=str)
            elif extraction:
                doc.extracted_data = json.dumps(extraction, default=str)

        claim.estimated_amount = rules.get("estimated_amount")
        claim.ai_recommendation = decision.get("recommendation")
        claim.ai_rationale = decision.get("rationale")
        claim.fraud_score = fraud.get("fraud_score")
        claim.rules_decision = rules.get("decision")
        claim.rules_rationale = rules.get("rationale")

        if rules.get("decision") == "auto_approve":
            claim.status = ClaimStatus.APPROVED
            claim.approved_amount = rules.get("capped_amount")
        elif rules.get("decision") == "deny":
            claim.status = ClaimStatus.DENIED
            claim.approved_amount = 0.0
        else:
            claim.status = ClaimStatus.NEEDS_REVIEW

        db.commit()

        audit_log.record(
            db,
            "workflow_completed",
            claim_id=claim_id,
            details=json.dumps({"rules_decision": rules.get("decision"), "fraud_score": fraud.get("fraud_score")}),
        )
        notifications.notify(
            db,
            f"Claim {claim.claim_number} processed — status: {claim.status.value.replace('_', ' ')}.",
            claim_id=claim_id,
            user_id=claim.customer_id,
        )
    finally:
        db.close()
