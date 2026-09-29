import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "server"))

from app.config import get_settings  # noqa: E402
from app.database.schema import prepare_database  # noqa: E402
from app.database.seed import seed_if_empty  # noqa: E402
from app.database.session import configure_engine, open_session  # noqa: E402
from app.main import app  # noqa: E402

_ready = False
_PATH_HEADERS = (
    "x-forwarded-uri",
    "x-original-uri",
    "x-invoke-path",
    "x-matched-path",
    "x-vercel-original-path",
    "x-middleware-rewrite",
)


def _original_api_path(scope: dict) -> str | None:
    raw_path = scope.get("raw_path") or b""
    if raw_path.startswith(b"/api/"):
        return raw_path.decode().split("?", 1)[0]
    headers = {
        key.decode().lower(): value.decode()
        for key, value in scope.get("headers", [])
        if isinstance(key, bytes)
    }
    for name in _PATH_HEADERS:
        raw = headers.get(name, "")
        path = raw.split("?", 1)[0]
        if path.startswith("/api/"):
            return path
    return None


def _boot() -> None:
    settings = get_settings()
    db_engine = configure_engine(settings.database_url)
    prepare_database(db_engine)
    if settings.seed_on_startup:
        session = open_session()
        try:
            seed_if_empty(session)
        finally:
            session.close()


@app.middleware("http")
async def boot_database(request, call_next):
    global _ready
    path = _original_api_path(request.scope)
    if path and request.scope.get("path") in {"/api", "/", ""}:
        request.scope["path"] = path
    if not _ready:
        _boot()
        _ready = True
    return await call_next(request)
