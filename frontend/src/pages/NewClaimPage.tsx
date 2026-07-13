import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";

export function NewClaimPage() {
  const navigate = useNavigate();
  const [policyNumber, setPolicyNumber] = useState("");
  const [incidentDate, setIncidentDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const claim = await api.createClaim({
        policy_number: policyNumber,
        incident_date: incidentDate,
        incident_description: description,
        incident_location: location,
      });
      navigate(`/claims/${claim.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create claim");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>File a New Claim</h1>
          <p className="page-sub">Start a draft — you'll be able to attach documents before submitting it.</p>
        </div>
      </div>

      <form className="card" onSubmit={handleSubmit} style={{ maxWidth: 520 }}>
        <div className="field">
          <label htmlFor="policyNumber">Policy number</label>
          <input
            id="policyNumber"
            required
            placeholder="POL-10001"
            value={policyNumber}
            onChange={(e) => setPolicyNumber(e.target.value)}
          />
          <span className="field-hint">Seeded demo policies: POL-10001 (active), POL-10002 (lapsed).</span>
        </div>

        <div className="form-row">
          <div className="field">
            <label htmlFor="incidentDate">Incident date</label>
            <input
              id="incidentDate"
              type="date"
              required
              value={incidentDate}
              onChange={(e) => setIncidentDate(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="location">Incident location</label>
            <input
              id="location"
              placeholder="Main St & 5th Ave"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
            />
          </div>
        </div>

        <div className="field">
          <label htmlFor="description">What happened?</label>
          <textarea
            id="description"
            required
            rows={4}
            placeholder="Describe the incident…"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        {error && <p className="field-error">{error}</p>}
        <button className="btn" type="submit" disabled={submitting}>
          {submitting ? "Creating…" : "Create draft claim"}
        </button>
      </form>
    </>
  );
}
