import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { useAuth } from "./context/AuthContext";
import Alerts from "./pages/Alerts";
import Dashboard from "./pages/Dashboard";
import FamilyPage from "./pages/Family";
import Login from "./pages/Login";
import Settings from "./pages/Settings";
import VehicleDetail from "./pages/VehicleDetail";
import Vehicles from "./pages/Vehicles";

export default function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="loader">Loading AutoTracker…</div>;
  }

  if (!user) {
    return (
      <Routes>
        <Route path="*" element={<Login />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="/vehicles" element={<Vehicles />} />
        <Route path="/vehicles/:id" element={<VehicleDetail />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/family" element={<FamilyPage />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
