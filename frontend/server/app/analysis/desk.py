import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.facts import company_financials, metric_rows
from app.database.models import DocumentChunk, SourceDocument

INDUSTRY = {
    "AAPL": "Technology · Consumer electronics",
    "MSFT": "Technology · Software",
    "NVDA": "Technology · Semiconductors",
    "AMZN": "Consumer · Internet retail and cloud",
    "GOOGL": "Communication · Internet platforms",
}

RISK_CATEGORIES = (
    ("Regulatory risk", ("regulat", "compliance", "litigation", "antitrust", "tariff")),
    ("Supply chain risk", ("supply chain", "supplier", "component", "manufactur")),
    ("Competition", ("compet", "market share")),
    ("Cybersecurity", ("cyber", "data breach", "privacy")),
    (
        "Macroeconomic risk",
        ("macroeconomic", "recession", "inflation", "interest rate", "currency"),
    ),
    ("Intellectual property", ("intellectual property", "patent", "infring")),
)

OVERVIEW_FOCUS = ("focused on", "designs", "develops", "manufactures", "operates", "provides")

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


def industry_label(ticker: str) -> str:
    return INDUSTRY.get(ticker.upper(), "Latest Form 10-K")


def risk_title(sentence: str) -> str:
    lowered = sentence.lower()
    for title, cues in RISK_CATEGORIES:
        if any(cue in lowered for cue in cues):
            return title
    return "Filing risk"


def _category_rank(title: str) -> int:
    for index, (name, _cues) in enumerate(RISK_CATEGORIES):
        if name == title:
            return index
    return len(RISK_CATEGORIES)


def risk_sentence(text: str) -> str:
    collapsed = " ".join(text.split())
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", collapsed) if part.strip()]
    chosen: tuple[int, str] | None = None
    fallback: str | None = None
    for part in parts:
        if _is_intro(part):
            continue
        title = risk_title(part)
        if title == "Filing risk":
            if fallback is None:
                fallback = part
            continue
        rank = _category_rank(title)
        if chosen is None or rank < chosen[0]:
            chosen = (rank, part)
    if chosen is not None:
        return chosen[1]
    if fallback is not None:
        return fallback
    return _sentence(text)


def _overview_score(sentence: str) -> int:
    lowered = sentence.lower()
    score = 0
    if any(cue in lowered for cue in OVERVIEW_FOCUS):
        score += 3
    if any(cue in lowered for cue in ("products", "services", "platform", "customers")):
        score += 1
    return score


def choose_overview(sentences: list[str]) -> str:
    ranked = [
        (_overview_score(sentence), sentence)
        for sentence in sentences
        if not _is_intro(sentence) and len(sentence) >= 60
    ]
    if not ranked:
        return "The loaded 10-K does not include an Item 1 business description."
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1]


def overview_sentence(session: Session, ticker: str) -> str:
    sentences = [_sentence(chunk.text) for chunk in section_chunks(session, ticker, "Item 1.")]
    return choose_overview(sentences)


def _item_sentences(text: str) -> list[str]:
    collapsed = " ".join(text.split())
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", collapsed) if part.strip()]


def segment_sentence(session: Session, ticker: str) -> str:
    ranked: list[tuple[int, str]] = []
    for chunk in section_chunks(session, ticker, "Item 1."):
        for sentence in _item_sentences(chunk.text):
            lowered = sentence.lower()
            if "segment" not in lowered or len(sentence) < 40:
                continue
            if any(word in lowered for word in ("competition", "competitor", "competitors")):
                continue
            score = 0
            if "reportable segment" in lowered or "segments consist" in lowered:
                score += 3
            if any(
                phrase in lowered
                for phrase in ("organized", "three segments", "two segments", "report our")
            ):
                score += 2
            ranked.append((score, sentence))
    if not ranked:
        return overview_sentence(session, ticker)
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1]


def segment_support(session: Session, ticker: str) -> tuple[str, DocumentChunk | None]:
    sentence = segment_sentence(session, ticker)
    collapsed = " ".join(sentence.split())
    for chunk in section_chunks(session, ticker, "Item 1."):
        if collapsed and collapsed in " ".join(chunk.text.split()):
            return sentence, chunk
    return sentence, None


def risk_items(session: Session, ticker: str, limit: int = 6) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    seen: list[str] = []
    for chunk in section_chunks(session, ticker, "1A"):
        sentence = risk_sentence(chunk.text)
        if _is_intro(sentence):
            continue
        title = risk_title(sentence)
        grouped.setdefault(title, [])
        if title not in seen:
            seen.append(title)
        if any(existing["text"] == sentence for existing in grouped[title]):
            continue
        grouped[title].append({"chunk": chunk, "text": sentence, "title": title})
    preferred = [title for title, _cues in RISK_CATEGORIES if grouped.get(title)]
    order = preferred + [title for title in seen if title not in preferred]
    items: list[dict] = []
    used: set[int] = set()
    for title in order:
        item = grouped[title][0]
        items.append(item)
        used.add(id(item["chunk"]))
    for title in order:
        for item in grouped[title][1:]:
            if id(item["chunk"]) in used:
                continue
            items.append(item)
            used.add(id(item["chunk"]))
    named_first: list[dict] = []
    seen_titles: set[str] = set()
    for item in items:
        if item["title"] == "Filing risk" or item["title"] in seen_titles:
            continue
        seen_titles.add(item["title"])
        named_first.append(item)
    if len(named_first) >= 3:
        return named_first[:limit]
    return items[:limit]


def best_chunks(chunks: list[DocumentChunk], count: int) -> list[DocumentChunk]:
    scored: list[tuple[int, int, DocumentChunk]] = []
    for index, chunk in enumerate(chunks):
        sentence = _sentence(chunk.text)
        if _is_intro(sentence) or len(sentence) < 60:
            continue
        scored.append((_overview_score(sentence), -index, chunk))
    scored.sort(reverse=True)
    return [chunk for _score, _index, chunk in scored[:count]]


def build_brief(session: Session, ticker: str) -> dict | None:
    company = company_financials(ticker)
    document = filing_for(session, ticker)
    if company is None and document is None:
        return None
    name = company["company"] if company else document.company
    business = best_chunks(section_chunks(session, ticker, "Item 1."), 2)
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
                "heading": "Business Performance",
                "body": overview,
                "chunks": overview_chunks,
            },
            {
                "id": "performance",
                "heading": "Financial Performance",
                "body": performance,
                "chunks": [],
            },
            {
                "id": "risks",
                "heading": "Key Risks",
                "body": risk_body,
                "chunks": [item["chunk"] for item in risks],
            },
            {
                "id": "changes",
                "heading": "Year-over-Year Changes",
                "body": "\n".join(changes) if changes else "No year-over-year change is loaded.",
                "chunks": [],
            },
            {
                "id": "commentary",
                "heading": "Management Commentary",
                "body": commentary,
                "chunks": commentary_chunks,
            },
            {
                "id": "takeaways",
                "heading": "Key Takeaways",
                "body": "\n".join(f"• {line}" for line in takeaways),
                "chunks": [],
            },
        ],
    }
