import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type { UserOut, UserRole } from "../api/types";
import { useToast } from "../components/Toaster";

const ROLE_TONE: Record<UserRole, string> = {
  customer: "neutral",
  adjuster: "accent",
  admin: "good",
};

export function AdminUsersPage() {
  const [users, setUsers] = useState<UserOut[] | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<UserRole>("adjuster");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const { notify, notifyError } = useToast();

  function load() {
    api
      .listUsers()
      .then(setUsers)
      .catch((err) => notifyError(err.message ?? "Failed to load users"));
  }

  useEffect(load, [notifyError]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api.createStaffUser(email, password, fullName, role);
      notify(`${fullName} added as ${role}.`);
      setEmail("");
      setPassword("");
      setFullName("");
      setRole("adjuster");
      setShowForm(false);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create user");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Users</h1>
          <p className="page-sub">
            Adjuster and admin accounts are provisioned here — self-registration only ever creates customers.
          </p>
        </div>
        <button className="btn" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ Add Staff User"}
        </button>
      </div>

      {showForm && (
        <form className="card" onSubmit={handleSubmit} style={{ marginBottom: 16, maxWidth: 480 }}>
          <div className="field">
            <label htmlFor="fullName">Full name</label>
            <input id="fullName" required value={fullName} onChange={(e) => setFullName(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="form-row">
            <div className="field">
              <label htmlFor="password">Temporary password</label>
              <input
                id="password"
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="role">Role</label>
              <select id="role" value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
                <option value="adjuster">Adjuster</option>
                <option value="admin">Admin</option>
              </select>
            </div>
          </div>
          {error && <p className="field-error">{error}</p>}
          <button className="btn" type="submit" disabled={submitting}>
            {submitting ? "Creating…" : "Create account"}
          </button>
        </form>
      )}

      <div className="card">
        {users === null ? (
          <p className="page-sub">Loading…</p>
        ) : (
          <div className="table-frame">
            <table className="data">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.full_name}</td>
                    <td>{u.email}</td>
                    <td>
                      <span className={`badge ${ROLE_TONE[u.role]}`}>{u.role}</span>
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
