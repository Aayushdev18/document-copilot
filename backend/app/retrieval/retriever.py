import re
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database.models import DocumentChunk, SourceDocument
from app.retrieval.fusion import reciprocal_rank_fusion

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "what",
    "when",
    "where",
    "which",
    "how",
    "did",
    "does",
    "has",
    "have",
    "had",
    "was",
    "were",
    "are",
    "its",
    "their",
    "about",
    "into",
    "over",
    "than",
    "then",
    "across",
    "between",
    "any",
    "most",
    "describe",
    "describes",
    "described",
    "say",
    "says",
    "said",
    "discuss",
    "discussed",
    "tell",
    "company",
    "companies",
    "filing",
    "filings",
    "of",
    "is",
    "it",
    "to",
    "we",
    "our",
    "or",
    "be",
    "an",
    "as",
    "at",
    "by",
    "on",
    "in",
    "if",
    "not",
    "no",
    "do",
    "can",
    "may",
    "will",
    "would",
    "could",
    "should",
    "also",
    "such",
}

TICKER_ALIASES = {
    "apple": "AAPL",
    "aapl": "AAPL",
    "microsoft": "MSFT",
    "msft": "MSFT",
    "nvidia": "NVDA",
    "nvda": "NVDA",
    "amazon": "AMZN",
    "amzn": "AMZN",
    "alphabet": "GOOGL",
    "google": "GOOGL",
    "googl": "GOOGL",
}
COMPANY_TERMS = set(TICKER_ALIASES)


@dataclass(frozen=True)
class Passage:
    chunk_id: str
    ticker: str
    company: str
    form: str
    filing_date: str
    section: str
    source_url: str
    text: str


def query_terms(question: str) -> list[str]:
    terms: list[str] = []
    for token in re.findall(r"[a-z0-9]{2,}", question.lower()):
        if token in STOPWORDS or token in terms:
            continue
        terms.append(token)
    return terms[:16]


def _fts_query(terms: list[str]) -> str:
    return " OR ".join(f'"{term}"' for term in terms)


def _content_terms(terms: list[str]) -> list[str]:
    return [term for term in terms if term not in COMPANY_TERMS]


def contains_term(term: str, text_lower: str) -> bool:
    candidates = {term}
    if len(term) > 3 and term.endswith("s"):
        candidates.add(term[:-1])
    else:
        candidates.add(f"{term}s")
    return any(
        re.search(rf"\b{re.escape(candidate)}\b", text_lower) is not None
        for candidate in candidates
    )


def search_passages(session: Session, question: str, *, limit: int = 3) -> list[Passage]:
    terms = query_terms(question)
    if not terms:
        return []

    rows = session.execute(
        text(
            """
            SELECT chunk_id, bm25(chunk_fts) AS rank
            FROM chunk_fts
            WHERE chunk_fts MATCH :query
            ORDER BY rank
            LIMIT 24
            """
        ),
        {"query": _fts_query(terms)},
    ).all()

    if not rows:
        return []

    by_id = _load_passages(session, [row.chunk_id for row in rows])
    lexical_ids = [row.chunk_id for row in rows if row.chunk_id in by_id]
    content_terms = _content_terms(terms)

    def hits(chunk_id: str) -> int:
        if not content_terms:
            return 1
        text_lower = by_id[chunk_id].text.lower()
        return sum(contains_term(term, text_lower) for term in content_terms)

    needed = 2 if len(content_terms) >= 2 else 1
    eligible = [chunk_id for chunk_id in lexical_ids if hits(chunk_id) >= needed]
    named = {TICKER_ALIASES[term] for term in terms if term in TICKER_ALIASES}
    if named:
        focused = [chunk_id for chunk_id in eligible if by_id[chunk_id].ticker in named]
        if focused:
            eligible = focused
    if not eligible:
        return []

    best = max(hits(chunk_id) for chunk_id in eligible)
    strong_ids = [chunk_id for chunk_id in eligible if hits(chunk_id) >= best - 1]
    overlap_ids = sorted(strong_ids, key=lambda chunk_id: hits(chunk_id), reverse=True)
    lexical_ids = [chunk_id for chunk_id in lexical_ids if chunk_id in set(strong_ids)]
    fused = reciprocal_rank_fusion([lexical_ids, overlap_ids])
    chosen = [chunk_id for chunk_id, _score in fused if chunk_id in by_id]
    return [by_id[chunk_id] for chunk_id in chosen[:limit]]


def _load_passages(session: Session, chunk_ids: list[str]) -> dict[str, Passage]:
    if not chunk_ids:
        return {}
    rows = session.execute(
        select(DocumentChunk, SourceDocument)
        .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
        .where(DocumentChunk.id.in_(chunk_ids))
    ).all()
    return {
        chunk.id: Passage(
            chunk_id=chunk.id,
            ticker=document.ticker,
            company=document.company,
            form=document.form,
            filing_date=document.filing_date,
            section=chunk.section,
            source_url=document.source_url,
            text=chunk.text,
        )
        for chunk, document in rows
    }
