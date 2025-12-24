import uuid
from datetime import datetime, timedelta

from jose import jwt

from app.core.config import settings
from app.models.employee import Employee


def create_internal_token(user: Employee, expires_delta: timedelta = None) -> str:
    """
    Generate short-lived internal JWT for API access.

    Includes:
    - sub: user's internal ID
    - jti: unique token ID for revocation
    - type: "access" for token type validation
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Generate unique token ID for revocation support
    jti = str(uuid.uuid4())

    to_encode = {
        "exp": expire,
        "iat": datetime.utcnow(),
        "sub": str(user.id),
        "jti": jti,  # JWT ID for revocation
        "type": "access",  # Token type
        "email": user.email,
        "org_id": str(user.org_id),
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict | None:
    """
    Decode and validate a JWT token.

    Returns payload dict or None if invalid.
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        return None


def get_token_expiry_seconds(token: str) -> int:
    """
    Get remaining seconds until token expires.

    Useful for blacklist TTL.
    """
    payload = decode_token(token)
    if not payload or "exp" not in payload:
        return 0

    exp = datetime.fromtimestamp(payload["exp"])
    remaining = (exp - datetime.utcnow()).total_seconds()
    return max(0, int(remaining))
