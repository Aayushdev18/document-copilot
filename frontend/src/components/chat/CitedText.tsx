import type { ReactNode } from "react"

import type { Citation } from "@/lib/types"

type CitedTextProps = {
  text: string
  citations: Citation[]
  onOpen: (citation: Citation) => void
  className?: string
}

export function CitedText({ text, citations, onOpen, className }: CitedTextProps) {
  const parts = text.split(/(\[\d+\])/g)
  const nodes: ReactNode[] = parts.map((part, index) => {
    const match = part.match(/^\[(\d+)\]$/)
    if (!match) return <span key={index}>{part}</span>
    const citation = citations.find((item) => item.label === match[1])
    if (!citation) return <span key={index}>{part}</span>
    return (
      <button
        key={index}
        type="button"
        className="mx-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded-md border border-primary/30 bg-primary/10 px-1 align-baseline font-mono text-[12px] text-primary hover:bg-primary/20"
        onClick={() => onOpen(citation)}
      >
        {part}
      </button>
    )
  })
  return <div className={className}>{nodes}</div>
}
