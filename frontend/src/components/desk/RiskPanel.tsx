import { Badge } from "@/components/ui/badge"
import type { Citation, CompanySnapshot } from "@/lib/types"
import { sectionTrail } from "@/lib/sources"

type RiskPanelProps = {
  snapshot: CompanySnapshot
  onOpenCitation: (citation: Citation) => void
}

export function RiskPanel({ snapshot, onOpenCitation }: RiskPanelProps) {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-6 md:px-8">
      <header>
        <p className="text-xs tracking-[0.16em] text-muted-foreground uppercase">Key Risks</p>
        <h2 className="mt-1 font-heading text-3xl tracking-tight">{snapshot.company}</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Each item is a sentence from Item 1A of the loaded 10-K. The title is a label for that
          sentence, and the source opens the passage.
        </p>
      </header>
      {snapshot.risks.length === 0 && (
        <p className="text-sm text-muted-foreground">Item 1A is not in the loaded passages.</p>
      )}
      <div className="flex flex-col gap-3">
        {snapshot.risks.map((risk, index) => (
          <article key={risk.citation.chunkId} className="rounded-2xl border bg-card px-4 py-4">
            <h3 className="font-heading text-lg">
              {String(index + 1).padStart(2, "0")} — {risk.title}
            </h3>
            <p className="mt-2 text-sm leading-7">{risk.text}</p>
            <button
              type="button"
              className="mt-3 text-left"
              onClick={() => onOpenCitation(risk.citation)}
            >
              <Badge variant="outline" className="font-mono">
                Source → {sectionTrail(risk.citation.section)}
              </Badge>
            </button>
          </article>
        ))}
      </div>
    </div>
  )
}
