import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.analysis.facts import financial_preface, supporting_passages
from app.auth.dependencies import get_current_user
from app.chat.orchestrator import compose_answer, stream_pieces
from app.database.models import (
    ChatMessage,
    ChatThread,
    DocumentChunk,
    MessageCitation,
    SourceDocument,
    User,
)
from app.database.session import get_db, open_session
from app.retrieval.retriever import search_passages

router = APIRouter(tags=["chat"])


class ThreadSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    updated_at: datetime = Field(serialization_alias="updatedAt")


class CitationOut(BaseModel):
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
    paragraph: int | None = None
    locator: str | None = None


class MessageOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    role: str
    content: str
    created_at: datetime = Field(serialization_alias="createdAt")
    citations: list[CitationOut]


class ThreadDetail(BaseModel):
    thread: ThreadSummary
    messages: list[MessageOut]


class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str = Field(min_length=1, max_length=4000)
    thread_id: str | None = Field(default=None, alias="threadId")
    ticker: str | None = None


class FilingOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ticker: str
    company: str
    form: str
    filing_date: str = Field(serialization_alias="filingDate")
    source_url: str = Field(serialization_alias="sourceUrl")
    passage_count: int = Field(serialization_alias="passageCount")


class CorpusOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    document_count: int = Field(serialization_alias="documentCount")
    passage_count: int = Field(serialization_alias="passageCount")
    filings: list[FilingOut]


def _owned_thread(session: Session, user: User, thread_id: str) -> ChatThread:
    thread = session.get(ChatThread, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="That conversation does not exist.")
    if thread.user_id != user.id:
        raise HTTPException(status_code=403, detail="That conversation belongs to another analyst.")
    return thread


def _title_from(message: str) -> str:
    compact = " ".join(message.split())
    if len(compact) <= 72:
        return compact
    return compact[:72].rsplit(" ", 1)[0]


def _citation_out(citation: MessageCitation) -> CitationOut:
    chunk = citation.chunk
    document = chunk.document
    return CitationOut(
        chunk_id=chunk.id,
        label=citation.label,
        excerpt=citation.excerpt,
        passage=chunk.text,
        ticker=document.ticker,
        company=document.company,
        form=document.form,
        filing_date=document.filing_date,
        section=chunk.section,
        source_url=document.source_url,
        paragraph=chunk.chunk_index + 1,
        locator=f"{chunk.section} · paragraph {chunk.chunk_index + 1}",
    )


def _message_out(message: ChatMessage) -> MessageOut:
    ordered = sorted(message.citations, key=lambda item: item.label)
    return MessageOut(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
        citations=[_citation_out(citation) for citation in ordered],
    )


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


@router.get("/corpus", response_model=CorpusOut)
async def read_corpus(
    _user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CorpusOut:
    documents = session.scalars(select(SourceDocument).order_by(SourceDocument.ticker)).all()
    filings: list[FilingOut] = []
    passage_count = 0
    for document in documents:
        count = session.scalar(
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.document_id == document.id)
        )
        passage_count += count or 0
        filings.append(
            FilingOut(
                ticker=document.ticker,
                company=document.company,
                form=document.form,
                filing_date=document.filing_date,
                source_url=document.source_url,
                passage_count=count or 0,
            )
        )
    return CorpusOut(
        document_count=len(documents),
        passage_count=passage_count,
        filings=filings,
    )


