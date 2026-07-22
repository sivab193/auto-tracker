import { useState, type FormEvent } from "react";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login, register, config } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, name, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="center-screen">
      <div className="card auth-card">
        <div className="brand" style={{ padding: "0 0 18px" }}>
          <img src="/favicon.svg" alt="" style={{ width: 34, height: 34 }} />
          <span>AutoTracker</span>
        </div>
        <h3>{mode === "login" ? "Sign in" : "Create your account"}</h3>
        <p className="muted" style={{ marginTop: -4 }}>
          Manage your vehicle documents, service history & alerts.
        </p>

        <form onSubmit={submit}>
          {mode === "register" && (
            <label className="field">
              <span className="lbl">Name</span>
              <input value={name} onChange={(e) => setName(e.target.value)} required />
            </label>
          )}
          <label className="field">
            <span className="lbl">Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
              required
            />
          </label>
          <label className="field">
            <span className="lbl">Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
            />
          </label>

          {error && <div className="notice error" style={{ marginBottom: 12 }}>{error}</div>}

          <button className="btn primary" type="submit" disabled={busy} style={{ width: "100%" }}>
            {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>

        {!config?.single_user && (
          <p className="muted" style={{ textAlign: "center", marginTop: 16, fontSize: "0.88rem" }}>
            {mode === "login" ? "No account yet? " : "Already registered? "}
            <a
              onClick={() => {
                setMode(mode === "login" ? "register" : "login");
                setError(null);
              }}
              style={{ cursor: "pointer" }}
            >
              {mode === "login" ? "Sign up" : "Sign in"}
            </a>
          </p>
        )}
      </div>
    </div>
  );
}
