import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type { PolicyOut } from "../api/types";
import { formatCurrency, formatDate } from "../lib/format";
import { useToast } from "../components/Toaster";

const BLANK = {
  policy_number: "",
  holder_name: "",
  vehicle_vin: "",
  vehicle_make: "",
  vehicle_model: "",
  vehicle_year: new Date().getFullYear(),
  coverage_type: "full",
  coverage_limit: 25000,
  deductible: 500,
  effective_date: new Date().toISOString().slice(0, 10),
  expiration_date: new Date(Date.now() + 365 * 24 * 3600 * 1000).toISOString().slice(0, 10),
  status: "active" as const,
};

export function AdminPoliciesPage() {
  const [policies, setPolicies] = useState<PolicyOut[] | null>(null);
  const [form, setForm] = useState(BLANK);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { notify, notifyError } = useToast();

  function load() {
    api
      .listPolicies()
      .then(setPolicies)
      .catch((err) => notifyError(err.message ?? "Failed to load policies"));
  }

  useEffect(load, [notifyError]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api.createPolicy(form);
      notify(`Policy ${form.policy_number} created.`);
      setForm(BLANK);
      setShowForm(false);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create policy");
    } finally {
      setSubmitting(false);
    }
  }

  function set<K extends keyof typeof BLANK>(key: K, value: (typeof BLANK)[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Policies</h1>
          <p className="page-sub">Underwritten vehicle policies claims are validated against.</p>
        </div>
        <button className="btn" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ New Policy"}
        </button>
      </div>

      {showForm && (
        <form className="card" onSubmit={handleSubmit} style={{ marginBottom: 16 }}>
          <div className="form-row">
            <div className="field">
              <label htmlFor="policy_number">Policy number</label>
              <input
                id="policy_number"
                required
                value={form.policy_number}
                onChange={(e) => set("policy_number", e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="holder_name">Holder name</label>
              <input id="holder_name" required value={form.holder_name} onChange={(e) => set("holder_name", e.target.value)} />
            </div>
          </div>
          <div className="form-row">
            <div className="field">
              <label htmlFor="vehicle_vin">VIN</label>
              <input id="vehicle_vin" required value={form.vehicle_vin} onChange={(e) => set("vehicle_vin", e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="vehicle_make">Make</label>
              <input id="vehicle_make" required value={form.vehicle_make} onChange={(e) => set("vehicle_make", e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="vehicle_model">Model</label>
              <input id="vehicle_model" required value={form.vehicle_model} onChange={(e) => set("vehicle_model", e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="vehicle_year">Year</label>
              <input
                id="vehicle_year"
                type="number"
                required
                value={form.vehicle_year}
                onChange={(e) => set("vehicle_year", Number(e.target.value))}
              />
            </div>
          </div>
          <div className="form-row">
            <div className="field">
              <label htmlFor="coverage_type">Coverage type</label>
              <select id="coverage_type" value={form.coverage_type} onChange={(e) => set("coverage_type", e.target.value)}>
                <option value="liability">Liability</option>
                <option value="collision">Collision</option>
                <option value="comprehensive">Comprehensive</option>
                <option value="full">Full</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="coverage_limit">Coverage limit</label>
              <input
                id="coverage_limit"
                type="number"
                required
                value={form.coverage_limit}
                onChange={(e) => set("coverage_limit", Number(e.target.value))}
              />
            </div>
            <div className="field">
              <label htmlFor="deductible">Deductible</label>
              <input
                id="deductible"
                type="number"
                required
                value={form.deductible}
                onChange={(e) => set("deductible", Number(e.target.value))}
              />
            </div>
          </div>
          <div className="form-row">
            <div className="field">
              <label htmlFor="effective_date">Effective date</label>
              <input
                id="effective_date"
                type="date"
                required
                value={form.effective_date}
                onChange={(e) => set("effective_date", e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="expiration_date">Expiration date</label>
              <input
                id="expiration_date"
                type="date"
                required
                value={form.expiration_date}
                onChange={(e) => set("expiration_date", e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="status">Status</label>
              <select id="status" value={form.status} onChange={(e) => set("status", e.target.value as typeof form.status)}>
                <option value="active">Active</option>
                <option value="lapsed">Lapsed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
          </div>
          {error && <p className="field-error">{error}</p>}
          <button className="btn" type="submit" disabled={submitting}>
            {submitting ? "Creating…" : "Create policy"}
          </button>
        </form>
      )}

      <div className="card">
        {policies === null ? (
          <p className="page-sub">Loading…</p>
        ) : (
          <div className="table-frame">
            <table className="data">
              <thead>
                <tr>
                  <th>Policy #</th>
                  <th>Holder</th>
                  <th>Vehicle</th>
                  <th>Coverage</th>
                  <th>Limit / Deductible</th>
                  <th>Valid</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {policies.map((p) => (
                  <tr key={p.id}>
                    <td className="claim-row-num">{p.policy_number}</td>
                    <td>{p.holder_name}</td>
                    <td>
                      {p.vehicle_year} {p.vehicle_make} {p.vehicle_model}
                    </td>
                    <td>{p.coverage_type}</td>
                    <td>
                      {formatCurrency(p.coverage_limit)} / {formatCurrency(p.deductible)}
                    </td>
                    <td>
                      {formatDate(p.effective_date)} – {formatDate(p.expiration_date)}
                    </td>
                    <td>
                      <span className={`badge ${p.status === "active" ? "good" : "neutral"}`}>{p.status}</span>
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
