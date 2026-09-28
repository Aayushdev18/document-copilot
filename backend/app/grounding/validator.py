from pydantic import BaseModel, ConfigDict, Field

from app.retrieval.retriever import Passage


class GroundingError(Exception):
    pass


class Citation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    chunk_id: str = Field(serialization_alias="chunkId")
    label: str
    excerpt: str
    ticker: str
    company: str
    form: str
    filing_date: str = Field(serialization_alias="filingDate")
    section: str
    source_url: str = Field(serialization_alias="sourceUrl")


class GroundedAnswer(BaseModel):
    answer: str
    citations: list[Citation]
    insufficient_evidence: bool = Field(serialization_alias="insufficientEvidence")


def normalize_text(value: str) -> str:
    return " ".join(value.split())


def validate_grounding(answer: GroundedAnswer, passages: list[Passage]) -> None:
    by_id = {passage.chunk_id: passage for passage in passages}
    if answer.insufficient_evidence:
        if answer.citations:
            raise GroundingError("An insufficient-evidence answer cannot include citations.")
        return
    if not answer.citations:
        raise GroundingError("A grounded answer needs at least one citation.")
    seen: set[str] = set()
    for citation in answer.citations:
        if citation.chunk_id in seen:
            raise GroundingError("Duplicate citation.")
        seen.add(citation.chunk_id)
        passage = by_id.get(citation.chunk_id)
        if passage is None:
            raise GroundingError("Citation does not map to a retrieved passage.")
        excerpt = normalize_text(citation.excerpt)
        source = normalize_text(passage.text)
        if not excerpt or excerpt not in source:
            raise GroundingError("Citation excerpt is not contained in the retrieved passage.")
        if citation.ticker != passage.ticker or citation.source_url != passage.source_url:
            raise GroundingError("Citation metadata does not match the retrieved filing.")
