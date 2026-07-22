import { useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { User } from "../api/types";
import { useAuth } from "../context/AuthContext";

export default function Settings() {
  const { user, refresh } = useAuth();
  const [name, setName] = useState(user?.name ?? "");
  const [lang, setLang] = useState(user?.preferred_language ?? "en");
  const [saved, setSaved] = useState(false);
  const [linkCode, setLinkCode] = useState<string | null>(null);
  const [linkMsg, setLinkMsg] = useState<string | null>(null);

  async function saveProfile(e: FormEvent) {
    e.preventDefault();
    await api.patch<User>("/api/auth/me", { name, preferred_language: lang });
    await refresh();
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  async function genCode() {
    const res = await api.post<{ code: string; instructions: string }>(
      "/api/auth/telegram/link-code",
    );
    setLinkCode(res.code);
    setLinkMsg(res.instructions);
  }

  async function unlink() {
    await api.del("/api/auth/telegram/link");
    await refresh();
    setLinkCode(null);
    setLinkMsg(null);
  }

  return (
    <div>
      <h1>Settings</h1>

      <div className="card" style={{ maxWidth: 560 }}>
        <h3>Profile</h3>
        <form onSubmit={saveProfile}>
          <label className="field">
            <span className="lbl">Email</span>
            <input value={user?.email ?? ""} disabled />
          </label>
          <label className="field">
            <span className="lbl">Name</span>
            <input value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label className="field">
            <span className="lbl">Preferred language</span>
            <select value={lang} onChange={(e) => setLang(e.target.value)}>
              <option value="en">English</option>
              <option value="hi">हिन्दी (Hindi)</option>
              <option value="es">Español</option>
              <option value="de">Deutsch</option>
            </select>
          </label>
          <div className="row">
            <button className="btn primary" type="submit">
              Save profile
            </button>
            {saved && <span className="notice success">Saved ✓</span>}
          </div>
        </form>
      </div>

      <div className="card" style={{ maxWidth: 560 }}>
        <h3>Telegram bot</h3>
        <p className="muted" style={{ marginTop: -4 }}>
          Link your account to fetch documents on the go. Files sent by the bot auto-delete for
          privacy.
        </p>
        {user?.telegram_chat_id ? (
          <div className="row between">
            <span className="notice success">Connected ✓</span>
            <button className="btn danger" onClick={unlink}>
              Unlink
            </button>
          </div>
        ) : (
          <>
            <button className="btn primary" onClick={genCode}>
              Generate link code
            </button>
            {linkCode && (
              <div className="notice info" style={{ marginTop: 12 }}>
                <div>
                  Your code: <strong style={{ fontSize: "1.1rem" }}>{linkCode}</strong>
                </div>
                <div style={{ marginTop: 4 }}>{linkMsg}</div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
