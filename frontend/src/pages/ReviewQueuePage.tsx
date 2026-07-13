import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { ClaimOut } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import { formatCurrency, formatDateTime, titleCase } from "../lib/format";
import { useToast } from "../components/Toaster";

export function ReviewQueuePage() {
  const [claims, setClaims] = useState<ClaimOut[] | null>(null);
  const { notifyError } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    api
      .reviewQueue()
      .then(setClaims)
      .catch((err) => notifyError(err.message ?? "Failed to load review queue"));
  }, [notifyError]);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Review Queue</h1>
          <p className="page-sub">Claims flagged by the rules engine for adjuster review, oldest first.</p>
        </div>
      </div>

      <div className="card">
        {claims === null ? (
          <p className="page-sub">Loading…</p>
        ) : claims.length === 0 ? (
          <div className="empty-state">Queue is empty — nothing needs review right now.</div>
        ) : (
          <div className="table-frame">
            <table className="data">
              <thead>
                <tr>
                  <th>Claim #</th>
                  <th>Filed</th>
                  <th>AI recommendation</th>
                  <th>Fraud score</th>
                  <th>Estimated</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {claims.map((c) => (
                  <tr key={c.id} className="clickable" onClick={() => navigate(`/claims/${c.id}`)}>
                    <td className="claim-row-num">{c.claim_number}</td>
                    <td>{formatDateTime(c.created_at)}</td>
                    <td>{c.ai_recommendation ? titleCase(c.ai_recommendation) : "—"}</td>
                    <td>{c.fraud_score ?? "—"}</td>
                    <td>{formatCurrency(c.estimated_amount)}</td>
                    <td>
                      <StatusBadge status={c.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
