import os
from urllib.parse import urlparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Р В РЎвЂєР В Р’В±Р РЋР РЏР В Р’В·Р В Р’В°Р РЋРІР‚С™Р В Р’ВµР В Р’В»Р РЋР Р‰Р В Р вЂ¦Р В РЎвЂў Р В Р’В±Р В Р’ВµР РЋР вЂљР РЋРІР‚ВР В РЎВ Postgres Р В РЎвЂР В Р’В· Р В РЎвЂ”Р В Р’ВµР РЋР вЂљР В Р’ВµР В РЎВР В Р’ВµР В Р вЂ¦Р В Р вЂ¦Р В РЎвЂўР В РІвЂћвЂ“ Р В РЎвЂўР В РЎвЂќР РЋР вЂљР РЋРЎвЂњР В Р’В¶Р В Р’ВµР В Р вЂ¦Р В РЎвЂР РЋР РЏ Р В Р вЂ¦Р В Р’В° Render
DB_URL = os.getenv("DATABASE_URL")
# normalize driver for Render/Neon
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DB_URL.startswith("postgresql://"):
    DB_URL = DB_URL.replace("postgresql://", "postgresql+psycopg://", 1)
# normalize
if not DB_URL:
    raise RuntimeError(
        "DATABASE_URL Р В Р вЂ¦Р В Р’Вµ Р В Р’В·Р В Р’В°Р В РўвЂР В Р’В°Р В Р вЂ¦. Р В РІР‚вЂќР В Р’В°Р В РўвЂР В Р’В°Р В РІвЂћвЂ“Р РЋРІР‚С™Р В Р’Вµ Р В РЎвЂ”Р В Р’ВµР РЋР вЂљР В Р’ВµР В РЎВР В Р’ВµР В Р вЂ¦Р В Р вЂ¦Р РЋРЎвЂњР РЋР вЂ№ Р В РЎвЂўР В РЎвЂќР РЋР вЂљР РЋРЎвЂњР В Р’В¶Р В Р’ВµР В Р вЂ¦Р В РЎвЂР РЋР РЏ Р В Р вЂ¦Р В Р’В° Render (Neon SQLAlchemy URL Р РЋР С“ sslmode=require)."
    )

# Р В Р Р‹Р В РЎвЂўР В Р’ВµР В РўвЂР В РЎвЂР В Р вЂ¦Р В Р’ВµР В Р вЂ¦Р В РЎвЂР В Р’Вµ Р РЋР С“ Postgres (sync, psycopg2), Р РЋР С“ Р В РЎвЂ”Р В РЎвЂР В Р вЂ¦Р В РЎвЂ“Р В РЎвЂўР В РЎВ Р В РЎвЂ”Р РЋРЎвЂњР В Р’В»Р В Р’В°
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
        # Р В Р вЂ¦Р В Р’Вµ Р В РЎвЂ”Р В Р’ВµР РЋРІР‚РЋР В Р’В°Р РЋРІР‚С™Р В Р’В°Р В Р’ВµР В РЎВ Р В Р’В»Р В РЎвЂўР В РЎвЂ“Р В РЎвЂР В Р вЂ¦/Р В РЎвЂ”Р В Р’В°Р РЋР вЂљР В РЎвЂўР В Р’В»Р РЋР Р‰
        dbname = p.path.rsplit("/", 1)[-1] if "/" in p.path else p.path
        return f"{p.scheme}://{p.hostname}/{dbname}?{p.query}"
    except Exception:
        return "<hidden>"

print(f"[Truepicc] DATABASE_URL -> {_mask_db_url(DB_URL)}")
