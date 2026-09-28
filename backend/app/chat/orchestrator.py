from app.grounding.validator import Citation, GroundedAnswer, validate_grounding
from app.retrieval.retriever import Passage


def clip_excerpt(text: str, limit: int = 680) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[:limit].rsplit(" ", 1)[0]


def compose_answer(passages: list[Passage]) -> GroundedAnswer:
    if not passages:
        return GroundedAnswer(
            answer=(
                "The corpus does not contain enough evidence to answer that. "
                "I only quote passages from the loaded 10-K filings, and none of them "
                "matched this question closely enough to cite."
            ),
            citations=[],
            insufficient_evidence=True,
        )

    citations: list[Citation] = []
    blocks: list[str] = []
    for index, passage in enumerate(passages, start=1):
        excerpt = clip_excerpt(passage.text)
        label = str(index)
        citations.append(
            Citation(
                chunk_id=passage.chunk_id,
                label=label,
                excerpt=excerpt,
                ticker=passage.ticker,
                company=passage.company,
                form=passage.form,
                filing_date=passage.filing_date,
                section=passage.section,
                source_url=passage.source_url,
            )
        )
        blocks.append(
            f"[{label}] {passage.company} ({passage.ticker}), Form {passage.form} "
            f"filed {passage.filing_date} — {passage.section}\n“{excerpt}”"
        )

    answer = GroundedAnswer(
        answer=(
            "These passages are quoted from the loaded 10-K filings. "
            "They are the evidence in the corpus, not an inference beyond it.\n\n"
            + "\n\n".join(blocks)
        ),
        citations=citations,
        insufficient_evidence=False,
    )
    validate_grounding(answer, passages)
    return answer


def stream_pieces(text: str, words_per_piece: int = 10) -> list[str]:
    words = text.split(" ")
    pieces: list[str] = []
    for start in range(0, len(words), words_per_piece):
        piece = " ".join(words[start : start + words_per_piece])
        if start + words_per_piece < len(words):
            piece += " "
        pieces.append(piece)
    return pieces
