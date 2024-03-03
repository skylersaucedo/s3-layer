def generate_ddl():
    from app.db.engine import engine
    from app.db.models import Base

    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    import dotenv

    dotenv.load_dotenv()

    generate_ddl()
