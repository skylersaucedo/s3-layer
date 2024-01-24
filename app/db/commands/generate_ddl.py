from ..engine import Base
from ..engine import engine

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
