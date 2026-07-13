import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { NotificationOut } from "../api/types";
import { formatDateTime } from "../lib/format";
import { useToast } from "../components/Toaster";

export function NotificationsPage() {
  const [items, setItems] = useState<NotificationOut[] | null>(null);
  const { notifyError } = useToast();

  useEffect(() => {
    api
      .notifications()
      .then(setItems)
      .catch((err) => notifyError(err.message ?? "Failed to load notifications"));
  }, [notifyError]);

  async function markRead(id: number) {
    try {
      const updated = await api.markNotificationRead(id);
      setItems((prev) => prev?.map((n) => (n.id === id ? updated : n)) ?? null);
    } catch (err) {
      notifyError(err instanceof Error ? err.message : "Could not mark as read");
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Notifications</h1>
          <p className="page-sub">Claim status changes land here.</p>
        </div>
      </div>

      <div className="card">
        {items === null ? (
          <p className="page-sub">Loading…</p>
        ) : items.length === 0 ? (
          <div className="empty-state">Nothing yet.</div>
        ) : (
          items.map((n) => (
            <div key={n.id} className={`notification-item ${n.read_at ? "" : "unread"}`}>
              <div>
                <div className="notification-message">{n.message}</div>
                <div className="notification-meta">{formatDateTime(n.created_at)}</div>
              </div>
              {!n.read_at && (
                <button className="btn secondary small" onClick={() => markRead(n.id)}>
                  Mark read
                </button>
              )}
            </div>
          ))
        )}
      </div>
    </>
  );
}
