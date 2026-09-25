"""
Product model — the catalog of packaged commodities.

Products can be:
  1. Pre-loaded via CSV bulk import by admins (known brands/products)
  2. Registered on-the-fly by inspectors during a scan

Schedule II commodities (e.g. mineral water) have restricted pack sizes
stored in standard_pack_sizes — validated by the compliance engine.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Represents a packaged commodity product.

    generic_name: The commodity type (e.g. "Mineral Water", "Refined Oil").
                  Used for Schedule II pack size lookup and rule matching.

    standard_pack_sizes: For Schedule II commodities, stores the list of
                         permitted pack sizes in grams/ml as declared by
                         the Second Schedule of the Rules.
                         Example: [100, 150, 200, 250, 300, 500, 750, 1000]

    is_schedule_ii_commodity: True if this product's generic_name appears
                               in Schedule II (restricted pack sizes apply).
    """

    __tablename__ = "products"

    # Core identity
    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    generic_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    brand: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(255), nullable=True, index=True)

    # Barcode (EAN-13, UPC, QR code value, etc.)
    barcode: Mapped[str] = mapped_column(String(100), nullable=True, unique=True, index=True)

    # Image stored in MinIO; URL saved here
    image_url: Mapped[str] = mapped_column(String(1000), nullable=True)

    # Schedule II pack size enforcement
    is_schedule_ii_commodity: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    # List of permitted quantities in g or ml (e.g. [100, 200, 500, 1000])
    standard_pack_sizes: Mapped[list] = mapped_column(
        ARRAY(String(50)), nullable=True, default=list
    )

    # Additional metadata (flexible key-value for category-specific fields)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, nullable=True, default=dict)

    # ── Foreign Keys ──────────────────────────────────────────────────
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("manufacturers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    registered_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Relationships ─────────────────────────────────────────────────
    manufacturer: Mapped["Manufacturer"] = relationship(  # noqa: F821
        "Manufacturer",
        back_populates="products",
    )
    registered_by_user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="registered_products",
    )
    inspections: Mapped[list["Inspection"]] = relationship(  # noqa: F821
        "Inspection",
        back_populates="product",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<Product id={self.id} name={self.name} brand={self.brand}>"
