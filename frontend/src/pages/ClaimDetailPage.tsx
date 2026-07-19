import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { ClaimOut, DocumentType, WorkflowRunOut } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import { WorkflowTimeline } from "../components/WorkflowTimeline";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../components/Toaster";
import { formatCurrency, formatDateTime, titleCase } from "../lib/format";

const DOC_TYPES: { value: DocumentType; label: string }[] = [
  { value: "police_report", label: "Police report" },
  { value: "damage_photo", label: "Damage photo" },
  { value: "id_proof", label: "ID proof" },
  { value: "repair_estimate", label: "Repair estimate" },
  { value: "other", label: "Other" },
];

const ACTIVE_STATUSES = new Set(["submitted", "processing"]);

export function ClaimDetailPage() {
  const { id } = useParams();
  const claimId = Number(id);
  const { user } = useAuth();
  const { notify, notifyError } = useToast();
  const navigate = useNavigate();

  const [claim, setClaim] = useState<ClaimOut | null>(null);
  const [run, setRun] = useState<WorkflowRunOut | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [docType, setDocType] = useState<DocumentType>("police_report");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [paying, setPaying] = useState(false);
  const [decision, setDecision] = useState<"approved" | "denied">("approved");
  const [approvedAmount, setApprovedAmount] = useState("");
  const [notes, setNotes] = useState("");
  const [decisionSubmitting, setDecisionSubmitting] = useState(false);

  const isCustomer = user?.role === "customer";
  const isStaff = user?.role === "adjuster" || user?.role === "admin";

  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      const [claimData, runs] = await Promise.all([api.getClaim(claimId), api.getWorkflow(claimId)]);
      setClaim(claimData);
      setRun(runs.length > 0 ? runs[runs.length - 1] : null);
      setLoadError(null);
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : "Failed to load claim");
    }
  }, [claimId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!claim || !ACTIVE_STATUSES.has(claim.status)) return;
    const interval = setInterval(load, 2500);
    return () => clearInterval(interval);
  }, [claim, load]);

  async function handleUpload(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    try {
      const updated = await api.uploadDocument(claimId, docType, file);
      setClaim(updated);
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      notify("Document uploaded.");
    } catch (err) {
      notifyError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function handleSubmitClaim() {
    setSubmitting(true);
    try {
      const updated = await api.submitClaim(claimId);
      setClaim(updated);
      notify("Claim submitted — the AI pipeline is now running.");
    } catch (err) {
      notifyError(err instanceof ApiError ? err.message : "Submit failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handlePay() {
    setPaying(true);
    try {
      const updated = await api.payClaim(claimId);
      setClaim(updated);
      notify("Claim marked as paid.");
    } catch (err) {
      notifyError(err instanceof ApiError ? err.message : "Payment failed");
    } finally {
      setPaying(false);
    }
  }

  async function handleDecision(e: FormEvent) {
    e.preventDefault();
    setDecisionSubmitting(true);
    try {
      const updated = await api.submitDecision(
        claimId,
        decision,
        decision === "approved" && approvedAmount ? Number(approvedAmount) : null,
        notes
      );
      setClaim(updated);
      notify(`Claim ${decision}.`);
    } catch (err) {
      notifyError(err instanceof ApiError ? err.message : "Decision failed");
    } finally {
      setDecisionSubmitting(false);
    }
  }

  if (loadError) {
    return (
      <div className="card">
        <p className="field-error">{loadError}</p>
        <button className="btn secondary" onClick={() => navigate(-1)}>
          Go back
        </button>
      </div>
    );
  }

  if (!claim) return <p className="page-sub">Loading…</p>;

  return (
    <>
      <div className="page-head">
        <div>
          <h1 className="mono">{claim.claim_number}</h1>
          <p className="page-sub">Filed {formatDateTime(claim.created_at)}</p>
        </div>
        <StatusBadge status={claim.status} />
      </div>

      <div className="card">
        <div className="section-title">Incident</div>
        <dl className="kv-grid">
          <div>
            <dt>Description</dt>
            <dd style={{ fontWeight: 400 }}>{claim.incident_description}</dd>
          </div>
          <div>
            <dt>Location</dt>
            <dd style={{ fontWeight: 400 }}>{claim.incident_location || "—"}</dd>
          </div>
          <div>
            <dt>Estimated amount</dt>
            <dd>{formatCurrency(claim.estimated_amount)}</dd>
          </div>
          <div>
            <dt>Approved amount</dt>
            <dd>{formatCurrency(claim.approved_amount)}</dd>
          </div>
        </dl>
      </div>

      {(claim.ai_recommendation || claim.rules_decision) && (
        <div className="card">
          <div className="section-title">AI &amp; Rules Engine</div>
          <dl className="kv-grid" style={{ marginBottom: 14 }}>
            <div>
              <dt>AI recommendation</dt>
              <dd>{claim.ai_recommendation ? titleCase(claim.ai_recommendation) : "—"}</dd>
            </div>
            <div>
              <dt>Rules engine decision</dt>
              <dd>{claim.rules_decision ? titleCase(claim.rules_decision) : "—"}</dd>
            </div>
            <div>
              <dt>Fraud score</dt>
              <dd>{claim.fraud_score ?? "—"} / 100</dd>
            </div>
          </dl>
          {claim.ai_rationale && (
            <>
              <div className="field-hint" style={{ marginBottom: 6 }}>
                AI rationale (advisory only)
              </div>
              <p className="rationale-box">{claim.ai_rationale}</p>
            </>
          )}
          {claim.rules_rationale && (
            <>
              <div className="field-hint" style={{ margin: "12px 0 6px" }}>
                Rules engine rationale (binding)
              </div>
              <p className="rationale-box">{claim.rules_rationale}</p>
            </>
          )}
        </div>
      )}

      {run && (
        <div className="card">
          <div className="section-title">AI Workflow</div>
          <WorkflowTimeline run={run} />
        </div>
      )}

      <div className="card">
        <div className="section-title">Documents</div>
        {claim.documents.length === 0 ? (
          <p className="page-sub">No documents uploaded yet.</p>
        ) : (
          <div className="doc-list">
            {claim.documents.map((doc) => (
              <div className="doc-item" key={doc.id}>
                <div>
                  <div className="doc-name">{doc.original_filename}</div>
                  <div className="doc-meta">
                    {titleCase(doc.doc_type)} · {formatDateTime(doc.uploaded_at)}
                    {doc.extracted_data ? " · analyzed" : ""}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {isCustomer && claim.status === "draft" && (
          <form onSubmit={handleUpload} style={{ marginTop: 16 }}>
            <div className="form-row">
              <div className="field">
                <label htmlFor="docType">Document type</label>
                <select id="docType" value={docType} onChange={(e) => setDocType(e.target.value as DocumentType)}>
                  {DOC_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="file">File</label>
                <input
                  id="file"
                  type="file"
                  ref={fileInputRef}
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
              </div>
            </div>
            <button className="btn secondary" type="submit" disabled={!file || uploading}>
              {uploading ? "Uploading…" : "Upload document"}
            </button>
          </form>
        )}
      </div>

      {isCustomer && claim.status === "draft" && (
        <div className="card">
          <div className="section-title">Ready to submit?</div>
          <p className="page-sub" style={{ marginBottom: 12 }}>
            Once submitted, the claim locks and runs through the AI pipeline automatically.
          </p>
          <button className="btn" onClick={handleSubmitClaim} disabled={submitting}>
            {submitting ? "Submitting…" : "Submit claim"}
          </button>
        </div>
      )}

      {isStaff && claim.status === "needs_review" && (
        <div className="card">
          <div className="section-title">Adjuster Decision</div>
          <form onSubmit={handleDecision}>
            <div className="form-row">
              <div className="field">
                <label htmlFor="decision">Decision</label>
                <select id="decision" value={decision} onChange={(e) => setDecision(e.target.value as "approved" | "denied")}>
                  <option value="approved">Approve</option>
                  <option value="denied">Deny</option>
                </select>
              </div>
              {decision === "approved" && (
                <div className="field">
                  <label htmlFor="approvedAmount">Approved amount</label>
                  <input
                    id="approvedAmount"
                    type="number"
                    min={0}
                    step="0.01"
                    required
                    value={approvedAmount}
                    onChange={(e) => setApprovedAmount(e.target.value)}
                    placeholder={claim.estimated_amount?.toString() ?? ""}
                  />
                </div>
              )}
            </div>
            <div className="field">
              <label htmlFor="notes">Notes</label>
              <textarea id="notes" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
            </div>
            <button className={`btn ${decision === "approved" ? "good" : "danger"}`} type="submit" disabled={decisionSubmitting}>
              {decisionSubmitting ? "Submitting…" : decision === "approved" ? "Approve claim" : "Deny claim"}
            </button>
          </form>
        </div>
      )}

      {isStaff && claim.status === "approved" && (
        <div className="card">
          <div className="section-title">Payout</div>
          <p className="page-sub" style={{ marginBottom: 12 }}>
            Approved for {formatCurrency(claim.approved_amount)}. Mark it paid once disbursed.
          </p>
          <button className="btn good" onClick={handlePay} disabled={paying}>
            {paying ? "Processing…" : "Mark as paid"}
          </button>
        </div>
      )}

      {claim.review_notes && (
        <div className="card">
          <div className="section-title">Adjuster Notes</div>
          <p className="rationale-box">{claim.review_notes}</p>
        </div>
      )}
    </>
  );
}
