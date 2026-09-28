import hashlib
import hmac
import time


class InvalidToken(Exception):
    pass


def issue_token(user_id: str, secret: str, ttl_seconds: int) -> str:
    expires_at = int(time.time()) + ttl_seconds
    payload = f"{user_id}.{expires_at}"
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def read_user_id(token: str, secret: str) -> str:
    user_id, separator, rest = token.partition(".")
    expires_at, separator_2, signature = rest.partition(".")
    if not user_id or not separator or not separator_2 or not expires_at or not signature:
        raise InvalidToken
    payload = f"{user_id}.{expires_at}"
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise InvalidToken
    try:
        expiry = int(expires_at)
    except ValueError as error:
        raise InvalidToken from error
    if expiry < int(time.time()):
        raise InvalidToken
    return user_id
