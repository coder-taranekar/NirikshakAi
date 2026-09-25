"""
Database setup: SQLAlchemy async engine, session factory, and base model.
All models inherit from Base declared here.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

# ── Engine ────────────────────────────────────────────────────────────────────
# Using synchronous engine for simplicity in MVP.
# connect_args only needed for SQLite; omitted here for PostgreSQL.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,       # Recycles stale connections automatically
    pool_size=10,
    max_overflow=20,
    echo=settings.is_development,  # SQL logging in dev only
)

# ── Session Factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ── Declarative Base ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """
    All SQLAlchemy ORM models inherit from this class.
    """
    pass


# ── Dependency ────────────────────────────────────────────────────────────────
def get_db():
    """
    FastAPI dependency that yields a database session and
    ensures it is closed after the request completes.

    Usage in a router:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """
    Attempts a lightweight query to verify DB connectivity.
    Used by the /health endpoint.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
