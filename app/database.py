import os
from urllib.parse import urlparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Обязательно берём Postgres из переменной окружения на Render
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise RuntimeError(
        "DATABASE_URL не задан. Задайте переменную окружения на Render (Neon SQLAlchemy URL с sslmode=require)."
    )

# Соединение с Postgres (sync, psycopg2), с пингом пула
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
        # не печатаем логин/пароль
        dbname = p.path.rsplit("/", 1)[-1] if "/" in p.path else p.path
        return f"{p.scheme}://{p.hostname}/{dbname}?{p.query}"
    except Exception:
        return "<hidden>"

print(f"[Truepicc] DATABASE_URL -> {_mask_db_url(DB_URL)}")
