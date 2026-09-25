"""
Database seeder.

Run with:  python -m app.utils.seed
Or via Docker:  docker-compose exec backend python -m app.utils.seed

Creates:
  1. Default admin user (from settings)
  2. Schedule II commodities in the products table
     (standard pack sizes per the Second Schedule of the Rules)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, engine
from app.models import User, UserRole, Manufacturer, Product

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Schedule II Commodities ───────────────────────────────────────────────────
# Source: Second Schedule, Legal Metrology (Packaged Commodities) Rules, 2011
# pack_sizes are in grams (for solids) or ml (for liquids)
SCHEDULE_II_COMMODITIES = [
    {
        "generic_name": "Mineral Water",
        "category": "Beverages",
        "standard_pack_sizes": ["100", "150", "200", "250", "300", "500", "750",
                                  "1000", "1500", "2000", "3000", "4000", "5000"],
    },
    {
        "generic_name": "Drinking Water",
        "category": "Beverages",
        "standard_pack_sizes": ["100", "150", "200", "250", "300", "500", "750",
                                  "1000", "1500", "2000", "3000", "4000", "5000"],
    },
    {
        "generic_name": "Refined Edible Oil",
        "category": "Edible Oils",
        "standard_pack_sizes": ["100", "200", "250", "500", "1000", "2000", "5000"],
    },
    {
        "generic_name": "Vanaspati",
        "category": "Edible Oils",
        "standard_pack_sizes": ["500", "1000", "2000", "5000"],
    },
    {
        "generic_name": "Milk",
        "category": "Dairy",
        "standard_pack_sizes": ["200", "250", "500", "1000"],
    },
    {
        "generic_name": "Wheat Flour (Atta)",
        "category": "Cereals & Flour",
        "standard_pack_sizes": ["500", "1000", "2000", "5000", "10000"],
    },
    {
        "generic_name": "Maida",
        "category": "Cereals & Flour",
        "standard_pack_sizes": ["500", "1000", "2000", "5000"],
    },
    {
        "generic_name": "Rice",
        "category": "Cereals & Grains",
        "standard_pack_sizes": ["500", "1000", "2000", "5000", "10000", "25000"],
    },
    {
        "generic_name": "Sugar",
        "category": "Sugar & Sweeteners",
        "standard_pack_sizes": ["500", "1000", "2000", "5000", "10000"],
    },
    {
        "generic_name": "Salt (Common Salt)",
        "category": "Condiments",
        "standard_pack_sizes": ["100", "200", "500", "1000", "2000"],
    },
    {
        "generic_name": "Pulses (Dal)",
        "category": "Pulses",
        "standard_pack_sizes": ["250", "500", "1000", "2000", "5000"],
    },
    {
        "generic_name": "Tea",
        "category": "Beverages",
        "standard_pack_sizes": ["25", "50", "100", "200", "250", "500", "1000"],
    },
    {
        "generic_name": "Coffee",
        "category": "Beverages",
        "standard_pack_sizes": ["25", "50", "100", "200", "250", "500"],
    },
    {
        "generic_name": "Butter",
        "category": "Dairy",
        "standard_pack_sizes": ["100", "200", "500"],
    },
    {
        "generic_name": "Ghee",
        "category": "Dairy",
        "standard_pack_sizes": ["100", "200", "500", "1000"],
    },
    {
        "generic_name": "Cement",
        "category": "Construction Materials",
        "standard_pack_sizes": ["1000", "2000", "5000", "10000", "25000", "50000"],
    },
    {
        "generic_name": "Fertilizer",
        "category": "Agricultural",
        "standard_pack_sizes": ["1000", "2000", "5000", "10000", "25000", "50000"],
    },
    {
        "generic_name": "Liquefied Petroleum Gas (LPG)",
        "category": "Fuel",
        "standard_pack_sizes": ["5000", "14200"],
    },
]


def seed_admin_user(db: Session) -> None:
    """Create the default admin user if it doesn't already exist."""
    existing = db.query(User).filter(User.email == settings.admin_email).first()
    if existing:
        print(f"  Admin user already exists: {settings.admin_email}")
        return

    admin = User(
        name=settings.admin_name,
        email=settings.admin_email,
        hashed_password=pwd_context.hash(settings.admin_password),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    print(f"  ✓ Admin user created: {settings.admin_email}")


def seed_schedule_ii_commodities(db: Session) -> None:
    """
    Seed Schedule II commodity reference entries.
    These are template products (no brand/manufacturer) used by the
    compliance engine to look up permitted pack sizes.
    """
    for commodity in SCHEDULE_II_COMMODITIES:
        existing = (
            db.query(Product)
            .filter(
                Product.generic_name == commodity["generic_name"],
                Product.brand == None,  # noqa: E711 — intentional None check
            )
            .first()
        )
        if existing:
            # Update pack sizes in case they changed
            existing.standard_pack_sizes = commodity["standard_pack_sizes"]
            existing.is_schedule_ii_commodity = True
            continue

        product = Product(
            name=f"[Schedule II] {commodity['generic_name']}",
            generic_name=commodity["generic_name"],
            brand=None,
            category=commodity["category"],
            is_schedule_ii_commodity=True,
            standard_pack_sizes=commodity["standard_pack_sizes"],
        )
        db.add(product)

    db.commit()
    print(f"  ✓ {len(SCHEDULE_II_COMMODITIES)} Schedule II commodity entries seeded.")


def run_seed() -> None:
    print("\nLabelGuard — Database Seeder")
    print("=" * 40)

    db: Session = SessionLocal()
    try:
        print("\n[1/2] Seeding admin user...")
        seed_admin_user(db)

        print("\n[2/2] Seeding Schedule II commodities...")
        seed_schedule_ii_commodities(db)

        print("\n✓ Seeding complete.\n")
    except Exception as e:
        print(f"\n✗ Seeding failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
