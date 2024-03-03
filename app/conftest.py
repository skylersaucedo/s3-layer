import dotenv
import os
import pytest

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

dotenv.load_dotenv(dotenv_path="test.env")


def create_database():
    from .db.commands.generate_ddl import generate_ddl

    """Create a new database for testing. Solve the chicken-and-egg problem by connecting to the default mysql database."""
    engine = create_engine(
        f"mysql+mysqldb://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/mysql",
        echo=False,
        pool_recycle=60,
        pool_pre_ping=False,
        pool_size=1,
    )

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    test_db_name = os.environ["DB_NAME"]

    with SessionLocal() as session:
        session.execute(text(f"CREATE DATABASE {test_db_name}"))
        session.commit()

        generate_ddl()

    print(f"Created database {test_db_name}")


def drop_database():
    """Create a new database for testing. Solve the chicken-and-egg problem by connecting to the default mysql database."""
    engine = create_engine(
        f"mysql+mysqldb://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/mysql",
        echo=False,
        pool_recycle=60,
        pool_pre_ping=False,
        pool_size=1,
    )

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    test_db_name = os.environ["DB_NAME"]

    with SessionLocal() as session:
        session.execute(text(f"DROP DATABASE {test_db_name}"))
        session.commit()

    print(f"Dropped database {test_db_name}")


@pytest.fixture(scope="session", autouse=True)
def my_fixture():
    create_database()
    yield  # this is where the testing happens
    drop_database()
