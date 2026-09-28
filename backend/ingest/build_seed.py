"""Download the latest 10-K for each sample company and write a local seed corpus.

Stdlib only. Run from the repo root:

    python backend/ingest/build_seed.py
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

USER_AGENT = "Document Copilot local-setup research@driftwood.example"
TICKERS = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "NVDA": "0001045810",
    "AMZN": "0001018724",
    "GOOGL": "0001652044",
}
MAX_CHUNKS = 36
MIN_CHARS = 280
MAX_CHARS = 1100
OUTPUT = Path(__file__).resolve().parents[1] / "app" / "corpus" / "seed.json"

SKIP_TAGS = {"script", "style", "head", "noscript", "svg"}
COMPANY_NAMES = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
}
PREFERRED_SECTIONS = (
    "Item 1. Business",
    "Item 1A. Risk Factors",
    "Item 7. Management's Discussion and Analysis",
)
SECTION_PATTERNS = (
    ("1A", "Item 1A. Risk Factors"),
    ("1B", "Item 1B. Unresolved Staff Comments"),
    ("1C", "Item 1C. Cybersecurity"),
    ("7A", "Item 7A. Quantitative and Qualitative Disclosures"),
    ("7", "Item 7. Management's Discussion and Analysis"),
    ("1", "Item 1. Business"),
    ("8", "Item 8. Financial Statements"),
)
BLOCK_TAGS = {"p", "div", "h1", "h2", "h3", "h4", "tr", "li", "br", "section"}


class FilingTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = tag.lower()
        if name in SKIP_TAGS or name == "ix:header" or name.endswith(":hidden"):
            self.skip_depth += 1
            return
        if name in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        name = tag.lower()
        if name in SKIP_TAGS or name == "ix:header" or name.endswith(":hidden"):
            if self.skip_depth:
                self.skip_depth -= 1
            return
        if name in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth or not data:
            return
        self.parts.append(data)


def get_bytes(url: str, accept: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    with urlopen(request, timeout=90) as response:
        return response.read()


def get_json(url: str) -> dict:
    return json.loads(get_bytes(url, "application/json").decode("utf-8"))


def latest_10k(cik: str) -> dict[str, str]:
    submission = get_json(f"https://data.sec.gov/submissions/CIK{cik}.json")
    recent = submission["filings"]["recent"]
    for form, accession, document, filing_date, report_date in zip(
        recent["form"],
        recent["accessionNumber"],
        recent["primaryDocument"],
        recent["filingDate"],
        recent["reportDate"],
        strict=True,
    ):
        if form == "10-K":
            accession_path = accession.replace("-", "")
            source_url = (
                "https://www.sec.gov/Archives/edgar/data/"
                f"{int(cik)}/{accession_path}/{document}"
            )
            return {
                "company": (
                    submission["name"].title()
                    if submission["name"].isupper()
                    else submission["name"]
                ),
                "form": form,
                "accession_number": accession,
                "filing_date": filing_date,
                "report_date": report_date,
                "year": (report_date or filing_date)[:4],
                "source_url": source_url,
            }
    raise RuntimeError(f"No 10-K found for CIK {cik}")


def html_to_text(html: str) -> str:
    parser = FilingTextParser()
    parser.feed(html)
    text = "".join(parser.parts)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text.strip()


def letter_ratio(text: str) -> float:
    letters = sum(character.isalpha() for character in text)
    return letters / max(len(text), 1)


def looks_like_prose(text: str) -> bool:
    lowered = text.lower()
    if letter_ratio(text) < 0.62:
        return False
    if lowered.count("us-gaap") or lowered.count("xbrl") or "http://" in lowered:
        return False
    words = text.split()
    if len(words) < 45:
        return False
    unique = len({word.lower() for word in words})
    return unique / len(words) > 0.35


def detect_section(paragraph: str) -> str | None:
    compact = re.sub(r"\s+", " ", paragraph).strip().lower()
    head = compact[:120]
    if len(head) > 90 and not head.startswith("item "):
        return None
    for key, label in SECTION_PATTERNS:
        if re.search(rf"\bitem\s+{key.lower()}\b", head):
            return label
    return None


def is_boilerplate(text: str) -> bool:
    lowered = text.lower()
    needles = (
        "indicate by check mark",
        "securities exchange act",
        "table of contents",
        "commission file number",
        "exact name of registrant",
        "large accelerated filer",
        "aggregate market value",
        "emerging growth company",
    )
    return any(needle in lowered for needle in needles) or "☐" in text or "☒" in text


def chunk_filing(text: str) -> list[dict[str, str]]:
    paragraphs = [re.sub(r"\s+", " ", part).strip() for part in re.split(r"\n+", text)]
    paragraphs = [part for part in paragraphs if part]
    grouped: dict[str, list[str]] = {section: [] for section in PREFERRED_SECTIONS}
    section = "Filing text"
    seen: set[str] = set()

    for paragraph in paragraphs:
        heading = detect_section(paragraph)
        if heading:
            section = heading
            continue
        if section not in grouped or is_boilerplate(paragraph) or not looks_like_prose(paragraph):
            continue
        body = paragraph
        if len(body) > MAX_CHARS:
            body = body[:MAX_CHARS].rsplit(" ", 1)[0]
        if len(body) < MIN_CHARS:
            continue
        key = body[:180].lower()
        if key in seen:
            continue
        seen.add(key)
        grouped[section].append(body)

    chunks: list[dict[str, str]] = []
    per_section = max(MAX_CHUNKS // len(PREFERRED_SECTIONS), 1)
    for name in PREFERRED_SECTIONS:
        for body in grouped[name][:per_section]:
            chunks.append({"section": name, "text": body})
    return chunks[:MAX_CHUNKS]


def build() -> None:
    documents = []
    for ticker, cik in TICKERS.items():
        print(f"Fetching {ticker} metadata...")
        filing = latest_10k(cik)
        print(f"Downloading {ticker} {filing['source_url']}")
        raw = get_bytes(filing["source_url"], "text/html,application/xhtml+xml")
        html = raw.decode("utf-8", errors="replace")
        chunks = chunk_filing(html_to_text(html))
        print(f"  {len(chunks)} passages")
        filing["company"] = COMPANY_NAMES[ticker]
        documents.append({"ticker": ticker, "cik": cik, **filing, "chunks": chunks})

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({"documents": documents}, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    build()
