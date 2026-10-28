from collections.abc import Generator
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()
DATABASE_URL = (
    f"mysql+pymysql://{quote_plus(settings.db_user)}:{quote_plus(settings.db_password)}"
    f"@{settings.db_host}:{settings.db_port}/{settings.db_name}?charset=utf8mb4"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    echo=settings.db_echo,
    connect_args={"connect_timeout": 5},
)
SessionLocal = sessionmaker(
    bind=engine, class_=Session, autoflush=False, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection() -> str:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT DATABASE()"))
        database_name = result.scalar()
        if not database_name:
            raise RuntimeError("Connected but no database is selected")
        return str(database_name)
