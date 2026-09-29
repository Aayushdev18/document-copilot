import re

import httpx
import structlog

from app.config import get_settings
from app.grounding.validator import Citation, GroundedAnswer, validate_grounding
from app.retrieval.retriever import Passage, contains_term, query_terms

log = structlog.get_logger()

REFUSAL = (
    "The corpus does not contain enough evidence to answer that. "
    "I only answer from the loaded 10-K filings, and none of them "
    "matched this question closely enough to cite."
)

MODEL_SYSTEM = (
    "You are Document Copilot, a research assistant for equity analysts. "
    "Answer in plain prose, in a few sentences, like a careful colleague. "
    "Use only the numbered passages. After each sentence, cite it as [1] or [2]. "
    "If the passages do not answer the question, reply with exactly: "
    "The corpus does not contain enough evidence to answer that. "
    "Do not add facts, numbers, or companies that are not in the passages. "
    "Do not give investment advice."
)


def clip_excerpt(text: str, limit: int = 680) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[:limit].rsplit(" ", 1)[0]


def _sentences(text: str) -> list[str]:
    collapsed = " ".join(text.split())
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z“\"])", collapsed)
    return [part.strip() for part in parts if len(part.split()) >= 6]


def _best_excerpt(passage: Passage, question: str) -> str:
    terms = query_terms(question)
    candidates = _sentences(passage.text) or [" ".join(passage.text.split())]
    ranked = sorted(
        candidates,
        key=lambda sentence: sum(contains_term(term, sentence.lower()) for term in terms),
        reverse=True,
    )
    source = " ".join(passage.text.split())
    chosen: list[str] = []
    for sentence in ranked:
        overlap = sum(contains_term(term, sentence.lower()) for term in terms)
        if terms and overlap == 0 and chosen:
            continue
        candidate = " ".join([*chosen, sentence])
        if chosen and (len(candidate) > 480 or candidate not in source):
            continue
        chosen.append(sentence)
        if len(chosen) == 2:
            break
    excerpt = " ".join(chosen)
    if len(excerpt) <= 700:
        return excerpt
    return clip_excerpt(excerpt, 480)


def _speak(excerpt: str, company: str) -> str:
    return excerpt.replace("The Company", company).replace("the Company", company)


def _paragraph(passage: Passage, excerpt: str, label: str) -> str:
    spoken = _speak(excerpt, passage.company)
    if spoken[-1:] not in ".!?":
        spoken += "."
    return f"{spoken} [{label}]"


def _citations(passages: list[Passage], excerpts: list[str]) -> list[Citation]:
    citations: list[Citation] = []
    for index, (passage, excerpt) in enumerate(zip(passages, excerpts, strict=True), start=1):
        citations.append(
            Citation(
                chunk_id=passage.chunk_id,
                label=str(index),
                excerpt=excerpt,
                ticker=passage.ticker,
                company=passage.company,
                form=passage.form,
                filing_date=passage.filing_date,
                section=passage.section,
                source_url=passage.source_url,
            )
        )
    return citations


def _lead(passages: list[Passage]) -> str:
    names = list(dict.fromkeys(passage.company for passage in passages))
    if len(names) == 1:
        return f"Here is what {names[0]}'s latest 10-K says."
    return "Here is what the loaded 10-K filings say."


def _local_answer(question: str, passages: list[Passage]) -> GroundedAnswer:
    excerpts = [_best_excerpt(passage, question) for passage in passages]
    citations = _citations(passages, excerpts)
    paragraphs = [
        _paragraph(passage, excerpt, citation.label)
        for passage, excerpt, citation in zip(passages, excerpts, citations, strict=True)
    ]
    answer = GroundedAnswer(
        answer=_lead(passages) + "\n\n" + "\n\n".join(paragraphs),
        citations=citations,
        insufficient_evidence=False,
    )
    validate_grounding(answer, passages)
    return answer


def _model_answer(
    question: str, passages: list[Passage], api_key: str, model: str
) -> GroundedAnswer:
    excerpts = [clip_excerpt(passage.text, 900) for passage in passages]
    citations = _citations(passages, excerpts)
    source_block = "\n\n".join(
        (
            f"[{citation.label}] {passage.company} ({passage.ticker}), "
            f"Form {passage.form} filed {passage.filing_date}, {passage.section}\n"
            f"{excerpt}"
        )
        for passage, excerpt, citation in zip(passages, excerpts, citations, strict=True)
    )
    log.info("openai_answer", model=model)
    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": MODEL_SYSTEM,
                },
                {
                    "role": "user",
                    "content": f"Question: {question}\n\nPassages:\n{source_block}",
                },
            ],
        },
        timeout=40,
    )
    response.raise_for_status()
    text = response.json()["choices"][0]["message"]["content"].strip()
    if "does not contain enough evidence" in text.lower():
        return GroundedAnswer(answer=REFUSAL, citations=[], insufficient_evidence=True)
    used = [citation for citation in citations if f"[{citation.label}]" in text]
    if not used:
        raise ValueError("The model answer did not cite a retrieved passage.")
    answer = GroundedAnswer(answer=text, citations=used, insufficient_evidence=False)
    validate_grounding(answer, passages)
    return answer


def compose_answer(passages: list[Passage], question: str = "") -> GroundedAnswer:
    if not passages:
        return GroundedAnswer(answer=REFUSAL, citations=[], insufficient_evidence=True)
    settings = get_settings()
    if settings.openai_api_key:
        return _model_answer(question, passages, settings.openai_api_key, settings.openai_model)
    return _local_answer(question, passages)


def stream_pieces(text: str, words_per_piece: int = 10) -> list[str]:
    words = text.split(" ")
    pieces: list[str] = []
    for start in range(0, len(words), words_per_piece):
        piece = " ".join(words[start : start + words_per_piece])
        if start + words_per_piece < len(words):
            piece += " "
        pieces.append(piece)
    return pieces