@router.get("/threads", response_model=list[ThreadSummary])
async def list_threads(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[ThreadSummary]:
    threads = session.scalars(
        select(ChatThread)
        .where(ChatThread.user_id == user.id)
        .order_by(ChatThread.updated_at.desc())
    ).all()
    return [
        ThreadSummary(id=thread.id, title=thread.title, updated_at=thread.updated_at)
        for thread in threads
    ]


@router.get("/threads/{thread_id}", response_model=ThreadDetail)
async def read_thread(
    thread_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ThreadDetail:
    thread = _owned_thread(session, user, thread_id)
    messages = session.scalars(
        select(ChatMessage)
        .where(ChatMessage.thread_id == thread.id)
        .options(
            selectinload(ChatMessage.citations)
            .selectinload(MessageCitation.chunk)
            .selectinload(DocumentChunk.document)
        )
        .order_by(ChatMessage.created_at.asc())
    ).all()
    return ThreadDetail(
        thread=ThreadSummary(id=thread.id, title=thread.title, updated_at=thread.updated_at),
        messages=[_message_out(message) for message in messages],
    )


@router.delete("/threads/{thread_id}", status_code=204)
async def delete_thread(
    thread_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> None:
    thread = _owned_thread(session, user, thread_id)
    messages = session.scalars(select(ChatMessage).where(ChatMessage.thread_id == thread.id)).all()
    for message in messages:
        for citation in session.scalars(
            select(MessageCitation).where(MessageCitation.message_id == message.id)
        ).all():
            session.delete(citation)
        session.delete(message)
    session.delete(thread)
    session.commit()


def _prepare_turn(
    user_id: str, message: str, thread_id: str | None, ticker: str | None = None
) -> tuple[str, str, str, list[dict]]:
    session = open_session()
    try:
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="Your session expired. Sign in again.")
        now = datetime.now(UTC)
        if thread_id:
            thread = _owned_thread(session, user, thread_id)
        else:
            thread = ChatThread(
                id=str(uuid.uuid4()),
                user_id=user.id,
                title=_title_from(message),
                created_at=now,
                updated_at=now,
            )
            session.add(thread)
            session.flush()
        session.add(
            ChatMessage(
                id=str(uuid.uuid4()),
                thread_id=thread.id,
                role="user",
                content=message,
                created_at=now,
            )
        )
        focus = ticker.upper() if ticker else None
        passages = search_passages(session, message, ticker=focus)
        if focus:
            passages = supporting_passages(passages, message)
        preface = financial_preface(focus, message) if focus else ""
        grounded = compose_answer(passages, message)
        asks_why = any(word in message.lower() for word in ("why", "cause", "caused", "driver"))
        if preface and grounded.insufficient_evidence:
            answer = preface
            if asks_why:
                answer += "\n\nThe loaded 10-K passages do not state a cause for that change."
        elif preface:
            answer = f"{preface}\n\n{grounded.answer}"
        else:
            answer = grounded.answer
        by_chunk = {passage.chunk_id: passage for passage in passages}
        payloads: list[dict] = []
        if passages:
            for citation in grounded.citations:
                payload = citation.model_dump(by_alias=True)
                passage = by_chunk[citation.chunk_id]
                payload["passage"] = passage.text
                payload["paragraph"] = passage.chunk_index + 1
                payload["locator"] = f"{passage.section} · paragraph {passage.chunk_index + 1}"
                payloads.append(payload)
        thread.updated_at = now
        session.commit()
        return thread.id, thread.title, answer, payloads
    finally:
        session.close()


def _persist_answer(thread_id: str, answer: str, citations: list[dict]) -> None:
    session = open_session()
    try:
        now = datetime.now(UTC)
        message = ChatMessage(
            id=str(uuid.uuid4()),
            thread_id=thread_id,
            role="assistant",
            content=answer,
            created_at=now,
        )
        session.add(message)
        session.flush()
        for citation in citations:
            session.add(
                MessageCitation(
                    id=str(uuid.uuid4()),
                    message_id=message.id,
                    chunk_id=citation["chunkId"],
                    label=citation["label"],
                    excerpt=citation["excerpt"],
                )
            )
        thread = session.get(ChatThread, thread_id)
        if thread is not None:
            thread.updated_at = now
        session.commit()
    finally:
        session.close()


@router.post("/chat/stream")
async def stream_chat(
    body: ChatRequest,
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    import asyncio

    message = " ".join(body.message.split())
    if not message:
        raise HTTPException(status_code=422, detail="Enter a question.")
    thread_id, title, answer, citation_payloads = await asyncio.to_thread(
        _prepare_turn, user.id, message, body.thread_id, body.ticker
    )

    def events() -> Iterator[str]:
        yield _sse("thread", {"id": thread_id, "title": title})
        for piece in stream_pieces(answer):
            yield _sse("delta", {"text": piece})
        yield _sse("citations", {"citations": citation_payloads})
        _persist_answer(thread_id, answer, citation_payloads)
        yield _sse("done", {"threadId": thread_id})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
