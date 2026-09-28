import { useEffect, useRef } from "react"

import { Badge } from "@/components/ui/badge"
import { suggestedQuestions } from "@/lib/questions"
import type { ChatMessage, Citation, Corpus } from "@/lib/types"

type TranscriptProps = {
  messages: ChatMessage[]
  streaming: string
  running: boolean
  error: string | null
  corpus: Corpus | null
  onSuggest: (question: string) => void
  onOpenCitation: (citation: Citation) => void
}

export function Transcript({
  messages,
  streaming,
  running,
  error,
  corpus,
  onSuggest,
  onOpenCitation,
}: TranscriptProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" })
  }, [messages, streaming, running])

  const showEmpty = messages.length === 0 && !streaming && !running

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-8 md:px-8">
        {showEmpty && (
          <div className="pt-8 md:pt-16">
            <p className="text-xs tracking-[0.18em] text-muted-foreground uppercase">
              Driftwood Capital
            </p>
            <h1 className="mt-3 font-heading text-4xl tracking-tight text-balance md:text-5xl">
              Ask a filing.
            </h1>
            <p className="mt-4 max-w-xl text-base leading-7 text-muted-foreground">
              Answers are quotations from the latest 10-K on the desk for Apple, Microsoft,
              NVIDIA, Amazon, and Alphabet. If the passage is not in the corpus, the copilot
              says so.
            </p>
            {corpus && (
              <p className="mt-3 font-mono text-xs text-muted-foreground">
                {corpus.filings.map((filing) => `${filing.ticker} ${filing.filingDate}`).join("  ·  ")}
              </p>
            )}
            <div className="mt-8 grid gap-2">
              {suggestedQuestions.map((item) => (
                <button
                  key={item.question}
                  type="button"
                  onClick={() => onSuggest(item.question)}
                  className="rounded-xl border bg-card px-4 py-3 text-left text-sm leading-6 transition-colors hover:border-primary/40 hover:bg-accent"
                >
                  <span className="mr-2 font-mono text-[11px] text-primary">{item.ticker}</span>
                  {item.question}
                </button>
              ))}
              <button
                type="button"
                onClick={() => onSuggest("What is the population of Lisbon?")}
                className="px-1 py-2 text-left text-sm text-muted-foreground underline-offset-2 hover:underline"
              >
                Try a question the filings cannot answer
              </button>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <MessageView key={message.id} message={message} onOpenCitation={onOpenCitation} />
        ))}

        {running && !streaming && (
          <p className="text-sm text-muted-foreground">Searching the filings…</p>
        )}

        {streaming && (
          <article className="max-w-[46rem]">
            <p className="mb-2 text-[11px] tracking-[0.14em] text-muted-foreground uppercase">
              Copilot
            </p>
            <div className="text-[15px] leading-7 whitespace-pre-wrap">{streaming}</div>
          </article>
        )}

        {error && (
          <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

function MessageView({
  message,
  onOpenCitation,
}: {
  message: ChatMessage
  onOpenCitation: (citation: Citation) => void
}) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <p className="max-w-[38rem] rounded-2xl bg-primary px-4 py-3 text-sm leading-6 text-primary-foreground">
          {message.content}
        </p>
      </div>
    )
  }

  return (
    <article className="max-w-[46rem]">
      <p className="mb-2 text-[11px] tracking-[0.14em] text-muted-foreground uppercase">Copilot</p>
      <div className="text-[15px] leading-7 whitespace-pre-wrap">{message.content}</div>
      {message.citations.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {message.citations.map((citation) => (
            <button key={citation.chunkId} type="button" onClick={() => onOpenCitation(citation)}>
              <Badge variant="outline" className="h-7 px-2.5 font-mono">
                [{citation.label}] {citation.ticker} · {citation.section.replace("Item ", "")}
              </Badge>
            </button>
          ))}
        </div>
      )}
    </article>
  )
}
