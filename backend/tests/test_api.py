import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import get_settings
from app.database import session as db_session
from app.database.models import DocumentChunk, SourceDocument
from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("SEED_ON_STARTUP", "false")
    monkeypatch.setenv("AUTH_MODE", "local")
    monkeypatch.setenv("LOCAL_AUTH_SECRET", "test-secret")
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as test_client:
        _insert_corpus()
        yield test_client
    get_settings.cache_clear()


def _insert_corpus() -> None:
    assert db_session.SessionLocal is not None
    session = db_session.SessionLocal()
    document = SourceDocument(
        id=str(uuid.uuid4()),
        ticker="AAPL",
        company="Apple Inc.",
        form="10-K",
        filing_date="2025-10-31",
        report_date="2025-09-27",
        accession_number="0000320193-25-000079",
        source_url="https://www.sec.gov/Archives/edgar/data/320193/example.htm",
        year="2025",
    )
    session.add(document)
    session.flush()
    chunk = DocumentChunk(
        id=str(uuid.uuid4()),
        document_id=document.id,
        chunk_index=0,
        section="Item 1A. Risk Factors",
        text=(
            "The Company uses custom components available from only one source and "
            "depends on those suppliers to deliver sufficient quantities."
        ),
    )
    distraction = DocumentChunk(
        id=str(uuid.uuid4()),
        document_id=document.id,
        chunk_index=1,
        section="Item 1. Business",
        text="Gamers choose NVIDIA GPUs because of the growing population of live streamers.",
    )
    session.add(chunk)
    session.add(distraction)
    session.flush()
    for row in (chunk, distraction):
        session.execute(
            text("INSERT INTO chunk_fts (chunk_id, text) VALUES (:chunk_id, :text)"),
            {
                "chunk_id": row.id,
                "text": f"{document.company} {document.ticker} {row.section} {row.text}",
            },
        )
    session.commit()
    session.close()


def _auth(client: TestClient, email: str = "analyst@driftwood.example") -> dict[str, str]:
    response = client.post("/auth/session", json={"email": email})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def _events(body: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in body.split("\n\n"):
        event = "message"
        data = ""
        for line in block.splitlines():
            if line.startswith("event:"):
                event = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                data += line.removeprefix("data:").strip()
        if data:
            events.append((event, json.loads(data)))
    return events


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/api/health").json() == {"status": "ok"}


def test_vercel_database_is_writable(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL", "1")
    get_settings.cache_clear()
    try:
        assert get_settings().database_url == "sqlite:////tmp/document_copilot.db"
    finally:
        get_settings.cache_clear()


def test_session_rejects_a_bad_email(client: TestClient) -> None:
    response = client.post("/auth/session", json={"email": "not-an-email"})
    assert response.status_code == 422


def test_chat_quotes_a_matching_passage_and_saves_the_thread(client: TestClient) -> None:
    headers = _auth(client)
    response = client.post(
        "/chat/stream",
        headers=headers,
        json={"message": "How does Apple describe its suppliers and custom components?"},
    )
    assert response.status_code == 200
    events = _events(response.text)
    names = [name for name, _payload in events]
    assert names[0] == "thread"
    assert "citations" in names
    assert names[-1] == "done"
    citations = next(payload for name, payload in events if name == "citations")["citations"]
    assert citations[0]["ticker"] == "AAPL"
    assert "suppliers" in citations[0]["excerpt"]

    thread_id = events[0][1]["id"]
    saved = client.get(f"/threads/{thread_id}", headers=headers)
    assert saved.status_code == 200
    messages = saved.json()["messages"]
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[1]["citations"][0]["sourceUrl"].startswith("https://www.sec.gov/")


def test_chat_refuses_when_the_corpus_does_not_cover_the_question(client: TestClient) -> None:
    headers = _auth(client)
    response = client.post(
        "/chat/stream",
        headers=headers,
        json={"message": "What is the population of Lisbon?"},
    )
    events = _events(response.text)
    citations = next(payload for name, payload in events if name == "citations")["citations"]
    assert citations == []
    text = "".join(payload["text"] for name, payload in events if name == "delta")
    assert "does not contain enough evidence" in text


def test_risk_question_cites_item_1a_for_the_selected_company(client: TestClient) -> None:
    headers = _auth(client)
    response = client.post(
        "/chat/stream",
        headers=headers,
        json={"message": "What were the major risks this year?", "ticker": "AAPL"},
    )
    assert response.status_code == 200
    citations = next(
        payload for name, payload in _events(response.text) if name == "citations"
    )["citations"]
    assert citations
    assert citations[0]["ticker"] == "AAPL"
    assert "1A" in citations[0]["section"]
    assert "paragraph" in citations[0]["locator"]


def test_why_revenue_reports_the_change_without_inventing_a_cause(client: TestClient) -> None:
    headers = _auth(client)
    response = client.post(
        "/chat/stream",
        headers=headers,
        json={"message": "Why did revenue increase?", "ticker": "AAPL"},
    )
    assert response.status_code == 200
    events = _events(response.text)
    text = "".join(payload["text"] for name, payload in events if name == "delta")
    citations = next(payload for name, payload in events if name == "citations")["citations"]
    assert "$416.2B" in text
    assert "do not state a cause" in text
    assert citations == []


def test_chat_compares_revenue_from_the_filing_facts(client: TestClient) -> None:
    headers = _auth(client)
    response = client.post(
        "/chat/stream",
        headers=headers,
        json={"message": "Compare this year's revenue with last year.", "ticker": "AAPL"},
    )
    assert response.status_code == 200
    text = "".join(
        payload["text"] for _name, payload in _events(response.text) if _name == "delta"
    )
    assert "$416.2B" in text
    assert "0000320193-25-000079" in text


def test_company_snapshot_and_brief(client: TestClient) -> None:
    headers = _auth(client)
    snapshot = client.get("/companies/AAPL", headers=headers)
    assert snapshot.status_code == 200
    revenue = next(metric for metric in snapshot.json()["metrics"] if metric["key"] == "revenue")
    assert revenue["current"]["display"] == "$416.2B"
    assert revenue["change"] == "+6.4%"
    assert revenue["current"]["sourceUrl"].startswith("https://www.sec.gov/")
    brief = client.post("/companies/AAPL/brief", headers=headers)
    assert brief.status_code == 200
    headings = [section["heading"] for section in brief.json()["sections"]]
    assert "Financial performance" in headings
    assert "Key risks" in headings
    assert "Important takeaways" in headings
    owner = _auth(client, "owner@driftwood.example")
    created = client.post(
        "/chat/stream",
        headers=owner,
        json={"message": "How does Apple describe its suppliers and custom components?"},
    )
    thread_id = _events(created.text)[0][1]["id"]
    other = _auth(client, "other@driftwood.example")
    denied = client.get(f"/threads/{thread_id}", headers=other)
    assert denied.status_code == 403
    assert client.get("/threads", headers=other).json() == []
