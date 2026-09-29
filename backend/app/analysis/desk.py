import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.facts import company_financials, metric_rows
from app.database.models import DocumentChunk, SourceDocument

INTRO_MARKERS = (
    "following summarizes",
    "following risk factors",
    "should be read in conjunction",
    "should be considered in addition",
    "not exhaustive",
    "not a complete statement",
    "complete statement of all potential",
)


def _sentence(text: str) -> str:
    collapsed = " ".join(text.split())
    parts = re.split(r"(?<=[.!?])\s+", collapsed)
    return parts[0] if parts else collapsed


def _is_intro(sentence: str) -> bool:
    lowered = sentence.lower()
    return any(marker in lowered for marker in INTRO_MARKERS)


def filing_for(session: Session, ticker: str) -> SourceDocument | None:
    return session.scalar(
        select(SourceDocument)
        .where(SourceDocument.ticker == ticker.upper())
        .order_by(SourceDocument.filing_date.desc())
    )


def section_chunks(session: Session, ticker: str, section_needle: str) -> list[DocumentChunk]:
    rows = session.execute(
        select(DocumentChunk, SourceDocument)
        .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
        .where(SourceDocument.ticker == ticker.upper())
        .order_by(DocumentChunk.chunk_index)
    ).all()
    return [chunk for chunk, _document in rows if section_needle in chunk.section]


def risk_items(session: Session, ticker: str, limit: int = 6) -> list[dict]:
    items = []
    for chunk in section_chunks(session, ticker, "1A"):
        sentence = _sentence(chunk.text)
        if _is_intro(sentence):
            continue
        items.append({"chunk": chunk, "text": sentence})
        if len(items) == limit:
            break
    return items


def build_brief(session: Session, ticker: str) -> dict | None:
    company = company_financials(ticker)
    document = filing_for(session, ticker)
    if company is None and document is None:
        return None
    name = company["company"] if company else document.company
    business = section_chunks(session, ticker, "Item 1.")
    narrative = section_chunks(session, ticker, "Item 7")
    risks = risk_items(session, ticker)
    rows = metric_rows(ticker)

    def passage_block(chunks: list[DocumentChunk], count: int) -> tuple[str, list[DocumentChunk]]:
        chosen = chunks[:count]
        if not chosen:
            return "The loaded 10-K does not include a passage for this section.", []
        lines = []
        for index, chunk in enumerate(chosen, start=1):
            lines.append(f"{_sentence(chunk.text)} [{index}]")
        return "\n\n".join(lines), chosen

    overview, overview_chunks = passage_block(business, 2)
    commentary, commentary_chunks = passage_block(narrative, 2)
    performance_lines = []
    for row in rows:
        current = row["current"]
        prior = row["prior"]
        performance_lines.append(
            f"{row['label']}: {row['currentDisplay']} in {current['year']} "
            f"versus {row['priorDisplay']} in {prior['year']} ({row['change']}). "
            f"us-gaap:{row['concept']}, accession {current['accession']}."
        )
    performance = (
        "\n".join(performance_lines)
        if performance_lines
        else "No XBRL annual facts are loaded for this company."
    )
    risk_lines = [f"{item['text']} [{index}]" for index, item in enumerate(risks, start=1)]
    risk_body = (
        "\n\n".join(risk_lines)
        if risk_lines
        else "Item 1A is not in the loaded passages for this company."
    )
    changes = [
        f"{row['label']} {row['change']} from {row['prior']['year']} to {row['current']['year']}."
        for row in rows
        if row["change"] not in {"n/a", "0.0%"}
    ]
    takeaways = []
    if rows:
        revenue = next((row for row in rows if row["key"] == "revenue"), rows[0])
        takeaways.append(
            f"{name} reported {revenue['label'].lower()} of {revenue['currentDisplay']} "
            f"for {revenue['current']['year']}, {revenue['change']} versus "
            f"{revenue['prior']['year']}."
        )
    if risks:
        takeaways.append(f"A leading risk in Item 1A: {risks[0]['text']}")
    if not takeaways:
        takeaways.append("The loaded filing does not support a longer takeaway.")

    return {
        "ticker": ticker.upper(),
        "company": name,
        "sections": [
            {
                "id": "overview",
                "heading": "Business overview",
                "body": overview,
                "chunks": overview_chunks,
            },
            {
                "id": "performance",
                "heading": "Financial performance",
                "body": performance,
                "chunks": [],
            },
            {
                "id": "risks",
                "heading": "Key risks",
                "body": risk_body,
                "chunks": [item["chunk"] for item in risks],
            },
            {
                "id": "changes",
                "heading": "Major changes",
                "body": "\n".join(changes) if changes else "No year-over-year change is loaded.",
                "chunks": [],
            },
            {
                "id": "commentary",
                "heading": "Management commentary",
                "body": commentary,
                "chunks": commentary_chunks,
            },
            {
                "id": "takeaways",
                "heading": "Important takeaways",
                "body": "\n".join(f"• {line}" for line in takeaways),
                "chunks": [],
            },
        ],
    }
