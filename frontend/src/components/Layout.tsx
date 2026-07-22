import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV = [
  { to: "/", label: "Dashboard", icon: "▤", end: true },
  { to: "/vehicles", label: "Vehicles", icon: "🚗", end: false },
  { to: "/alerts", label: "Alerts", icon: "🔔", end: false },
  { to: "/family", label: "Family", icon: "👥", end: false },
  { to: "/settings", label: "Settings", icon: "⚙", end: false },
];

function NavItems() {
  return (
    <>
      {NAV.map((n) => (
        <NavLink
          key={n.to}
          to={n.to}
          end={n.end}
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
        >
          <span className="icon">{n.icon}</span>
          {n.label}
        </NavLink>
      ))}
    </>
  );
}

export default function Layout() {
  const { user, logout, config } = useAuth();

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <img src="/favicon.svg" alt="" />
          <span>AutoTracker</span>
        </div>
        <NavItems />
        <div className="nav-spacer" />
        <div className="muted" style={{ fontSize: "0.78rem", padding: "0 10px" }}>
          {user?.name || user?.email}
        </div>
        {!config?.single_user && (
          <button className="btn ghost sm" onClick={logout} style={{ justifyContent: "flex-start" }}>
            Sign out
          </button>
        )}
      </aside>

      <div className="main">
        <div className="topbar">
          <div className="brand" style={{ padding: 0 }}>
            <img src="/favicon.svg" alt="" style={{ width: 24, height: 24 }} />
            <span style={{ fontSize: "1rem" }}>AutoTracker</span>
          </div>
          <div className="row" style={{ gap: 10 }}>
            <span className="badge blue">{config?.single_user ? "Single-user" : "Multi-user"}</span>
            {!config?.single_user && (
              <button className="btn ghost sm" onClick={logout}>
                Sign out
              </button>
            )}
          </div>
        </div>
        {/* Horizontal nav for mobile (sidebar is hidden < 860px). */}
        <nav className="mobile-nav">
          <NavItems />
        </nav>
        <div className="content">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
