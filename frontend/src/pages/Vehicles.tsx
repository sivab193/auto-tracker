import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Family, FuelType, Vehicle } from "../api/types";
import Modal from "../components/Modal";
import { titleize } from "../lib/format";

const FUEL_TYPES: FuelType[] = ["petrol", "diesel", "cng", "lpg", "electric", "hybrid"];

export default function Vehicles() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [families, setFamilies] = useState<Family[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => api.get<Vehicle[]>("/api/vehicles").then(setVehicles).catch(() => {});
  useEffect(() => {
    load();
    api.get<Family[]>("/api/families").then(setFamilies).catch(() => {});
  }, []);

  async function create(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const f = new FormData(e.currentTarget);
    const payload: Record<string, unknown> = {
      registration_number: f.get("registration_number"),
      nickname: f.get("nickname") || null,
      make: f.get("make") || null,
      model: f.get("model") || null,
      year: f.get("year") ? Number(f.get("year")) : null,
      color: f.get("color") || null,
      fuel_type: f.get("fuel_type") || null,
      odometer: Number(f.get("odometer") || 0),
      family_id: f.get("family_id") ? Number(f.get("family_id")) : null,
    };
    try {
      await api.post<Vehicle>("/api/vehicles", payload);
      setShowAdd(false);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create vehicle");
    }
  }

  return (
    <div>
      <div className="row between" style={{ marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>Vehicles</h1>
        <button className="btn primary" onClick={() => setShowAdd(true)}>
          + Add vehicle
        </button>
      </div>

      {vehicles.length === 0 ? (
        <div className="card empty">
          <div className="big">🚗</div>
          No vehicles yet — add your first one to start tracking documents & costs.
        </div>
      ) : (
        <div className="grid cols-3">
          {vehicles.map((v) => (
            <Link key={v.id} to={`/vehicles/${v.id}`} className="card" style={{ color: "inherit" }}>
              <div className="row between">
                <h3 style={{ margin: 0 }}>{v.display_name}</h3>
                {v.family_id && <span className="badge blue">Shared</span>}
              </div>
              <div className="muted" style={{ fontSize: "0.86rem", marginBottom: 10 }}>
                {v.registration_number}
              </div>
              <dl className="kv">
                <dt>Make/Model</dt>
                <dd>{[v.make, v.model].filter(Boolean).join(" ") || "—"}</dd>
                <dt>Year</dt>
                <dd>{v.year ?? "—"}</dd>
                <dt>Fuel</dt>
                <dd>{v.fuel_type ? titleize(v.fuel_type) : "—"}</dd>
                <dt>Odometer</dt>
                <dd>{v.odometer.toLocaleString()} km</dd>
              </dl>
            </Link>
          ))}
        </div>
      )}

      {showAdd && (
        <Modal title="Add vehicle" onClose={() => setShowAdd(false)}>
          <form onSubmit={create} id="add-vehicle-form">
            {error && <div className="notice error" style={{ marginBottom: 12 }}>{error}</div>}
            <label className="field">
              <span className="lbl">Registration number *</span>
              <input name="registration_number" required placeholder="KA01AB1234" />
            </label>
            <div className="form-row">
              <label className="field">
                <span className="lbl">Nickname</span>
                <input name="nickname" placeholder="Daily driver" />
              </label>
              <label className="field">
                <span className="lbl">Odometer (km)</span>
                <input name="odometer" type="number" min="0" defaultValue={0} />
              </label>
            </div>
            <div className="form-row">
              <label className="field">
                <span className="lbl">Make</span>
                <input name="make" placeholder="Toyota" />
              </label>
              <label className="field">
                <span className="lbl">Model</span>
                <input name="model" placeholder="Corolla" />
              </label>
            </div>
            <div className="form-row">
              <label className="field">
                <span className="lbl">Year</span>
                <input name="year" type="number" min="1900" max="2100" />
              </label>
              <label className="field">
                <span className="lbl">Color</span>
                <input name="color" />
              </label>
            </div>
            <div className="form-row">
              <label className="field">
                <span className="lbl">Fuel type</span>
                <select name="fuel_type" defaultValue="">
                  <option value="">—</option>
                  {FUEL_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {titleize(t)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span className="lbl">Share with family</span>
                <select name="family_id" defaultValue="">
                  <option value="">Private</option>
                  {families.map((fam) => (
                    <option key={fam.id} value={fam.id}>
                      {fam.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <button className="btn primary" type="submit" style={{ width: "100%" }}>
              Create vehicle
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}
