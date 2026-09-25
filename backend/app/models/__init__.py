"""
Models package — imports all ORM models so Alembic can discover them
when generating migrations.

Import order matters: models with no FK dependencies come first.
"""

from app.models.user import User, UserRole  # noqa: F401
from app.models.manufacturer import Manufacturer, ViolationRecord, PenaltyTier  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.inspection import Inspection, InspectionStatus, InspectionSource  # noqa: F401
