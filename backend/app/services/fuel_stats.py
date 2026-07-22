"""Recompute per-fill distance & efficiency using the full-to-full method.

For each full-tank fill after the first full tank:
    distance   = odometer - odometer_of_previous_full_tank
    fuel_used  = sum of quantities of every fill (incl. partials) in that span
    efficiency = distance / fuel_used     (distance per unit of fuel)

Partial fills and the very first fill get distance (vs the immediately prior
fill) but no efficiency, since the tank wasn't filled to a known level.

The whole chain is recomputed on every insert/update/delete so out-of-order
entry still yields correct numbers.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fuel import FuelLog


def recompute(db: Session, vehicle_id: int) -> None:
    logs = db.scalars(
        select(FuelLog)
        .where(FuelLog.vehicle_id == vehicle_id)
        .order_by(FuelLog.odometer, FuelLog.fill_date)
    ).all()

    prev_odo: int | None = None
    last_full_odo: int | None = None
    fuel_since_full = 0.0

    for log in logs:
        # Distance vs. the immediately preceding fill (informational).
        if prev_odo is not None and log.odometer > prev_odo:
            log.distance = log.odometer - prev_odo
        else:
            log.distance = None

        fuel_since_full += log.quantity or 0.0

        if log.is_full_tank:
            if last_full_odo is not None and log.odometer > last_full_odo and fuel_since_full > 0:
                span = log.odometer - last_full_odo
                # Efficiency spans multiple partials → report the full-tank distance.
                log.distance = span
                log.efficiency = round(span / fuel_since_full, 3)
            else:
                log.efficiency = None
            last_full_odo = log.odometer
            fuel_since_full = 0.0
        else:
            log.efficiency = None

        prev_odo = log.odometer

    db.commit()
