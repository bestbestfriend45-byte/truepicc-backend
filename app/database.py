import os
from urllib.parse import urlparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Р С›Р В±РЎРЏР В·Р В°РЎвЂљР ВµР В»РЎРЉР Р…Р С• Р В±Р ВµРЎР‚РЎвЂР С Postgres Р С‘Р В· Р С—Р ВµРЎР‚Р ВµР СР ВµР Р…Р Р…Р С•Р в„– Р С•Р С”РЎР‚РЎС“Р В¶Р ВµР Р…Р С‘РЎРЏ Р Р…Р В° Render
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise RuntimeError(
        "DATABASE_URL Р Р…Р Вµ Р В·Р В°Р Т‘Р В°Р Р…. Р вЂ”Р В°Р Т‘Р В°Р в„–РЎвЂљР Вµ Р С—Р ВµРЎР‚Р ВµР СР ВµР Р…Р Р…РЎС“РЎР‹ Р С•Р С”РЎР‚РЎС“Р В¶Р ВµР Р…Р С‘РЎРЏ Р Р…Р В° Render (Neon SQLAlchemy URL РЎРѓ sslmode=require)."
    )

# Р РЋР С•Р ВµР Т‘Р С‘Р Р…Р ВµР Р…Р С‘Р Вµ РЎРѓ Postgres (sync, psycopg2), РЎРѓ Р С—Р С‘Р Р…Р С–Р С•Р С Р С—РЎС“Р В»Р В°
engine = create_engine(
    DB_URL,
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "5")),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def _mask_db_url(u: str) -> str:
    try:
        p = urlparse(u)
        # Р Р…Р Вµ Р С—Р ВµРЎвЂЎР В°РЎвЂљР В°Р ВµР С Р В»Р С•Р С–Р С‘Р Р…/Р С—Р В°РЎР‚Р С•Р В»РЎРЉ
        dbname = p.path.rsplit("/", 1)[-1] if "/" in p.path else p.path
        return f"{p.scheme}://{p.hostname}/{dbname}?{p.query}"
    except Exception:
        return "<hidden>"

print(f"[Truepicc] DATABASE_URL -> {_mask_db_url(DB_URL)}")
