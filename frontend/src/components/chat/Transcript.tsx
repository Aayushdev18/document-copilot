import { useEffect, useRef } from "react"

import { Badge } from "@/components/ui/badge"
import { filingLinks, sourceTrail } from "@/lib/sources"
import type { ChatMessage, Citation } from "@/lib/types"

type TranscriptProps = {
  messages: ChatMessage[]
  streaming: string
  running: boolean
  error: string | null
  companyName: string
  prompts: string[]
  onSuggest: (question: string) => void
  onOpenCitation: (citation: Citation) => void
}

export function Transcript({
  messages,
  streaming,
  running,
  error,
  companyName,
  prompts,
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
          <div className="pt-6">
            <p className="text-xs tracking-[0.16em] text-muted-foreground uppercase">
              Ask about this filing
            </p>
            <h1 className="mt-2 font-heading text-3xl tracking-tight text-balance">
              {companyName}
            </h1>
            <p className="mt-3 max-w-xl text-sm leading-7 text-muted-foreground">
              Questions stay on this company&apos;s latest 10-K. Answers cite the passage or the
              XBRL fact they came from.
            </p>
            <div className="mt-5 grid gap-2">
              {prompts.map((question) => (
                <button
                  key={question}
                  type="button"
                  onClick={() => onSuggest(question)}
                  className="rounded-xl border bg-card px-4 py-3 text-left text-sm leading-6 transition-colors hover:border-primary/40 hover:bg-accent"
                >
                  {question}
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
              Answer
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

  const links = filingLinks(message.content)
  return (
    <article className="max-w-[46rem]">
      <p className="mb-2 text-[11px] tracking-[0.14em] text-muted-foreground uppercase">Answer</p>
      <div className="text-[15px] leading-7 whitespace-pre-wrap">{message.content}</div>
      <div className="mt-4 rounded-xl border bg-card px-4 py-3">
        <p className="text-[11px] tracking-[0.14em] text-muted-foreground uppercase">Sources</p>
        {message.citations.length > 0 && (
          <ul className="mt-2 flex flex-col gap-2">
            {message.citations.map((citation) => (
              <li key={citation.chunkId}>
                <button type="button" className="text-left" onClick={() => onOpenCitation(citation)}>
                  <Badge variant="outline" className="h-auto max-w-full px-2.5 py-1 font-mono whitespace-normal">
                    {sourceTrail(citation)}
                  </Badge>
                </button>
              </li>
            ))}
          </ul>
        )}
        {message.citations.length === 0 && links.length > 0 && (
          <ul className="mt-2 flex flex-col gap-2">
            {links.map((url) => (
              <li key={url}>
                <a
                  href={url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-primary underline-offset-2 hover:underline"
                >
                  SEC XBRL company facts
                </a>
              </li>
            ))}
          </ul>
        )}
        {message.citations.length === 0 && links.length === 0 && (
          <p className="mt-2 text-sm text-muted-foreground">
            No filing passage supports this answer.
          </p>
        )}
      </div>
    </article>
  )
}
