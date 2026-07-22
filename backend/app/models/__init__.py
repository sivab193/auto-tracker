"""ORM models. Importing this package registers every table on the metadata."""
from __future__ import annotations

from app.models.alert import Alert, AuditLog
from app.models.document import Document
from app.models.family import Family, FamilyInvite, FamilyMembership
from app.models.fuel import FuelLog
from app.models.service import AccidentRecord, ServiceRecord
from app.models.user import User
from app.models.vehicle import Vehicle

__all__ = [
    "User",
    "Vehicle",
    "Document",
    "ServiceRecord",
    "AccidentRecord",
    "FuelLog",
    "Family",
    "FamilyMembership",
    "FamilyInvite",
    "Alert",
    "AuditLog",
]
