from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Called on startup."""
    from app.models import user, company, receipt, approval_rule, pre_approved_item  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _ensure_receipt_item_quantity_column()


def _ensure_receipt_item_quantity_column():
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if "receipt_items" not in table_names:
        return

    columns = {col["name"] for col in inspector.get_columns("receipt_items")}
    if "quantity" in columns:
        return

    ddl = "ALTER TABLE receipt_items ADD COLUMN quantity INTEGER"
    with engine.begin() as conn:
        conn.execute(text(ddl))
