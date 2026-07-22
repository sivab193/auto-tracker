"""Enumerations shared across models and schemas."""
from __future__ import annotations

import enum


class DocumentType(str, enum.Enum):
    registration = "registration"          # RC / vehicle registration
    insurance = "insurance"                # insurance policy
    pollution = "pollution"                # PUC / emission certificate
    road_tax = "road_tax"
    fitness = "fitness"                    # fitness certificate
    permit = "permit"
    driving_license = "driving_license"
    warranty = "warranty"
    invoice = "invoice"
    other = "other"


class FuelType(str, enum.Enum):
    petrol = "petrol"
    diesel = "diesel"
    cng = "cng"
    lpg = "lpg"
    electric = "electric"
    hybrid = "hybrid"


class ServiceType(str, enum.Enum):
    routine = "routine"
    repair = "repair"
    inspection = "inspection"
    tyre = "tyre"
    battery = "battery"
    other = "other"


class FamilyRole(str, enum.Enum):
    admin = "admin"
    member = "member"
    viewer = "viewer"


class AlertChannel(str, enum.Enum):
    in_app = "in_app"
    telegram = "telegram"
    email = "email"


class AlertStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    acknowledged = "acknowledged"
    dismissed = "dismissed"
