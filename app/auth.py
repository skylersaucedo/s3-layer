import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from .db.models import APICredentials
from .db.engine import SessionLocal
from sqlalchemy import select

security = HTTPBasic()


def authenticate_user(credentials: HTTPBasicCredentials = Depends(security)):
    session = SessionLocal()

    stmt = select(APICredentials).where(
        APICredentials.api_key == credentials.username.encode("utf8")
    )

    result = session.execute(stmt)

    valid_users = result.all()

    if len(valid_users) == 0 or len(valid_users) > 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    valid_user = valid_users[0][0]

    is_correct_password = valid_user.validate_password(credentials.password)

    if not (is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    return valid_user
