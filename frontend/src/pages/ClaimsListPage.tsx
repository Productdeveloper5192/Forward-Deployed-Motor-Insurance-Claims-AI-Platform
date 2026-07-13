import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { ClaimOut } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import { formatCurrency, formatDate } from "../lib/format";
import { useToast } from "../components/Toaster";

export function ClaimsListPage() {
  const [claims, setClaims] = useState<ClaimOut[] | null>(null);
  const { notifyError } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    api
      .listClaims()
      .then(setClaims)
      .catch((err) => notifyError(err.message ?? "Failed to load claims"));
  }, [notifyError]);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>My Claims</h1>
          <p className="page-sub">Every claim you've filed, and where it stands.</p>
        </div>
        <Link className="btn" to="/claims/new">
          + New Claim
        </Link>
      </div>

      <div className="card">
        {claims === null ? (
          <p className="page-sub">Loading…</p>
        ) : claims.length === 0 ? (
          <div className="empty-state">
            No claims yet. <Link to="/claims/new">File your first claim</Link>.
          </div>
        ) : (
          <div className="table-frame">
            <table className="data">
              <thead>
                <tr>
                  <th>Claim #</th>
                  <th>Incident</th>
                  <th>Filed</th>
                  <th>Estimated</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {claims.map((c) => (
                  <tr key={c.id} className="clickable" onClick={() => navigate(`/claims/${c.id}`)}>
                    <td className="claim-row-num">{c.claim_number}</td>
                    <td>{c.incident_description.slice(0, 60)}</td>
                    <td>{formatDate(c.incident_date)}</td>
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
