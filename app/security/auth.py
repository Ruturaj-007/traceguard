from fastapi import Header
from app.config import settings
from app.exceptions import InvalidApiKeyError


def verify_api_key(x_api_key: str = Header(...)) -> str:
    """Verify the API key from the request header."""
    if x_api_key != settings.api_key:
        raise InvalidApiKeyError()
    return x_api_key