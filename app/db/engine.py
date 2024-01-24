from sqlalchemy import create_engine
from ..config import get_settings
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import DeclarativeBase

settings = get_settings()

engine = create_engine(
    f"mysql+mysqldb://{settings.db_username}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}",
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass
