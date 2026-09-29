from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.analysis.desk import (
    build_brief,
    filing_for,
    industry_label,
    overview_sentence,
    risk_items,
)
from app.analysis.facts import company_financials, metric_rows
from app.auth.dependencies import get_current_user
from app.database.models import DocumentChunk, User
from app.database.session import get_db

router = APIRouter(tags=["desk"])


class FactYear(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    year: str
    end: str
    value: float
    display: str
    accession: str
    filed: str
    source_url: str = Field(serialization_alias="sourceUrl")


class MetricOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    key: str
    label: str
    concept: str
    current: FactYear
    prior: FactYear
    change: str


class DeskCitation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    chunk_id: str = Field(serialization_alias="chunkId")
    label: str
    excerpt: str
    passage: str
    ticker: str
    company: str
    form: str
    filing_date: str = Field(serialization_alias="filingDate")
    section: str
    source_url: str = Field(serialization_alias="sourceUrl")
    paragraph: int
    locator: str


class RiskOut(BaseModel):
    title: str
    text: str
    citation: DeskCitation


class SnapshotOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ticker: str
    company: str
    form: str
    filing_date: str = Field(serialization_alias="filingDate")
    source_url: str = Field(serialization_alias="sourceUrl")
    facts_url: str = Field(serialization_alias="factsUrl")
    industry: str
    overview: str
    metrics: list[MetricOut]
    risks: list[RiskOut]


class BriefSection(BaseModel):
    id: str
    heading: str
    body: str
    citations: list[DeskCitation]


class BriefOut(BaseModel):
    ticker: str
    company: str
    sections: list[BriefSection]


def _require_company(ticker: str) -> dict:
    company = company_financials(ticker)
    if company is None:
        raise HTTPException(status_code=404, detail="That company is not on the desk.")
    return company


def _citation(chunk: DocumentChunk, label: str, excerpt: str) -> DeskCitation:
    document = chunk.document
    paragraph = chunk.chunk_index + 1
    return DeskCitation(
        chunk_id=chunk.id,
        label=label,
        excerpt=excerpt,
        passage=chunk.text,
        ticker=document.ticker,
        company=document.company,
        form=document.form,
        filing_date=document.filing_date,
        section=chunk.section,
        source_url=document.source_url,
        paragraph=paragraph,
        locator=f"{chunk.section} · paragraph {paragraph}",
    )


def _metric_out(row: dict) -> MetricOut:
    def year(point: dict, display: str) -> FactYear:
        return FactYear(
            year=point["year"],
            end=point["end"],
            value=point["value"],
            display=display,
            accession=point["accession"],
            filed=point["filed"],
            source_url=point["sourceUrl"],
        )

    return MetricOut(
        key=row["key"],
        label=row["label"],
        concept=row["concept"],
        current=year(row["current"], row["currentDisplay"]),
        prior=year(row["prior"], row["priorDisplay"]),
        change=row["change"],
    )


@router.get("/companies/{ticker}", response_model=SnapshotOut)
async def company_snapshot(
    ticker: str,
    _user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> SnapshotOut:
    company = _require_company(ticker)
    document = filing_for(session, ticker)
    risks = [
        RiskOut(
            title=item["title"],
            text=item["text"],
            citation=_citation(item["chunk"], str(index), item["text"]),
        )
        for index, item in enumerate(risk_items(session, ticker), start=1)
    ]
    return SnapshotOut(
        ticker=company["ticker"],
        company=company["company"],
        form="10-K",
        filing_date=(
            document.filing_date if document else company["metrics"][0]["current"]["filed"]
        ),
        source_url=(
            document.source_url if document else company["metrics"][0]["current"]["sourceUrl"]
        ),
        facts_url=company["factsUrl"],
        industry=industry_label(company["ticker"]),
        overview=overview_sentence(session, company["ticker"]),
        metrics=[_metric_out(row) for row in metric_rows(ticker)],
        risks=risks,
    )


@router.post("/companies/{ticker}/brief", response_model=BriefOut)
async def company_brief(
    ticker: str,
    _user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> BriefOut:
    _require_company(ticker)
    brief = build_brief(session, ticker)
    if brief is None:
        raise HTTPException(status_code=404, detail="That company is not on the desk.")
    sections = []
    for section in brief["sections"]:
        sections.append(
            BriefSection(
                id=section["id"],
                heading=section["heading"],
                body=section["body"],
                citations=[
                    _citation(chunk, str(index), chunk.text[:280])
                    for index, chunk in enumerate(section["chunks"], start=1)
                ],
            )
        )
    return BriefOut(ticker=brief["ticker"], company=brief["company"], sections=sections)
