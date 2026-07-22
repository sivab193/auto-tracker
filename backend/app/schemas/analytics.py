from __future__ import annotations

from pydantic import BaseModel


class MonthlyCost(BaseModel):
    month: str  # YYYY-MM
    fuel: float = 0.0
    service: float = 0.0
    total: float = 0.0


class VehicleAnalytics(BaseModel):
    vehicle_id: int
    total_fuel_cost: float = 0.0
    total_service_cost: float = 0.0
    total_cost: float = 0.0
    fuel_events: int = 0
    service_events: int = 0
    avg_efficiency: float | None = None
    best_efficiency: float | None = None
    worst_efficiency: float | None = None
    cost_per_distance: float | None = None
    distance_tracked: int = 0
    monthly: list[MonthlyCost] = []


class DashboardSummary(BaseModel):
    vehicles: int = 0
    documents: int = 0
    expiring_soon: int = 0
    pending_alerts: int = 0
    total_spend: float = 0.0
