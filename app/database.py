import os
from datetime import datetime

from sqlalchemy import create_engine, String, Float, Boolean, DateTime, Integer, Text, MetaData
from sqlalchemy.orm import declarative_base, Mapped, mapped_column

# ---- DATABASE URL (Render/Neon) ----
DB_URL = os.getenv("DATABASE_URL", "").strip()
if not DB_URL:
    raise RuntimeError("DATABASE_URL is not set")

# normalize driver: psycopg3
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DB_URL.startswith("postgresql://"):
    DB_URL = DB_URL.replace("postgresql://", "postgresql+psycopg://", 1)

POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "5"))

engine = create_engine(
    DB_URL,
    pool_pre_ping=True,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
)

# ---- ORM base ----
metadata = MetaData()
Base = declarative_base(metadata=metadata)

# ---- Models (must be importable in main.py) ----
class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # nanoid
    verify_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # storage
    storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # device/time/location
    device_time_utc: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow, index=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    altitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)

    # request meta
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(256), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow, index=True)


class PhotoAudit(Base):
    __tablename__ = "photo_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    photo_id: Mapped[int] = mapped_column(Integer, index=True)
    field: Mapped[str] = mapped_column(String(64))
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    edited_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    edited_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow, index=True)

# ---- Backward-compat exports for main.py ----
ENGINE = engine
