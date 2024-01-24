import uuid
import random
import string
from ..models import APICredentials
from ..engine import SessionLocal
from sqlalchemy import insert

def create_api_key(friendly_name: str) -> None:
    session = SessionLocal()

    salt = "".join(random.choices(string.ascii_letters + string.digits, k=30))
    api_key = "".join(random.choices(string.ascii_letters + string.digits, k=12))
    api_secret = "".join(random.choices(string.ascii_letters + string.digits, k=30))

    session.execute(
        insert(APICredentials).values(
            id=uuid.uuid4(),
            friendly_name=friendly_name,
            api_key=api_key,
            api_secret=APICredentials.hash_password(password=api_secret, salt=salt),
            salt=salt,
        )
    )

    session.commit()

    return api_key, api_secret

if __name__ == "__main__":
    api_key, api_secret = create_api_key("test")
    print(f"api_key: {api_key}")
    print(f"api_secret: {api_secret}")
