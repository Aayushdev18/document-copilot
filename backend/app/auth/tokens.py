import base64
import hashlib
import hmac
import time


class InvalidToken(Exception):
    pass


def issue_token(user_id: str, secret: str, ttl_seconds: int, email: str = "") -> str:
    expires_at = int(time.time()) + ttl_seconds
    email_part = base64.urlsafe_b64encode(email.encode()).decode().rstrip("=")
    payload = f"{user_id}.{expires_at}.{email_part}"
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def read_token(token: str, secret: str) -> tuple[str, str]:
    parts = token.split(".")
    if len(parts) != 4:
        raise InvalidToken
    user_id, expires_at, email_part, signature = parts
    if not user_id or not expires_at or not email_part or not signature:
        raise InvalidToken
    payload = f"{user_id}.{expires_at}.{email_part}"
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise InvalidToken
    try:
        expiry = int(expires_at)
        padding = "=" * (-len(email_part) % 4)
        email = base64.urlsafe_b64decode(email_part + padding).decode()
    except (ValueError, UnicodeDecodeError) as error:
        raise InvalidToken from error
    if expiry < int(time.time()) or "@" not in email:
        raise InvalidToken
    return user_id, email
