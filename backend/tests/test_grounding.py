import pytest

from app.chat.orchestrator import compose_answer
from app.grounding.validator import Citation, GroundedAnswer, GroundingError, validate_grounding
from app.retrieval.retriever import Passage


def passage() -> Passage:
    return Passage(
        chunk_id="chunk-1",
        ticker="AAPL",
        company="Apple Inc.",
        form="10-K",
        filing_date="2025-10-31",
        section="Item 1A. Risk Factors",
        source_url="https://www.sec.gov/example",
        text="The Company depends on component suppliers for custom parts.",
    )


def test_compose_refuses_when_nothing_was_retrieved() -> None:
    answer = compose_answer([])
    assert answer.insufficient_evidence
    assert answer.citations == []
    assert "does not contain enough evidence" in answer.answer


def test_compose_quotes_only_retrieved_text() -> None:
    source = passage()
    answer = compose_answer([source])
    assert answer.insufficient_evidence is False
    assert answer.citations[0].excerpt in source.text
    assert "Apple Inc." in answer.answer
    validate_grounding(answer, [source])


def test_validator_rejects_a_citation_that_was_not_retrieved() -> None:
    answer = GroundedAnswer(
        answer="Invented.",
        insufficient_evidence=False,
        citations=[
            Citation(
                chunk_id="missing",
                label="1",
                excerpt="The Company depends on component suppliers for custom parts.",
                ticker="AAPL",
                company="Apple Inc.",
                form="10-K",
                filing_date="2025-10-31",
                section="Item 1A. Risk Factors",
                source_url="https://www.sec.gov/example",
            )
        ],
    )
    with pytest.raises(GroundingError):
        validate_grounding(answer, [passage()])


def test_validator_rejects_an_excerpt_that_is_not_in_the_passage() -> None:
    source = passage()
    answer = compose_answer([source])
    forged = answer.model_copy(
        update={
            "citations": [
                answer.citations[0].model_copy(update={"excerpt": "Revenue grew 40 percent."})
            ]
        }
    )
    with pytest.raises(GroundingError):
        validate_grounding(forged, [source])
