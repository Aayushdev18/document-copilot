import { useState } from "react"

import { CitedText } from "@/components/chat/CitedText"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import { shortCompany } from "@/lib/companies"
import { errorMessage } from "@/lib/http"
import { changeTone, formatChange, metricByKey } from "@/lib/insights"
import { revenueCitation, sectionTrail } from "@/lib/sources"
import type { Citation, CompanySnapshot, Filing } from "@/lib/types"

type ComparePanelProps = {
  filings: Filing[]
  snapshots: Record<string, CompanySnapshot>
  onOpenCitation: (citation: Citation) => void
}

function headline(filings: Filing[]): string {
  const names = filings.map((filing) => shortCompany(filing.company))
  if (names.length === 2) return `${names[0]} vs ${names[1]}`
  return names.join(", ")
}

export function ComparePanel({ filings, snapshots, onOpenCitation }: ComparePanelProps) {
  const [selected, setSelected] = useState<string[]>(["AAPL", "MSFT"])
  const [narrative, setNarrative] = useState("")
  const [sources, setSources] = useState<Citation[]>([])
  const [writing, setWriting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const chosen = filings.filter((filing) => selected.includes(filing.ticker))

  function toggle(ticker: string) {
    setNarrative("")
    setSources([])
    setError(null)
    setSelected((current) => {
      if (current.includes(ticker)) {
        if (current.length === 2) return current
        return current.filter((item) => item !== ticker)
      }
      return [...current, ticker]
    })
  }

  async function writeComparison() {
    setWriting(true)
    setError(null)
    setNarrative("")
    setSources([])
    try {
      const result = await api.compare(selected)
      const words = result.narrative.split(" ")
      let built = ""
      for (let index = 0; index < words.length; index += 1) {
        built = index === 0 ? words[index] : `${built} ${words[index]}`
        setNarrative(built)
        await new Promise((resolve) => setTimeout(resolve, 16))
      }
      setSources(result.sources)
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setWriting(false)
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-5 px-4 py-6 md:px-8">
      <header>
        <p className="text-xs tracking-[0.16em] text-muted-foreground uppercase">Compare Companies</p>
        <h2 className="mt-1 font-heading text-3xl tracking-tight">{headline(chosen) || "Compare"}</h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
          Growth is the change between the two most recent fiscal years in each company&apos;s own
          10-K. Those year-ends are not the same calendar year.
        </p>
      </header>
      <div className="flex flex-wrap gap-2">
        {filings.map((filing) => {
          const active = selected.includes(filing.ticker)
          return (
            <button
              key={filing.ticker}
              type="button"
              aria-pressed={active}
              onClick={() => toggle(filing.ticker)}
              className={`rounded-full border px-3 py-1.5 text-sm ${
                active ? "border-primary bg-primary text-primary-foreground" : "bg-card"
              }`}
            >
              {shortCompany(filing.company)}
              {active ? " ✓" : ""}
            </button>
          )
        })}
      </div>
      <div className="overflow-x-auto rounded-xl border bg-card">
        <table className="w-full min-w-[40rem] text-left text-sm">
          <thead className="border-b text-xs tracking-wide text-muted-foreground uppercase">
            <tr>
              <th className="px-3 py-2 font-medium">Metric</th>
              {chosen.map((filing) => (
                <th key={filing.ticker} className="px-3 py-2 font-medium">
                  {shortCompany(filing.company)}
                  <div className="mt-1 font-mono text-[10px] tracking-normal normal-case">
                    {snapshots[filing.ticker]?.metrics[0]?.current.year ?? "…"} 10-K
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr className="border-b">
              <td className="px-3 py-3 align-top">Revenue</td>
              {chosen.map((filing) => {
                const snapshot = snapshots[filing.ticker]
                const metric = snapshot ? metricByKey(snapshot, "revenue") : undefined
                const tone = metric ? changeTone(metric.change) : "flat"
                let color = ""
                if (tone === "up") color = "text-primary"
                if (tone === "down") color = "text-destructive"
                const source = snapshot ? revenueCitation(snapshot) : null
                return (
                  <td key={filing.ticker} className="px-3 py-3 align-top">
                    <p className="font-mono">{metric ? metric.current.display : "…"}</p>
                    {metric && <p className={`font-mono text-xs ${color}`}>{formatChange(metric.change)}</p>}
                    {source && (
                      <button
                        type="button"
                        className="mt-2 text-xs text-primary underline-offset-2 hover:underline"
                        onClick={() => onOpenCitation(source)}
                      >
                        source
                      </button>
                    )}
                  </td>
                )
              })}
            </tr>
            <tr className="border-b">
              <td className="px-3 py-3 align-top">Risks</td>
              {chosen.map((filing) => {
                const risks = snapshots[filing.ticker]?.risks.slice(0, 3) ?? []
                return (
                  <td key={filing.ticker} className="px-3 py-3 align-top text-sm leading-6">
                    {risks.length === 0 && "…"}
                    {risks.map((risk) => (
                      <p key={risk.citation.chunkId}>
                        {risk.title}{" "}
                        <button
                          type="button"
                          className="text-xs text-primary underline-offset-2 hover:underline"
                          onClick={() => onOpenCitation(risk.citation)}
                        >
                          source
                        </button>
                      </p>
                    ))}
                  </td>
                )
              })}
            </tr>
            <tr>
              <td className="px-3 py-3 align-top">Business performance</td>
              {chosen.map((filing) => {
                const snapshot = snapshots[filing.ticker]
                return (
                  <td key={filing.ticker} className="px-3 py-3 align-top text-sm leading-6">
                    {snapshot?.segments ?? "…"}
                    {snapshot?.segmentCitation && (
                      <button
                        type="button"
                        className="mt-2 block text-xs text-primary underline-offset-2 hover:underline"
                        onClick={() => onOpenCitation(snapshot.segmentCitation as Citation)}
                      >
                        source
                      </button>
                    )}
                  </td>
                )
              })}
            </tr>
          </tbody>
        </table>
      </div>
      <section className="rounded-2xl border bg-card p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="font-heading text-xl">Sourced comparison</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Written only from the loaded 10-K facts, Item 1A, and the segment description.
            </p>
          </div>
          <Button type="button" onClick={() => void writeComparison()} disabled={writing || chosen.length < 2}>
            {writing ? "Writing…" : "Write sourced comparison"}
          </Button>
        </div>
        {error && <p className="mt-4 text-sm text-destructive">{error}</p>}
        {!narrative && !writing && !error && (
          <p className="mt-4 text-sm text-muted-foreground">
            Choose at least two companies, then write a comparison you can cite.
          </p>
        )}
        {narrative && (
          <div className="mt-4">
            <CitedText
              text={narrative}
              citations={sources}
              onOpen={onOpenCitation}
              className="text-sm leading-7 whitespace-pre-wrap"
            />
            {writing && (
              <span className="ml-0.5 inline-block h-4 w-px animate-pulse bg-foreground align-middle" />
            )}
          </div>
        )}
        {sources.length > 0 && (
          <div className="mt-4">
            <p className="text-[11px] tracking-[0.14em] text-muted-foreground uppercase">Sources</p>
            <div className="mt-2 flex flex-col gap-2">
              {sources.map((citation) => (
                <button
                  key={citation.chunkId + citation.label}
                  type="button"
                  className="text-left"
                  onClick={() => onOpenCitation(citation)}
                >
                  <Badge variant="outline" className="h-auto max-w-full px-2.5 py-1 font-mono whitespace-normal">
                    [{citation.label}] {citation.company} → {sectionTrail(citation.section)}
                  </Badge>
                </button>
              ))}
            </div>
          </div>
        )}
      </section>
    </div>
  )
}
