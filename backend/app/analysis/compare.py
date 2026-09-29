import re

import httpx
from sqlalchemy.orm import Session

from app.analysis.desk import risk_items, section_chunks, segment_sentence
from app.analysis.facts import company_financials, metric_rows
from app.config import get_settings

MODEL_SYSTEM = (
    "You write a short comparison for an equity analyst. "
    "Use only the numbered sources. Cite factual sentences as [n]. "
    "Do not add companies, figures, or risks that are not in the sources. "
    "Do not give investment advice. Write three short paragraphs: "
    "financial performance, major risks, and business segments."
)


def _short_name(company: str) -> str:
    return (
        company.replace("Amazon.com, Inc.", "Amazon")
        .replace(", Inc.", "")
        .replace(" Corporation", "")
        .replace(" Inc.", "")
    )


def _figures(text: str) -> set[str]:
    found = re.findall(r"\$\d[\d,.]*[BMK]?|[+-]?\d+\.\d+%", text)
    return {item.lstrip("+") for item in found}


def _segment_chunk(session: Session, ticker: str):
    sentence = segment_sentence(session, ticker)
    collapsed_sentence = " ".join(sentence.split())
    for chunk in section_chunks(session, ticker, "Item 1."):
        if collapsed_sentence in " ".join(chunk.text.split()):
            return chunk, sentence
    return None, sentence


def _source(
    *,
    chunk_id: str,
    label: str,
    excerpt: str,
    passage: str,
    ticker: str,
    company: str,
    filing_date: str,
    section: str,
    source_url: str,
    locator: str,
    paragraph: int = 0,
) -> dict:
    return {
        "chunk_id": chunk_id,
        "label": label,
        "excerpt": excerpt[:280],
        "passage": passage,
        "ticker": ticker,
        "company": company,
        "form": "10-K",
        "filing_date": filing_date,
        "section": section,
        "source_url": source_url,
        "paragraph": paragraph,
        "locator": locator,
    }


def _model_narrative(packet: str, api_key: str, model: str) -> str:
    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": MODEL_SYSTEM},
                {"role": "user", "content": packet},
            ],
        },
        timeout=40,
    )
    response.raise_for_status()
    text = response.json()["choices"][0]["message"]["content"].strip()
    extra = _figures(text) - _figures(packet)
    if extra:
        raise ValueError("The comparison introduced a figure that is not in the filings.")
    if not re.search(r"\[\d+\]", text):
        raise ValueError("The comparison did not cite a source.")
    return text


def build_comparison(session: Session, tickers: list[str]) -> dict:
    chosen = list(dict.fromkeys(ticker.upper() for ticker in tickers))
    names: list[str] = []
    financial_rows: list[tuple[str, dict]] = []
    risk_rows: list[tuple[str, list[tuple[str, dict]]]] = []
    segment_rows: list[tuple[str, str, dict | None]] = []

    for ticker in chosen:
        company = company_financials(ticker)
        if company is None:
            continue
        rows = {row["key"]: row for row in metric_rows(ticker)}
        revenue = rows["revenue"]
        net = rows["net_income"]
        name = company["company"]
        names.append(_short_name(name))
        current = revenue["current"]
        fact = (
            f"{name} reported revenue of {revenue['currentDisplay']} "
            f"in its {current['year']} Form 10-K, {revenue['change']} versus "
            f"{revenue['prior']['year']}, and net income of {net['currentDisplay']} "
            f"({net['change']}). Accession {current['accession']}, filed {current['filed']}."
        )
        financial_rows.append(
            (
                fact,
                _source(
                    chunk_id=f"xbrl-{ticker}-revenue",
                    label="",
                    excerpt=fact,
                    passage=fact,
                    ticker=ticker,
                    company=name,
                    filing_date=current["filed"],
                    section="Item 8. Financial Statements",
                    source_url=current["sourceUrl"],
                    locator="Item 8 · SEC XBRL",
                ),
            )
        )
        notes: list[tuple[str, dict]] = []
        for item in risk_items(session, ticker, limit=2):
            chunk = item["chunk"]
            document = chunk.document
            paragraph = chunk.chunk_index + 1
            notes.append(
                (
                    f"{item['title']}: {item['text']}",
                    _source(
                        chunk_id=chunk.id,
                        label="",
                        excerpt=item["text"],
                        passage=chunk.text,
                        ticker=document.ticker,
                        company=document.company,
                        filing_date=document.filing_date,
                        section=chunk.section,
                        source_url=document.source_url,
                        locator=f"{chunk.section} · paragraph {paragraph}",
                        paragraph=paragraph,
                    ),
                )
            )
        risk_rows.append((name, notes))
        chunk, sentence = _segment_chunk(session, ticker)
        segment_source = None
        if chunk is not None:
            document = chunk.document
            paragraph = chunk.chunk_index + 1
            segment_source = _source(
                chunk_id=chunk.id,
                label="",
                excerpt=sentence,
                passage=chunk.text,
                ticker=document.ticker,
                company=document.company,
                filing_date=document.filing_date,
                section=chunk.section,
                source_url=document.source_url,
                locator=f"{chunk.section} · paragraph {paragraph}",
                paragraph=paragraph,
            )
        segment_rows.append((name, sentence, segment_source))

    sources: list[dict] = []
    label = 1

    def stamp(text: str, source: dict | None) -> str:
        nonlocal label
        if source is None:
            return text
        source["label"] = str(label)
        sources.append(source)
        marked = f"{text} [{label}]"
        label += 1
        return marked

    financial_bits = [stamp(text, source) for text, source in financial_rows]
    risk_bits = []
    for name, notes in risk_rows:
        if not notes:
            risk_bits.append(f"{name}: Item 1A is not in the loaded passages.")
            continue
        risk_bits.append(f"{name}: " + " ".join(stamp(text, source) for text, source in notes))
    segment_bits = []
    for name, sentence, source in segment_rows:
        segment_bits.append(f"{name}: {stamp(sentence, source)}")

    blocks: list[str] = []
    year_note = (
        "Each figure is that company's latest annual 10-K fact, "
        "so the fiscal years are not the same calendar year."
    )
    blocks.append(" ".join(financial_bits) + " " + year_note)
    blocks.append("Major risks. " + " ".join(risk_bits))
    blocks.append("Business segments. " + " ".join(segment_bits))
    packet_lines = []
    for source in sources:
        packet_lines.append(
            f"[{source['label']}] {source['company']} {source['form']} {source['locator']}\n"
            f"{source['passage']}"
        )
    packet = "\n\n".join(packet_lines)
    local = "\n\n".join(blocks)
    settings = get_settings()
    if settings.openai_api_key:
        narrative = _model_narrative(packet, settings.openai_api_key, settings.openai_model)
    else:
        narrative = local
    headline = " vs ".join(names) if len(names) == 2 else ", ".join(names)
    return {"headline": headline, "narrative": narrative, "sources": sources}
