import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDIDATES = (HERE.parent / "server", HERE.parent.parent / "backend")
for candidate in CANDIDATES:
    if (candidate / "app" / "main.py").is_file():
        sys.path.insert(0, str(candidate))
        break

from app.config import get_settings  # noqa: E402
from app.database.schema import prepare_database  # noqa: E402
from app.database.seed import seed_if_empty  # noqa: E402
from app.database.session import configure_engine, open_session  # noqa: E402
from app.main import app  # noqa: E402

_ready = False


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
    if not _ready:
        _boot()
        _ready = True
    return await call_next(request)
