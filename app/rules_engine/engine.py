"""Deterministic rules engine that sits downstream of the AI workflow.

The LangGraph workflow produces a recommendation, a fraud score, and a set of
validation findings. This module applies hard, auditable business rules on
top of that output so that no claim can be auto-approved or auto-denied
purely on an LLM's say-so. The rules engine's decision — not the raw AI
recommendation — is what a human adjuster sees framed as "requires your
review" vs. "eligible for fast-track".
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class RulesEngineInput:
    policy_active: bool
    policy_effective_date: date
    policy_expiration_date: date
    incident_date: date
    coverage_limit: float
    deductible: float
    estimated_amount: float
    fraud_score: int
    validation_issues: list[str] = field(default_factory=list)
    auto_approve_max_amount: float = 3000.0
    fraud_review_threshold: int = 60
    fraud_deny_threshold: int = 85


@dataclass
class RulesEngineResult:
    decision: str  # auto_approve | manual_review | deny
    capped_amount: float
    rationale: str
    triggered_rules: list[str]


def evaluate(inp: RulesEngineInput) -> RulesEngineResult:
    triggered: list[str] = []

    # Hard denials — deterministic, no human ambiguity
    if not inp.policy_active:
        triggered.append("policy_inactive")
        return RulesEngineResult("deny", 0.0, "Policy is not active.", triggered)

    if not (inp.policy_effective_date <= inp.incident_date <= inp.policy_expiration_date):
        triggered.append("incident_outside_coverage_period")
        return RulesEngineResult(
            "deny", 0.0, "Incident date falls outside the policy's coverage period.", triggered
        )

    # Cap payout at policy limit regardless of downstream decision
    capped_amount = min(inp.estimated_amount, inp.coverage_limit)
    if capped_amount < inp.estimated_amount:
        triggered.append("amount_capped_at_policy_limit")

    net_amount = max(capped_amount - inp.deductible, 0.0)

    # Escalate to human review — never let the model auto-deny on suspicion alone
    if inp.fraud_score >= inp.fraud_deny_threshold:
        triggered.append("high_fraud_score")
        return RulesEngineResult(
            "manual_review",
            net_amount,
            f"Fraud risk score {inp.fraud_score} exceeds the deny threshold; requires adjuster investigation.",
            triggered,
        )

    if inp.fraud_score >= inp.fraud_review_threshold:
        triggered.append("elevated_fraud_score")

    if inp.validation_issues:
        triggered.append("cross_document_validation_issues")

    if "amount_capped_at_policy_limit" in triggered:
        return RulesEngineResult(
            "manual_review",
            net_amount,
            "Estimated damages exceed the policy coverage limit; adjuster must confirm payout.",
            triggered,
        )

    if triggered:
        reasons = "; ".join(triggered)
        return RulesEngineResult(
            "manual_review", net_amount, f"Flagged for review: {reasons}.", triggered
        )

    if inp.estimated_amount <= inp.auto_approve_max_amount:
        triggered.append("auto_approve_eligible")
        return RulesEngineResult(
            "auto_approve",
            net_amount,
            f"Claim meets fast-track criteria (amount <= ${inp.auto_approve_max_amount:,.2f}, "
            f"fraud score {inp.fraud_score} below review threshold, no validation issues).",
            triggered,
        )

    triggered.append("above_auto_approve_limit")
    return RulesEngineResult(
        "manual_review",
        net_amount,
        "Claim amount exceeds the auto-approval limit; standard adjuster review required.",
        triggered,
    )
