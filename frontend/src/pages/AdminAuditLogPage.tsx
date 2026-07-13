import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { AuditLogOut } from "../api/types";
import { formatDateTime, titleCase } from "../lib/format";
import { useToast } from "../components/Toaster";

export function AdminAuditLogPage() {
  const [entries, setEntries] = useState<AuditLogOut[] | null>(null);
  const [claimIdFilter, setClaimIdFilter] = useState("");
  const { notifyError } = useToast();

  function load(claimId?: number) {
    api
      .auditLog(claimId)
      .then(setEntries)
      .catch((err) => notifyError(err.message ?? "Failed to load audit log"));
  }

  useEffect(() => load(), []); // eslint-disable-line react-hooks/exhaustive-deps

  function handleFilter(e: FormEvent) {
    e.preventDefault();
    load(claimIdFilter ? Number(claimIdFilter) : undefined);
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Audit Log</h1>
          <p className="page-sub">Append-only trail of every state change, most recent first.</p>
        </div>
      </div>

      <form className="card" onSubmit={handleFilter} style={{ marginBottom: 16, display: "flex", gap: 12, alignItems: "flex-end" }}>
        <div className="field" style={{ marginBottom: 0 }}>
          <label htmlFor="claimId">Filter by claim ID</label>
          <input
            id="claimId"
            type="number"
            placeholder="e.g. 12"
            value={claimIdFilter}
            onChange={(e) => setClaimIdFilter(e.target.value)}
          />
        </div>
        <button className="btn secondary" type="submit">
          Filter
        </button>
      </form>

      <div className="card">
        {entries === null ? (
          <p className="page-sub">Loading…</p>
        ) : entries.length === 0 ? (
          <div className="empty-state">No matching audit entries.</div>
        ) : (
          <div className="table-frame">
            <table className="data">
              <thead>
                <tr>
                  <th>When</th>
                  <th>Action</th>
                  <th>Claim</th>
                  <th>User</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e) => (
                  <tr key={e.id}>
                    <td>{formatDateTime(e.created_at)}</td>
                    <td>{titleCase(e.action)}</td>
                    <td>{e.claim_id ?? "—"}</td>
                    <td>{e.user_id ?? "system"}</td>
                    <td style={{ maxWidth: 380 }}>{e.details ?? "—"}</td>
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
