from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

import jwt as pyjwt

import nta_user_svc.config as config

logger = logging.getLogger(__name__)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token containing the provided data and an expiration (exp) claim.

    Args:
        data: dictionary payload to include in the token (e.g., {"user_id": ...}).
        expires_delta: optional timedelta to override default expiry.

    Returns:
        A signed JWT as a string.

    Raises:
        Exception: Any exception from PyJWT encoding is logged and re-raised.
    """
    try:
        to_encode = data.copy()
        if expires_delta is None:
            expires_delta = timedelta(hours=int(config.JWT_EXP_HOURS))
        expire = datetime.utcnow() + expires_delta
        # Use integer unix timestamp for exp claim
        to_encode.update({"exp": int(expire.timestamp())})
        token = pyjwt.encode(to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
        # PyJWT >=2 returns str, but handle bytes defensively
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        return token
    except Exception as e:
        logger.error(e, exc_info=True)
        # Re-raise so callers/tests can handle specific PyJWT exceptions
        raise


def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode a JWT token.

    Args:
        token: JWT token string.

    Returns:
        Decoded token payload as a dictionary.

    Raises:
        pyjwt.ExpiredSignatureError: if token is expired.
        pyjwt.InvalidTokenError: if token is invalid for any reason.
        Exception: any other exception during decode is logged and re-raised.
    """
    try:
        payload = pyjwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        return payload
    except pyjwt.ExpiredSignatureError as e:
        logger.error(e, exc_info=True)
        raise
    except pyjwt.InvalidTokenError as e:
        logger.error(e, exc_info=True)
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        raise
