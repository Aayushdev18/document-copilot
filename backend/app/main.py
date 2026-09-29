from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.config import get_settings
from app.database.schema import prepare_database
from app.database.seed import seed_if_empty
from app.database.session import configure_engine, open_session

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ]
)
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    db_engine = configure_engine(settings.database_url)
    prepare_database(db_engine)
    if settings.seed_on_startup:
        session = open_session()
        try:
            seed_if_empty(session)
        finally:
            session.close()
        log.info("corpus.ready")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Document Copilot", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router)
    app.include_router(chat_router)
    app.include_router(auth_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")

    @app.get("/health")
    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
