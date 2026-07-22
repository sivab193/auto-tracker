import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { Family, FamilyRole, Invite } from "../api/types";
import { useAuth } from "../context/AuthContext";
import Modal from "../components/Modal";
import { fmtDate, titleize } from "../lib/format";

interface AuditRow {
  id: number;
  action: string;
  entity_type: string | null;
  detail: string | null;
  created_at: string;
}

const ROLES: FamilyRole[] = ["admin", "member", "viewer"];

export default function FamilyPage() {
  const { user } = useAuth();
  const [families, setFamilies] = useState<Family[]>([]);
  const [selected, setSelected] = useState<Family | null>(null);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [audit, setAudit] = useState<AuditRow[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [showJoin, setShowJoin] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadFamilies = () => api.get<Family[]>("/api/families").then(setFamilies).catch(() => {});
  useEffect(() => {
    loadFamilies();
  }, []);

  async function selectFamily(f: Family) {
    setSelected(f);
    const isAdmin = f.members.find((m) => m.user_id === user?.id)?.role === "admin";
    if (isAdmin) {
      api.get<Invite[]>(`/api/families/${f.id}/invites`).then(setInvites).catch(() => setInvites([]));
      api.get<AuditRow[]>(`/api/families/${f.id}/audit`).then(setAudit).catch(() => setAudit([]));
    } else {
      setInvites([]);
      setAudit([]);
    }
  }

  async function createFamily(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const name = new FormData(e.currentTarget).get("name");
    const fam = await api.post<Family>("/api/families", { name });
    setShowCreate(false);
    await loadFamilies();
    selectFamily(fam);
  }

  async function join(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const code = new FormData(e.currentTarget).get("code");
    try {
      await api.post("/api/families/join", { code });
      setShowJoin(false);
      loadFamilies();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not join");
    }
  }

  async function createInvite() {
    if (!selected) return;
    await api.post(`/api/families/${selected.id}/invites`, { role: "member", max_uses: 5 });
    api.get<Invite[]>(`/api/families/${selected.id}/invites`).then(setInvites);
  }

  async function changeRole(membershipId: number, role: FamilyRole) {
    if (!selected) return;
    await api.patch(`/api/families/${selected.id}/members/${membershipId}`, { role });
    const fresh = await api.get<Family>(`/api/families/${selected.id}`);
    setSelected(fresh);
    loadFamilies();
  }

  const isAdmin = selected?.members.find((m) => m.user_id === user?.id)?.role === "admin";

  return (
    <div>
      <div className="row between" style={{ marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>Family sharing</h1>
        <div className="row">
          <button className="btn" onClick={() => setShowJoin(true)}>
            Join with code
          </button>
          <button className="btn primary" onClick={() => setShowCreate(true)}>
            + New family
          </button>
        </div>
      </div>

      {families.length === 0 ? (
        <div className="card empty">
          <div className="big">👥</div>
          Create a family group to share vehicles & documents with role-based access.
        </div>
      ) : (
        <div className="grid cols-3" style={{ marginBottom: 18 }}>
          {families.map((f) => (
            <div
              key={f.id}
              className="card"
              style={{
                cursor: "pointer",
                borderColor: selected?.id === f.id ? "var(--primary)" : undefined,
              }}
              onClick={() => selectFamily(f)}
            >
              <h3 style={{ margin: 0 }}>{f.name}</h3>
              <div className="muted">{f.members.length} member(s)</div>
            </div>
          ))}
        </div>
      )}

      {selected && (
        <>
          <div className="card">
            <div className="card-head">
              <h3 style={{ margin: 0 }}>{selected.name} — members</h3>
              {isAdmin && (
                <button className="btn sm" onClick={createInvite}>
                  + Invite code
                </button>
              )}
            </div>
            <table>
              <thead>
                <tr>
                  <th>Member</th>
                  <th>Role</th>
                </tr>
              </thead>
              <tbody>
                {selected.members.map((m) => (
                  <tr key={m.id}>
                    <td>
                      {m.user_name || m.user_email}
                      {m.user_id === selected.owner_id && (
                        <span className="badge blue" style={{ marginLeft: 8 }}>
                          Owner
                        </span>
                      )}
                    </td>
                    <td>
                      {isAdmin && m.user_id !== selected.owner_id ? (
                        <select
                          value={m.role}
                          onChange={(e) => changeRole(m.id, e.target.value as FamilyRole)}
                          style={{ width: "auto" }}
                        >
                          {ROLES.map((r) => (
                            <option key={r} value={r}>
                              {titleize(r)}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span className="badge">{titleize(m.role)}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {isAdmin && invites.length > 0 && (
            <div className="card">
              <h3>Invite codes</h3>
              <div className="chip-list">
                {invites
                  .filter((i) => !i.revoked)
                  .map((i) => (
                    <span key={i.id} className="badge blue" title={`${i.uses}/${i.max_uses} used`}>
                      {i.code} · {titleize(i.role)} ({i.uses}/{i.max_uses})
                    </span>
                  ))}
              </div>
            </div>
          )}

          {isAdmin && audit.length > 0 && (
            <div className="card">
              <h3>Activity log</h3>
              <table>
                <tbody>
                  {audit.slice(0, 25).map((row) => (
                    <tr key={row.id}>
                      <td>
                        <span className="badge">{row.action}</span>
                      </td>
                      <td className="muted">{row.detail || row.entity_type || ""}</td>
                      <td className="muted" style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                        {fmtDate(row.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {showCreate && (
        <Modal title="New family" onClose={() => setShowCreate(false)}>
          <form onSubmit={createFamily}>
            <label className="field">
              <span className="lbl">Family name</span>
              <input name="name" required placeholder="The Smiths" />
            </label>
            <button className="btn primary" type="submit" style={{ width: "100%" }}>
              Create
            </button>
          </form>
        </Modal>
      )}

      {showJoin && (
        <Modal title="Join a family" onClose={() => setShowJoin(false)}>
          <form onSubmit={join}>
            {error && <div className="notice error" style={{ marginBottom: 12 }}>{error}</div>}
            <label className="field">
              <span className="lbl">Invite code</span>
              <input name="code" required placeholder="ABC12XYZ" />
            </label>
            <button className="btn primary" type="submit" style={{ width: "100%" }}>
              Join
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}
