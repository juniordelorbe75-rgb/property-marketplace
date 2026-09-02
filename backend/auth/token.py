import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from dotenv import load_dotenv
from backend.config import validate_secret_key

load_dotenv()


SECRET_KEY = validate_secret_key(os.getenv("SECRET_KEY"))

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120
TOKEN_ISSUER = "property-marketplace-api"
TOKEN_AUDIENCE = "property-marketplace-web"
TOKEN_TYPE = "access"


def create_access_token(data: dict):

    to_encode = data.copy()
    issued_at = datetime.now(timezone.utc)

    expire = issued_at + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({
        "exp": expire,
        "iat": issued_at,
        "iss": TOKEN_ISSUER,
        "aud": TOKEN_AUDIENCE,
        "token_type": TOKEN_TYPE,
    })

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def verify_access_token(token: str):

    payload = decode_access_token(token)
    return payload.get("sub") if payload else None


def decode_access_token(token: str):

    try:
        payload = jwt.decode(
            token, SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=TOKEN_AUDIENCE,
            issuer=TOKEN_ISSUER,
            options={
                "require_exp": True,
                "require_iat": True,
                "require_iss": True,
                "require_aud": True,
                "require_sub": True,
            },
        )

        user_id = payload.get("sub")

        if user_id is None or payload.get("token_type") != TOKEN_TYPE:
            return None

        return payload

    except JWTError:
        return None
