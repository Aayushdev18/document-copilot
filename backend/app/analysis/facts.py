import json
from functools import lru_cache
from pathlib import Path

FACTS_PATH = Path(__file__).resolve().parents[1] / "corpus" / "financials.json"

METRIC_CUES = (
    ("revenue", ("revenue", "sales", "top line")),
    ("net_income", ("net income", "net earnings")),
    ("operating_income", ("operating income", "operating profit")),
    ("eps", ("eps", "earnings per share", "diluted eps")),
    ("cash", ("cash",)),
    ("debt", ("debt", "borrowing")),
)


@lru_cache
def load_financials() -> dict[str, dict]:
    payload = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    return {company["ticker"]: company for company in payload["companies"]}


def company_financials(ticker: str) -> dict | None:
    return load_financials().get(ticker.upper())


def display_value(value: float, unit: str) -> str:
    if unit == "USD/shares":
        return f"${value:.2f}"
    sign = "-" if value < 0 else ""
    amount = abs(value)
    if amount >= 1_000_000_000:
        return f"{sign}${amount / 1_000_000_000:.1f}B"
    if amount >= 1_000_000:
        return f"{sign}${amount / 1_000_000:.1f}M"
    return f"{sign}${amount:,.0f}"


def change_label(current: float, prior: float) -> str:
    if prior == 0:
        return "n/a"
    pct = (current - prior) / abs(prior) * 100
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.1f}%"


def metric_rows(ticker: str) -> list[dict]:
    company = company_financials(ticker)
    if company is None:
        return []
    rows = []
    for metric in company["metrics"]:
        current = metric["current"]
        prior = metric["prior"]
        rows.append(
            {
                **metric,
                "currentDisplay": display_value(current["value"], metric["unit"]),
                "priorDisplay": display_value(prior["value"], metric["unit"]),
                "change": change_label(current["value"], prior["value"]),
            }
        )
    return rows


def _selected_keys(question: str, available: list[str]) -> list[str]:
    lowered = question.lower()
    chosen = [
        key for key, cues in METRIC_CUES if any(cue in lowered for cue in cues) and key in available
    ]
    broad = any(
        word in lowered
        for word in ("compare", "year over year", "year-over-year", "last year", "yoy")
    )
    if broad and not chosen:
        return available
    return chosen


def financial_preface(ticker: str, question: str) -> str:
    company = company_financials(ticker)
    if company is None:
        return ""
    rows = metric_rows(ticker)
    by_key = {row["key"]: row for row in rows}
    keys = _selected_keys(question, list(by_key))
    if not keys:
        return ""
    lines = [
        (
            f"{company['company']} reports these figures in its latest Form 10-K "
            "(Item 8, SEC XBRL facts):"
        )
    ]
    for key in keys:
        row = by_key[key]
        current = row["current"]
        prior = row["prior"]
        lines.append(
            f"{row['label']} was {row['currentDisplay']} for the year ended {current['end']}, "
            f"compared with {row['priorDisplay']} for the year ended {prior['end']} "
            f"({row['change']}). "
            f"Source: us-gaap:{row['concept']}, accession {current['accession']}, "
            f"filed {current['filed']}. {current['sourceUrl']}"
        )
    return "\n\n".join(lines)
