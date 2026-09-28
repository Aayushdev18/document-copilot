from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.database.models import Base


def prepare_database(db_engine: Engine) -> None:
    Base.metadata.create_all(db_engine)
    with db_engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(
                    chunk_id UNINDEXED,
                    text,
                    tokenize='porter'
                )
                """
            )
        )
