from app.analysis.desk import choose_overview, risk_title
from app.analysis.facts import change_label, company_financials, display_value, financial_preface


def test_apple_revenue_is_the_latest_annual_fact() -> None:
    company = company_financials("AAPL")
    assert company is not None
    revenue = next(metric for metric in company["metrics"] if metric["key"] == "revenue")
    assert revenue["current"]["value"] == 416161000000
    assert revenue["prior"]["value"] == 391035000000
    assert display_value(revenue["current"]["value"], "USD") == "$416.2B"
    assert change_label(revenue["current"]["value"], revenue["prior"]["value"]) == "+6.4%"


def test_profitability_and_change_questions_use_the_annual_facts() -> None:
    profit = financial_preface("AAPL", "How did profitability change?")
    assert "Net income" in profit
    assert "Operating income" in profit
    changed = financial_preface("AAPL", "What changed from 2024 to 2025?")
    assert "$416.2B" in changed
    assert "Net income" in changed


def test_overview_prefers_the_business_description() -> None:
    chosen = choose_overview(
        [
            "Gamers choose NVIDIA GPUs because of the growing population of live streamers.",
            "The Company designs and develops nearly the entire solution for its products, "
            "including the hardware and related services.",
        ]
    )
    assert chosen.startswith("The Company designs and develops")


def test_risk_titles_follow_the_sentence() -> None:
    regulatory = "New tariffs and regulatory changes could limit sales."
    supply = "The Company depends on suppliers for custom components."
    competition = "Competition for customers remains intense."
    assert risk_title(regulatory) == "Regulatory risk"
    assert risk_title(supply) == "Supply chain risk"
    assert risk_title(competition) == "Competition"


def test_revenue_comparison_cites_the_accession() -> None:
    text = financial_preface("AAPL", "Compare this year's revenue with last year.")
    assert "$416.2B" in text
    assert "0000320193-25-000079" in text
    assert "sec.gov" in text
