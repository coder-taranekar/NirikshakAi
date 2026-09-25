"""Initial schema — create all core tables

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000

Tables created:
  - users
  - manufacturers
  - violation_records
  - products
  - inspections

Enums created:
  - user_role
  - penalty_tier
  - inspection_source
  - inspection_status
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enums ──────────────────────────────────────────────────────────
    user_role = postgresql.ENUM("inspector", "admin", name="user_role", create_type=True)
    user_role.create(op.get_bind(), checkfirst=True)

    penalty_tier = postgresql.ENUM(
        "first", "second", "subsequent", name="penalty_tier", create_type=True
    )
    penalty_tier.create(op.get_bind(), checkfirst=True)

    inspection_source = postgresql.ENUM(
        "camera", "upload", "url", name="inspection_source", create_type=True
    )
    inspection_source.create(op.get_bind(), checkfirst=True)

    inspection_status = postgresql.ENUM(
        "pending", "compliant", "partial", "non_compliant",
        name="inspection_status", create_type=True
    )
    inspection_status.create(op.get_bind(), checkfirst=True)

    # ── users ──────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("inspector", "admin", name="user_role"),
            nullable=False,
            server_default="inspector",
        ),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("district", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── manufacturers ──────────────────────────────────────────────────
    op.create_table(
        "manufacturers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("registered_address", sa.Text(), nullable=False),
        sa.Column("registration_number", sa.String(100), nullable=True),
        sa.Column(
            "states_operating",
            postgresql.ARRAY(sa.String(100)),
            nullable=True,
        ),
        sa.Column("contact_phone", sa.String(20), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("registration_number"),
    )
    op.create_index("ix_manufacturers_name", "manufacturers", ["name"])
    op.create_index(
        "ix_manufacturers_registration_number",
        "manufacturers",
        ["registration_number"],
        unique=True,
    )

    # ── products ───────────────────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("generic_name", sa.String(255), nullable=False),
        sa.Column("brand", sa.String(255), nullable=True),
        sa.Column("category", sa.String(255), nullable=True),
        sa.Column("barcode", sa.String(100), nullable=True),
        sa.Column("image_url", sa.String(1000), nullable=True),
        sa.Column(
            "is_schedule_ii_commodity", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "standard_pack_sizes",
            postgresql.ARRAY(sa.String(50)),
            nullable=True,
        ),
        sa.Column("extra_metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "manufacturer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("manufacturers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "registered_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("barcode"),
    )
    op.create_index("ix_products_name", "products", ["name"])
    op.create_index("ix_products_generic_name", "products", ["generic_name"])
    op.create_index("ix_products_brand", "products", ["brand"])
    op.create_index("ix_products_barcode", "products", ["barcode"], unique=True)
    op.create_index("ix_products_manufacturer_id", "products", ["manufacturer_id"])

    # ── inspections ────────────────────────────────────────────────────
    op.create_table(
        "inspections",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.Enum("camera", "upload", "url", name="inspection_source"),
            nullable=False,
            server_default="upload",
        ),
        sa.Column("source_url", sa.String(2000), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("district", sa.String(100), nullable=True),
        sa.Column("image_url", sa.String(1000), nullable=True),
        sa.Column("annotated_image_url", sa.String(1000), nullable=True),
        sa.Column("ocr_result", postgresql.JSONB(), nullable=True),
        sa.Column("compliance_result", postgresql.JSONB(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "compliant", "partial", "non_compliant", name="inspection_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "hard_fail_triggered", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("penalty_tier", sa.String(50), nullable=True),
        sa.Column("estimated_penalty_min", sa.Integer(), nullable=True),
        sa.Column("estimated_penalty_max", sa.Integer(), nullable=True),
        sa.Column("inspector_notes", sa.Text(), nullable=True),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "inspector_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inspections_status", "inspections", ["status"])
    op.create_index("ix_inspections_state", "inspections", ["state"])
    op.create_index("ix_inspections_product_id", "inspections", ["product_id"])
    op.create_index("ix_inspections_inspector_id", "inspections", ["inspector_id"])
    op.create_index("ix_inspections_created_at", "inspections", ["created_at"])

    # ── violation_records ──────────────────────────────────────────────
    op.create_table(
        "violation_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "manufacturer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("manufacturers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "inspection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("inspections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("state", sa.String(100), nullable=False),
        sa.Column("offence_type", sa.String(255), nullable=False),
        sa.Column(
            "penalty_tier",
            sa.Enum("first", "second", "subsequent", name="penalty_tier"),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_violation_records_manufacturer_id",
        "violation_records",
        ["manufacturer_id"],
    )
    op.create_index(
        "ix_violation_records_inspection_id",
        "violation_records",
        ["inspection_id"],
    )


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("violation_records")
    op.drop_table("inspections")
    op.drop_table("products")
    op.drop_table("manufacturers")
    op.drop_table("users")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS inspection_status")
    op.execute("DROP TYPE IF EXISTS inspection_source")
    op.execute("DROP TYPE IF EXISTS penalty_tier")
    op.execute("DROP TYPE IF EXISTS user_role")
