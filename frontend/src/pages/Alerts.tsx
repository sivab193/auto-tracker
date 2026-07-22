import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Alert } from "../api/types";
import { expiryTone, fmtDate, titleize } from "../lib/format";

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [busy, setBusy] = useState(false);

  const load = () => api.get<Alert[]>("/api/alerts").then(setAlerts).catch(() => {});
  useEffect(() => {
    load();
  }, []);

  async function sweep() {
    setBusy(true);
    try {
      await api.post("/api/alerts/sweep");
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function act(id: number, action: "acknowledge" | "dismiss") {
    await api.post(`/api/alerts/${id}/${action}`);
    load();
  }

  return (
    <div>
      <div className="row between" style={{ marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>Alerts</h1>
        <button className="btn" onClick={sweep} disabled={busy}>
          {busy ? "Checking…" : "↻ Check expiries now"}
        </button>
      </div>

      {alerts.length === 0 ? (
        <div className="card empty">
          <div className="big">✅</div>
          You're all caught up — no alerts.
        </div>
      ) : (
        <div className="card">
          <table>
            <thead>
              <tr>
                <th>Alert</th>
                <th>Due</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a) => (
                <tr key={a.id}>
                  <td>
                    <strong>{a.title}</strong>
                    <div className="muted" style={{ fontSize: "0.84rem" }}>
                      {a.message}
                    </div>
                  </td>
                  <td>
                    {a.due_date ? (
                      <span className={`badge ${expiryTone(a.due_date)}`}>{fmtDate(a.due_date)}</span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td>
                    <span
                      className={`badge ${
                        a.status === "acknowledged" ? "green" : a.status === "dismissed" ? "" : "amber"
                      }`}
                    >
                      {titleize(a.status)}
                    </span>
                  </td>
                  <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                    {a.status !== "acknowledged" && (
                      <button className="btn sm" onClick={() => act(a.id, "acknowledge")}>
                        Ack
                      </button>
                    )}{" "}
                    {a.status !== "dismissed" && (
                      <button className="btn ghost sm" onClick={() => act(a.id, "dismiss")}>
                        Dismiss
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
