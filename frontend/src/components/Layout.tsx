import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { api } from "../api/client";

const CUSTOMER_LINKS = [
  { to: "/claims", label: "My Claims" },
  { to: "/claims/new", label: "New Claim" },
];

const ADJUSTER_LINKS = [{ to: "/review", label: "Review Queue" }];

const ADMIN_LINKS = [
  { to: "/admin/policies", label: "Policies" },
  { to: "/admin/users", label: "Users" },
  { to: "/admin/evaluation", label: "Evaluation" },
  { to: "/admin/audit-log", label: "Audit Log" },
];

export function Layout() {
  const { user, logout } = useAuth();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const poll = () => {
      api
        .notifications()
        .then((items) => {
          if (!cancelled) setUnread(items.filter((n) => !n.read_at).length);
        })
        .catch(() => {});
    };
    poll();
    const id = setInterval(poll, 15000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  if (!user) return null;

  return (
    <div className="app-shell">
      <nav className="nav">
        <div className="nav-brand">
          <span className="dot" />
          Moto Claims
        </div>

        {user.role === "customer" && (
          <>
            <div className="nav-section-label">Customer</div>
            {CUSTOMER_LINKS.map((link) => (
              <NavLink key={link.to} to={link.to} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
                {link.label}
              </NavLink>
            ))}
          </>
        )}

        {(user.role === "adjuster" || user.role === "admin") && (
          <>
            <div className="nav-section-label">Adjuster</div>
            {ADJUSTER_LINKS.map((link) => (
              <NavLink key={link.to} to={link.to} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
                {link.label}
              </NavLink>
            ))}
          </>
        )}

        {user.role === "admin" && (
          <>
            <div className="nav-section-label">Admin</div>
            {ADMIN_LINKS.map((link) => (
              <NavLink key={link.to} to={link.to} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
                {link.label}
              </NavLink>
            ))}
          </>
        )}

        <div className="nav-section-label">Account</div>
        <NavLink to="/notifications" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
          Notifications{unread > 0 ? ` (${unread})` : ""}
        </NavLink>

        <div className="nav-footer">
          <div className="nav-user">
            <strong>{user.full_name}</strong>
            {user.email} · {user.role}
          </div>
          <button className="btn secondary small" onClick={logout}>
            Log out
          </button>
        </div>
      </nav>
      <div className="main">
        <Outlet />
      </div>
    </div>
  );
}
