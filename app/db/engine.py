from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import DeclarativeBase

import os

engine = create_engine(
    f"mysql+mysqldb://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}",
    echo=False,
    pool_recycle=600,
    pool_pre_ping=True,
    pool_size=25,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_local_session():
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()


class Base(DeclarativeBase):
    pass
