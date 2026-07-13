import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ClaimStatus, EvaluationMetrics } from "../api/types";
import { titleCase } from "../lib/format";
import { useToast } from "../components/Toaster";

// Fixed lifecycle order — never re-sorted by count, so a bar's position always
// means the same status regardless of which statuses are present.
const STATUS_ORDER: ClaimStatus[] = [
  "draft",
  "submitted",
  "processing",
  "needs_review",
  "approved",
  "denied",
  "paid",
  "failed",
];

const STATUS_TONE: Record<ClaimStatus, string> = {
  draft: "var(--neutral-ink)",
  submitted: "var(--accent)",
  processing: "var(--accent)",
  needs_review: "var(--warn)",
  approved: "var(--good)",
  denied: "var(--bad)",
  paid: "var(--good)",
  failed: "var(--bad)",
};

function pct(value: number | null): string {
  if (value === null) return "—";
  return `${Math.round(value * 100)}%`;
}

export function AdminEvaluationPage() {
  const [metrics, setMetrics] = useState<EvaluationMetrics | null>(null);
  const { notifyError } = useToast();

  useEffect(() => {
    api
      .evaluation()
      .then(setMetrics)
      .catch((err) => notifyError(err.message ?? "Failed to load evaluation metrics"));
  }, [notifyError]);

  if (!metrics) {
    return (
      <>
        <div className="page-head">
          <h1>Evaluation</h1>
        </div>
        <p className="page-sub">Loading…</p>
      </>
    );
  }

  const maxCount = Math.max(1, ...Object.values(metrics.claims_by_status));

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Evaluation</h1>
          <p className="page-sub">How often the AI recommendation, the rules engine, and human adjusters agree.</p>
        </div>
      </div>

      <div className="stat-grid" style={{ marginBottom: 16 }}>
        <div className="stat-tile">
          <div className="stat-label">Total claims</div>
          <div className="stat-value">{metrics.total_claims.toLocaleString()}</div>
        </div>
        <div className="stat-tile">
          <div className="stat-label">AI ↔ Rules Agreement</div>
          <div className="stat-value">{pct(metrics.ai_rules_engine_agreement_rate)}</div>
          <div className="field-hint">of {metrics.workflow_processed_count} processed</div>
        </div>
        <div className="stat-tile">
          <div className="stat-label">AI ↔ Human Agreement</div>
          <div className="stat-value">{pct(metrics.ai_human_agreement_rate)}</div>
          <div className="field-hint">of {metrics.human_reviewed_count} reviewed</div>
        </div>
        <div className="stat-tile">
          <div className="stat-label">Avg. fraud score</div>
          <div className="stat-value">{metrics.average_fraud_score ?? "—"}</div>
          <div className="field-hint">out of 100</div>
        </div>
      </div>

      <div className="card">
        <div className="section-title">Claims by status</div>
        {STATUS_ORDER.map((status) => {
          const count = metrics.claims_by_status[status] ?? 0;
          return (
            <div className="bar-row" key={status}>
              <div className="bar-label">{titleCase(status)}</div>
              <div className="bar-track">
                <div
                  className="bar-fill"
                  style={{ width: `${(count / maxCount) * 100}%`, background: STATUS_TONE[status] }}
                />
              </div>
              <div className="bar-count">{count}</div>
            </div>
          );
        })}
      </div>
    </>
  );
}
