import json
import uuid
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.database.models import DocumentChunk, SourceDocument

SEED_PATH = Path(__file__).resolve().parents[1] / "corpus" / "seed.json"


def seed_if_empty(session: Session) -> None:
    existing = session.scalar(select(func.count()).select_from(SourceDocument))
    if existing:
        return
    payload = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    for document in payload["documents"]:
        source = SourceDocument(
            id=str(uuid.uuid4()),
            ticker=document["ticker"],
            company=document["company"],
            form=document["form"],
            filing_date=document["filing_date"],
            report_date=document["report_date"],
            accession_number=document["accession_number"],
            source_url=document["source_url"],
            year=document["year"],
        )
        session.add(source)
        session.flush()
        for index, chunk in enumerate(document["chunks"]):
            row = DocumentChunk(
                id=str(uuid.uuid4()),
                document_id=source.id,
                chunk_index=index,
                section=chunk["section"],
                text=chunk["text"],
            )
            session.add(row)
            session.flush()
            indexed = f"{source.company} {source.ticker} {row.section} {row.text}"
            session.execute(
                text("INSERT INTO chunk_fts (chunk_id, text) VALUES (:chunk_id, :text)"),
                {"chunk_id": row.id, "text": indexed},
            )
    session.commit()
