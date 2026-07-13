from datetime import date, timedelta

import pytest

from app.rules_engine.engine import RulesEngineInput, evaluate

TODAY = date(2026, 1, 1)


def make_input(**overrides) -> RulesEngineInput:
    defaults = dict(
        policy_active=True,
        policy_effective_date=TODAY - timedelta(days=30),
        policy_expiration_date=TODAY + timedelta(days=335),
        incident_date=TODAY,
        coverage_limit=25000.0,
        deductible=500.0,
        estimated_amount=2000.0,
        fraud_score=10,
        validation_issues=[],
    )
    defaults.update(overrides)
    return RulesEngineInput(**defaults)


def test_denies_when_policy_inactive():
    result = evaluate(make_input(policy_active=False))
    assert result.decision == "deny"
    assert result.capped_amount == 0.0
    assert "policy_inactive" in result.triggered_rules


def test_denies_when_incident_outside_coverage_period():
    result = evaluate(make_input(incident_date=TODAY - timedelta(days=400)))
    assert result.decision == "deny"
    assert "incident_outside_coverage_period" in result.triggered_rules


def test_auto_approves_small_clean_claim():
    result = evaluate(make_input(estimated_amount=1500.0, fraud_score=5))
    assert result.decision == "auto_approve"
    assert result.capped_amount == pytest.approx(1000.0)  # 1500 - 500 deductible
    assert "auto_approve_eligible" in result.triggered_rules


def test_manual_review_above_auto_approve_limit():
    result = evaluate(make_input(estimated_amount=5000.0, auto_approve_max_amount=3000.0))
    assert result.decision == "manual_review"
    assert "above_auto_approve_limit" in result.triggered_rules


def test_caps_payout_at_policy_limit_and_forces_review():
    result = evaluate(make_input(estimated_amount=50000.0, coverage_limit=25000.0))
    assert result.decision == "manual_review"
    assert "amount_capped_at_policy_limit" in result.triggered_rules
    assert result.capped_amount == pytest.approx(24500.0)  # 25000 - 500 deductible


def test_high_fraud_score_never_auto_denies_goes_to_manual_review():
    result = evaluate(make_input(fraud_score=90, fraud_deny_threshold=85))
    assert result.decision == "manual_review"
    assert "high_fraud_score" in result.triggered_rules


def test_elevated_fraud_score_triggers_review():
    result = evaluate(make_input(fraud_score=70, fraud_review_threshold=60, fraud_deny_threshold=85))
    assert result.decision == "manual_review"
    assert "elevated_fraud_score" in result.triggered_rules


def test_validation_issues_trigger_review():
    result = evaluate(make_input(validation_issues=["VIN mismatch between claim and policy"]))
    assert result.decision == "manual_review"
    assert "cross_document_validation_issues" in result.triggered_rules


def test_net_amount_floors_at_zero_when_deductible_exceeds_estimate():
    result = evaluate(make_input(estimated_amount=200.0, deductible=500.0))
    assert result.capped_amount == 0.0
