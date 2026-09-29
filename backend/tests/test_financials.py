from app.analysis.facts import change_label, company_financials, display_value, financial_preface


def test_apple_revenue_is_the_latest_annual_fact() -> None:
    company = company_financials("AAPL")
    assert company is not None
    revenue = next(metric for metric in company["metrics"] if metric["key"] == "revenue")
    assert revenue["current"]["value"] == 416161000000
    assert revenue["prior"]["value"] == 391035000000
    assert display_value(revenue["current"]["value"], "USD") == "$416.2B"
    assert change_label(revenue["current"]["value"], revenue["prior"]["value"]) == "+6.4%"


def test_revenue_comparison_cites_the_accession() -> None:
    text = financial_preface("AAPL", "Compare this year's revenue with last year.")
    assert "$416.2B" in text
    assert "0000320193-25-000079" in text
    assert "sec.gov" in text
