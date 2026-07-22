import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Alert, DashboardSummary, Vehicle } from "../api/types";
import { fmtDate, money } from "../lib/format";

export default function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  useEffect(() => {
    api.get<DashboardSummary>("/api/analytics/dashboard").then(setSummary).catch(() => {});
    api.get<Vehicle[]>("/api/vehicles").then(setVehicles).catch(() => {});
    api.get<Alert[]>("/api/alerts?status_filter=pending").then(setAlerts).catch(() => {});
  }, []);

  const tiles = [
    { label: "Vehicles", value: summary?.vehicles ?? 0 },
    { label: "Documents", value: summary?.documents ?? 0 },
    { label: "Expiring ≤30d", value: summary?.expiring_soon ?? 0 },
    { label: "Total spend", value: money(summary?.total_spend ?? 0) },
  ];

  return (
    <div>
      <h1>Dashboard</h1>
      <div className="grid cols-4">
        {tiles.map((t) => (
          <div className="card stat" key={t.label}>
            <span className="label">{t.label}</span>
            <span className="value">{t.value}</span>
          </div>
        ))}
      </div>

      <div className="grid cols-2" style={{ marginTop: 18 }}>
        <div className="card">
          <div className="card-head">
            <h3 style={{ margin: 0 }}>Your vehicles</h3>
            <Link className="btn sm" to="/vehicles">
              View all
            </Link>
          </div>
          {vehicles.length === 0 ? (
            <div className="empty">
              <div className="big">🚗</div>
              No vehicles yet. <Link to="/vehicles">Add one</Link>.
            </div>
          ) : (
            <table>
              <tbody>
                {vehicles.slice(0, 6).map((v) => (
                  <tr key={v.id}>
                    <td>
                      <Link to={`/vehicles/${v.id}`}>
                        <strong>{v.display_name}</strong>
                      </Link>
                      <div className="muted" style={{ fontSize: "0.82rem" }}>
                        {v.registration_number}
                      </div>
                    </td>
                    <td style={{ textAlign: "right" }} className="muted">
                      {v.odometer.toLocaleString()} km
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="card">
          <div className="card-head">
            <h3 style={{ margin: 0 }}>Upcoming alerts</h3>
            <Link className="btn sm" to="/alerts">
              View all
            </Link>
          </div>
          {alerts.length === 0 ? (
            <div className="empty">
              <div className="big">✅</div>
              Nothing needs attention.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {alerts.slice(0, 6).map((a) => (
                <div key={a.id} className="row between" style={{ alignItems: "flex-start" }}>
                  <div>
                    <strong>{a.title}</strong>
                    <div className="muted" style={{ fontSize: "0.84rem" }}>
                      {a.message}
                    </div>
                  </div>
                  <span className="badge amber">{fmtDate(a.due_date)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
