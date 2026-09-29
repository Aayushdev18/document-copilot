import { CitedText } from "@/components/chat/CitedText"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { AnalystBrief, Citation } from "@/lib/types"
import { sectionTrail } from "@/lib/sources"

const BRIEF_SECTIONS = [
  "Business Performance",
  "Financial Performance",
  "Key Risks",
  "Year-over-Year Changes",
  "Management Commentary",
  "Key Takeaways",
]

type BriefPanelProps = {
  company: string
  brief: AnalystBrief | null
  briefError: string | null
  briefing: boolean
  onBrief: () => void
  onOpenCitation: (citation: Citation) => void
}

export function BriefPanel({
  company,
  brief,
  briefError,
  briefing,
  onBrief,
  onOpenCitation,
}: BriefPanelProps) {
  if (!brief) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-6 md:px-8">
        <section className="rounded-2xl border bg-card p-6">
          <p className="text-xs tracking-[0.16em] text-muted-foreground uppercase">Analyst Brief</p>
          <h2 className="mt-2 font-heading text-3xl tracking-tight text-balance">
            Write the brief for {company}
          </h2>
          <p className="mt-3 max-w-xl text-sm leading-7 text-muted-foreground">
            Six sections drawn from this company&apos;s latest 10-K and its annual XBRL facts.
            Passages keep their section, and the financial lines keep their accession.
          </p>
          <ol className="mt-5 grid gap-2 sm:grid-cols-2">
            {BRIEF_SECTIONS.map((heading, index) => (
              <li key={heading} className="rounded-xl border bg-background px-3 py-2 text-sm">
                <span className="font-mono text-[11px] text-muted-foreground">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="ml-2">{heading}</span>
              </li>
            ))}
          </ol>
          {briefError && <p className="mt-4 text-sm text-destructive">{briefError}</p>}
          <Button type="button" className="mt-5 h-10 px-4" onClick={onBrief} disabled={briefing}>
            {briefing ? "Writing brief…" : "Generate Analyst Brief"}
          </Button>
        </section>
      </div>
    )
  }

  return (
    <article className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6 md:px-8">
      <header>
        <p className="text-xs tracking-[0.16em] text-muted-foreground uppercase">Analyst Brief</p>
        <h2 className="mt-1 font-heading text-3xl tracking-tight">{brief.company}</h2>
      </header>
      {brief.sections.map((section, index) => (
        <section key={section.id} className="rounded-2xl border bg-card px-5 py-4">
          <p className="font-mono text-[11px] text-muted-foreground">
            {String(index + 1).padStart(2, "0")}
          </p>
          <h3 className="mt-1 font-heading text-xl">{section.heading}</h3>
          <CitedText
            text={section.body}
            citations={section.citations}
            onOpen={onOpenCitation}
            className="mt-3 text-sm leading-7 whitespace-pre-wrap"
          />
          {section.citations.length > 0 && (
            <div className="mt-3 flex flex-col gap-2">
              <p className="text-[11px] tracking-[0.14em] text-muted-foreground uppercase">Sources</p>
              <div className="flex flex-wrap gap-2">
                {section.citations.map((citation) => (
                  <button
                    key={citation.chunkId + citation.label}
                    type="button"
                    onClick={() => onOpenCitation(citation)}
                  >
                    <Badge variant="outline" className="font-mono">
                      [{citation.label}] {sectionTrail(citation.section)}
                    </Badge>
                  </button>
                ))}
              </div>
            </div>
          )}
        </section>
      ))}
      <div>
        <Button type="button" variant="outline" onClick={onBrief} disabled={briefing}>
          {briefing ? "Writing brief…" : "Regenerate Analyst Brief"}
        </Button>
      </div>
    </article>
  )
}
