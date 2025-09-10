from sqlalchemy import create_engine, Integer, Float, String, Boolean
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped

ENGINE = create_engine("sqlite:///./data.db", connect_args={"check_same_thread": False})

class Base(DeclarativeBase):
    pass

class Photo(Base):
    __tablename__ = "photos"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    created_server_utc: Mapped[str] = mapped_column(String(32))       # ISO-8601 UTC
    device_time_utc: Mapped[str] = mapped_column(String(32))          # ISO-8601 UTC
    tz_offset_min: Mapped[int] = mapped_column(Integer)

    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    altitude_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_mock: Mapped[bool] = mapped_column(Boolean)

    device_model: Mapped[str] = mapped_column(String(64))
    android_api: Mapped[int] = mapped_column(Integer)
    app_version: Mapped[str] = mapped_column(String(32))

    image_key_original: Mapped[str] = mapped_column(String(256))
    image_key_web: Mapped[str] = mapped_column(String(256))
    hash_sha256: Mapped[str] = mapped_column(String(64))

class PhotoAudit(Base):
    __tablename__ = "photo_audit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    photo_id: Mapped[str] = mapped_column(String(40))
    field: Mapped[str] = mapped_column(String(64))
    old_value: Mapped[str] = mapped_column(String(256))
    new_value: Mapped[str] = mapped_column(String(256))
    changed_by: Mapped[str] = mapped_column(String(64))               # admin username
    changed_at_utc: Mapped[str] = mapped_column(String(32))           # ISO-8601 UTC
