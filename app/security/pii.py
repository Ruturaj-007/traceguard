import re

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(r"\b\d{10}\b")


def mask_pii(message: str) -> str:
    message = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", message)
    message = PHONE_PATTERN.sub("[PHONE_REDACTED]", message)
    return message