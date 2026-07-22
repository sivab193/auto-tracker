import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type {
  Document,
  DocumentType,
  FuelLog,
  OCRPreview,
  ServiceRecord,
  Vehicle,
  VehicleAnalytics,
} from "../api/types";
import BarChart from "../components/BarChart";
import Modal from "../components/Modal";
import { docTypeLabel, expiryTone, fmtDate, money, titleize, today } from "../lib/format";

const DOC_TYPES: DocumentType[] = [
  "registration",
  "insurance",
  "pollution",
  "road_tax",
  "fitness",
  "permit",
  "driving_license",
  "warranty",
  "invoice",
  "other",
];

type Tab = "documents" | "services" | "fuel" | "analytics";

export default function VehicleDetail() {
  const { id } = useParams();
  const vid = Number(id);
  const [vehicle, setVehicle] = useState<Vehicle | null>(null);
  const [tab, setTab] = useState<Tab>("documents");

  useEffect(() => {
    api.get<Vehicle>(`/api/vehicles/${vid}`).then(setVehicle).catch(() => {});
  }, [vid]);

  if (!vehicle) return <div className="loader">Loading…</div>;

  return (
    <div>
      <Link to="/vehicles" className="muted" style={{ fontSize: "0.86rem" }}>
        ← Vehicles
      </Link>
      <div className="row between" style={{ margin: "6px 0 18px" }}>
        <div>
          <h1 style={{ margin: 0 }}>{vehicle.display_name}</h1>
          <div className="muted">
            {vehicle.registration_number}
            {vehicle.make && ` · ${[vehicle.make, vehicle.model].filter(Boolean).join(" ")}`}
            {vehicle.year && ` · ${vehicle.year}`} · {vehicle.odometer.toLocaleString()} km
          </div>
        </div>
      </div>

      <div className="tabs">
        {(["documents", "services", "fuel", "analytics"] as Tab[]).map((t) => (
          <div key={t} className={`tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
            {titleize(t)}
          </div>
        ))}
      </div>

      {tab === "documents" && <Documents vid={vid} />}
      {tab === "services" && <Services vid={vid} />}
      {tab === "fuel" && <Fuel vid={vid} />}
      {tab === "analytics" && <Analytics vid={vid} />}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Documents                                                           */
/* ------------------------------------------------------------------ */
function Documents({ vid }: { vid: number }) {
  const [docs, setDocs] = useState<Document[]>([]);
  const [showUpload, setShowUpload] = useState(false);

  const load = () =>
    api.get<Document[]>(`/api/vehicles/${vid}/documents`).then(setDocs).catch(() => {});
  useEffect(() => {
    load();
  }, [vid]);

  async function remove(docId: number) {
    if (!confirm("Delete this document?")) return;
    await api.del(`/api/documents/${docId}`);
    load();
  }

  return (
    <div className="card">
      <div className="card-head">
        <h3 style={{ margin: 0 }}>Documents</h3>
        <button className="btn primary sm" onClick={() => setShowUpload(true)}>
          + Upload
        </button>
      </div>
      {docs.length === 0 ? (
        <div className="empty">
          <div className="big">📄</div>
          No documents. Upload insurance, registration, PUC & more — OCR fills the details.
        </div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th>Title / Number</th>
              <th>Expiry</th>
              <th>Version</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id}>
                <td>
                  <span className="badge">{docTypeLabel(d.doc_type)}</span>
                </td>
                <td>
                  {d.title || d.original_filename}
                  {d.document_number && (
                    <div className="muted" style={{ fontSize: "0.8rem" }}>
                      #{d.document_number}
                    </div>
                  )}
                </td>
                <td>
                  {d.expiry_date ? (
                    <span className={`badge ${expiryTone(d.expiry_date)}`}>
                      {fmtDate(d.expiry_date)}
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="muted">v{d.version}</td>
                <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                  <a
                    className="btn ghost sm"
                    href={api.downloadUrl(`/api/documents/${d.id}/download`)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open
                  </a>{" "}
                  <button className="btn danger sm" onClick={() => remove(d.id)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {showUpload && (
        <UploadModal
          vid={vid}
          onClose={() => setShowUpload(false)}
          onDone={() => {
            setShowUpload(false);
            load();
          }}
        />
      )}
    </div>
  );
}

function UploadModal({
  vid,
  onClose,
  onDone,
}: {
  vid: number;
  onClose: () => void;
  onDone: () => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [docType, setDocType] = useState<DocumentType | "">("");
  const [title, setTitle] = useState("");
  const [expiry, setExpiry] = useState("");
  const [issue, setIssue] = useState("");
  const [number, setNumber] = useState("");
  const [issuer, setIssuer] = useState("");
  const [preview, setPreview] = useState<OCRPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runOcr() {
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError("Choose a file first.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", file);
      if (docType) form.append("doc_type", docType);
      const res = await api.upload<OCRPreview>("/api/documents/ocr-preview", form);
      setPreview(res);
      if (!docType) setDocType(res.doc_type);
      if (res.fields.expiry_date) setExpiry(res.fields.expiry_date);
      if (res.fields.issue_date) setIssue(res.fields.issue_date);
      if (res.fields.document_number) setNumber(res.fields.document_number);
      if (res.fields.issuer) setIssuer(res.fields.issuer);
    } catch (err) {
      setError(err instanceof Error ? err.message : "OCR failed");
    } finally {
      setBusy(false);
    }
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError("Choose a file.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("auto_ocr", preview ? "false" : "true");
      if (docType) form.append("doc_type", docType);
      if (title) form.append("title", title);
      if (expiry) form.append("expiry_date", expiry);
      if (issue) form.append("issue_date", issue);
      if (number) form.append("document_number", number);
      if (issuer) form.append("issuer", issuer);
      await api.upload<Document>(`/api/vehicles/${vid}/documents`, form);
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title="Upload document" onClose={onClose}>
      <form onSubmit={submit}>
        {error && <div className="notice error" style={{ marginBottom: 12 }}>{error}</div>}
        <label className="field">
          <span className="lbl">File (PDF or image) *</span>
          <input ref={fileRef} type="file" accept="image/*,application/pdf" required />
        </label>
        <div className="row" style={{ marginBottom: 12 }}>
          <button type="button" className="btn sm" onClick={runOcr} disabled={busy}>
            {busy ? "Reading…" : "🔍 Extract with OCR"}
          </button>
          {preview && (
            <span className="muted" style={{ fontSize: "0.82rem" }}>
              Confidence: {preview.ocr_confidence ?? "n/a"}% — review & edit below
            </span>
          )}
        </div>

        <div className="form-row">
          <label className="field">
            <span className="lbl">Document type</span>
            <select value={docType} onChange={(e) => setDocType(e.target.value as DocumentType)}>
              <option value="">Auto-detect</option>
              {DOC_TYPES.map((t) => (
                <option key={t} value={t}>
                  {docTypeLabel(t)}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span className="lbl">Title</span>
            <input value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
        </div>
        <div className="form-row">
          <label className="field">
            <span className="lbl">Issue date</span>
            <input type="date" value={issue} onChange={(e) => setIssue(e.target.value)} />
          </label>
          <label className="field">
            <span className="lbl">Expiry date</span>
            <input type="date" value={expiry} onChange={(e) => setExpiry(e.target.value)} />
          </label>
        </div>
        <div className="form-row">
          <label className="field">
            <span className="lbl">Document number</span>
            <input value={number} onChange={(e) => setNumber(e.target.value)} />
          </label>
          <label className="field">
            <span className="lbl">Issuer</span>
            <input value={issuer} onChange={(e) => setIssuer(e.target.value)} />
          </label>
        </div>

        <button className="btn primary" type="submit" disabled={busy} style={{ width: "100%" }}>
          {busy ? "Uploading…" : "Upload document"}
        </button>
      </form>
    </Modal>
  );
}

/* ------------------------------------------------------------------ */
/* Services                                                            */
/* ------------------------------------------------------------------ */
function Services({ vid }: { vid: number }) {
  const [rows, setRows] = useState<ServiceRecord[]>([]);
  const [show, setShow] = useState(false);

  const load = () =>
    api.get<ServiceRecord[]>(`/api/vehicles/${vid}/services`).then(setRows).catch(() => {});
  useEffect(() => {
    load();
  }, [vid]);

  async function add(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    await api.post(`/api/vehicles/${vid}/services`, {
      service_type: f.get("service_type"),
      service_date: f.get("service_date"),
      odometer: f.get("odometer") ? Number(f.get("odometer")) : null,
      cost: Number(f.get("cost") || 0),
      vendor: f.get("vendor") || null,
      description: f.get("description") || null,
      next_service_date: f.get("next_service_date") || null,
    });
    setShow(false);
    load();
  }

  async function remove(rid: number) {
    if (!confirm("Delete this service record?")) return;
    await api.del(`/api/services/${rid}`);
    load();
  }

  return (
    <div className="card">
      <div className="card-head">
        <h3 style={{ margin: 0 }}>Service history</h3>
        <button className="btn primary sm" onClick={() => setShow(true)}>
          + Add
        </button>
      </div>
      {rows.length === 0 ? (
        <div className="empty">
          <div className="big">🔧</div>
          No service records yet.
        </div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Type</th>
              <th>Vendor</th>
              <th>Odometer</th>
              <th style={{ textAlign: "right" }}>Cost</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{fmtDate(r.service_date)}</td>
                <td>
                  <span className="badge">{titleize(r.service_type)}</span>
                </td>
                <td>{r.vendor || "—"}</td>
                <td className="muted">{r.odometer ? `${r.odometer.toLocaleString()} km` : "—"}</td>
                <td style={{ textAlign: "right" }}>{money(r.cost, r.currency)}</td>
                <td style={{ textAlign: "right" }}>
                  <button className="btn danger sm" onClick={() => remove(r.id)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {show && (
        <Modal title="Add service record" onClose={() => setShow(false)}>
          <form onSubmit={add}>
            <div className="form-row">
              <label className="field">
                <span className="lbl">Type</span>
                <select name="service_type" defaultValue="routine">
                  {["routine", "repair", "inspection", "tyre", "battery", "other"].map((t) => (
                    <option key={t} value={t}>
                      {titleize(t)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span className="lbl">Date</span>
                <input name="service_date" type="date" defaultValue={today()} required />
              </label>
            </div>
            <div className="form-row">
              <label className="field">
                <span className="lbl">Odometer (km)</span>
                <input name="odometer" type="number" min="0" />
              </label>
              <label className="field">
                <span className="lbl">Cost</span>
                <input name="cost" type="number" step="0.01" min="0" defaultValue={0} />
              </label>
            </div>
            <label className="field">
              <span className="lbl">Vendor</span>
              <input name="vendor" />
            </label>
            <label className="field">
              <span className="lbl">Next service date</span>
              <input name="next_service_date" type="date" />
            </label>
            <label className="field">
              <span className="lbl">Notes</span>
              <textarea name="description" rows={2} />
            </label>
            <button className="btn primary" type="submit" style={{ width: "100%" }}>
              Save
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Fuel                                                                */
/* ------------------------------------------------------------------ */
function Fuel({ vid }: { vid: number }) {
  const [rows, setRows] = useState<FuelLog[]>([]);
  const [show, setShow] = useState(false);

  const load = () => api.get<FuelLog[]>(`/api/vehicles/${vid}/fuel`).then(setRows).catch(() => {});
  useEffect(() => {
    load();
  }, [vid]);

  async function add(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    await api.post(`/api/vehicles/${vid}/fuel`, {
      fill_date: f.get("fill_date"),
      odometer: Number(f.get("odometer")),
      quantity: Number(f.get("quantity")),
      price_per_unit: f.get("price_per_unit") ? Number(f.get("price_per_unit")) : null,
      total_cost: Number(f.get("total_cost") || 0),
      is_full_tank: f.get("is_full_tank") === "on",
      station: f.get("station") || null,
    });
    setShow(false);
    load();
  }

  async function remove(rid: number) {
    if (!confirm("Delete this fuel log?")) return;
    await api.del(`/api/fuel/${rid}`);
    load();
  }

  return (
    <div className="card">
      <div className="card-head">
        <h3 style={{ margin: 0 }}>Fuel log</h3>
        <button className="btn primary sm" onClick={() => setShow(true)}>
          + Add fill-up
        </button>
      </div>
      {rows.length === 0 ? (
        <div className="empty">
          <div className="big">⛽</div>
          No fill-ups logged. Mileage is calculated automatically between full tanks.
        </div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Odometer</th>
              <th>Qty</th>
              <th>Efficiency</th>
              <th style={{ textAlign: "right" }}>Cost</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{fmtDate(r.fill_date)}</td>
                <td className="muted">{r.odometer.toLocaleString()} km</td>
                <td>
                  {r.quantity}
                  {!r.is_full_tank && <span className="badge amber" style={{ marginLeft: 6 }}>partial</span>}
                </td>
                <td>{r.efficiency ? <strong>{r.efficiency} km/unit</strong> : "—"}</td>
                <td style={{ textAlign: "right" }}>{money(r.total_cost, r.currency)}</td>
                <td style={{ textAlign: "right" }}>
                  <button className="btn danger sm" onClick={() => remove(r.id)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {show && (
        <Modal title="Add fill-up" onClose={() => setShow(false)}>
          <form onSubmit={add}>
            <div className="form-row">
              <label className="field">
                <span className="lbl">Date</span>
                <input name="fill_date" type="date" defaultValue={today()} required />
              </label>
              <label className="field">
                <span className="lbl">Odometer (km)</span>
                <input name="odometer" type="number" min="0" required />
              </label>
            </div>
            <div className="form-row">
              <label className="field">
                <span className="lbl">Quantity (L / kWh)</span>
                <input name="quantity" type="number" step="0.01" min="0" required />
              </label>
              <label className="field">
                <span className="lbl">Price / unit</span>
                <input name="price_per_unit" type="number" step="0.01" min="0" />
              </label>
            </div>
            <div className="form-row">
              <label className="field">
                <span className="lbl">Total cost</span>
                <input name="total_cost" type="number" step="0.01" min="0" />
              </label>
              <label className="field">
                <span className="lbl">Station</span>
                <input name="station" />
              </label>
            </div>
            <label className="row" style={{ gap: 8, marginBottom: 14 }}>
              <input name="is_full_tank" type="checkbox" defaultChecked style={{ width: "auto" }} />
              <span>Full tank (needed for mileage calculation)</span>
            </label>
            <button className="btn primary" type="submit" style={{ width: "100%" }}>
              Save
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Analytics                                                           */
/* ------------------------------------------------------------------ */
function Analytics({ vid }: { vid: number }) {
  const [a, setA] = useState<VehicleAnalytics | null>(null);

  useEffect(() => {
    api.get<VehicleAnalytics>(`/api/analytics/vehicles/${vid}`).then(setA).catch(() => {});
  }, [vid]);

  if (!a) return <div className="loader">Loading analytics…</div>;

  const tiles = [
    { label: "Total spend", value: money(a.total_cost) },
    { label: "Fuel cost", value: money(a.total_fuel_cost) },
    { label: "Service cost", value: money(a.total_service_cost) },
    { label: "Avg efficiency", value: a.avg_efficiency ? `${a.avg_efficiency} km/u` : "—" },
  ];

  return (
    <div>
      <div className="grid cols-4">
        {tiles.map((t) => (
          <div className="card stat" key={t.label}>
            <span className="label">{t.label}</span>
            <span className="value" style={{ fontSize: "1.5rem" }}>
              {t.value}
            </span>
          </div>
        ))}
      </div>
      <div className="card" style={{ marginTop: 18 }}>
        <h3>Monthly costs</h3>
        <BarChart data={a.monthly} currency="USD" />
      </div>
      <div className="card">
        <h3>Efficiency</h3>
        <dl className="kv">
          <dt>Best</dt>
          <dd>{a.best_efficiency ? `${a.best_efficiency} km/unit` : "—"}</dd>
          <dt>Worst</dt>
          <dd>{a.worst_efficiency ? `${a.worst_efficiency} km/unit` : "—"}</dd>
          <dt>Distance tracked</dt>
          <dd>{a.distance_tracked.toLocaleString()} km</dd>
          <dt>Cost / km</dt>
          <dd>{a.cost_per_distance ? money(a.cost_per_distance) : "—"}</dd>
        </dl>
      </div>
    </div>
  );
}
