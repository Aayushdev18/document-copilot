import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { AnalystBrief, Citation, CompanySnapshot, Filing } from "@/lib/types"

type Panel = "snapshot" | "risks" | "chat" | "brief"

type CompanyDeskProps = {
  filings: Filing[]
  ticker: string
  panel: Panel
  snapshot: CompanySnapshot | null
  brief: AnalystBrief | null
  briefError: string | null
  briefing: boolean
  onSelect: (ticker: string) => void
  onPanel: (panel: Panel) => void
  onBrief: () => void
  onOpenCitation: (citation: Citation) => void
}

export function CompanyDesk({
  filings,
  ticker,
  panel,
  snapshot,
  brief,
  briefError,
  briefing,
  onSelect,
  onPanel,
  onBrief,
  onOpenCitation,
}: CompanyDeskProps) {
  const years = snapshot
    ? [snapshot.metrics[0]?.current.year, snapshot.metrics[0]?.prior.year]
    : []

  return (
    <div className="border-b bg-card/40">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-3 px-4 py-4 md:px-8">
        <div className="flex gap-2 overflow-x-auto pb-1">
          {filings.map((filing) => {
            const active = filing.ticker === ticker
            return (
              <button
                key={filing.ticker}
                type="button"
                onClick={() => onSelect(filing.ticker)}
                className={`shrink-0 rounded-full border px-3 py-1.5 text-left text-sm ${
                  active ? "border-primary bg-primary text-primary-foreground" : "bg-card"
                }`}
              >
                <span className="font-mono text-[11px]">{filing.ticker}</span>
                <span className="ml-2">{filing.company.replace(/, Inc\.| Corporation| Inc\./, "")}</span>
              </button>
            )
          })}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {(
            [
              ["snapshot", "Financials"],
              ["risks", "Risks"],
              ["chat", "Chat"],
              ["brief", "Brief"],
            ] as const
          ).map(([id, label]) => (
            <Button
              key={id}
              type="button"
              size="sm"
              variant={panel === id ? "default" : "outline"}
              onClick={() => onPanel(id)}
            >
              {label}
            </Button>
          ))}
          <Button type="button" size="sm" onClick={onBrief} disabled={briefing}>
            {briefing ? "Writing brief…" : "Generate Analyst Brief"}
          </Button>
        </div>
        {snapshot && (
          <p className="text-xs text-muted-foreground">
            Latest 10-K filed {snapshot.filingDate}, loaded from EDGAR.{" "}
            <a className="underline-offset-2 hover:underline" href={snapshot.sourceUrl} target="_blank" rel="noreferrer">
              Open filing
            </a>
          </p>
        )}
        {panel === "snapshot" && snapshot && (
          <div className="overflow-x-auto rounded-xl border bg-card">
            <table className="w-full min-w-[32rem] text-left text-sm">
              <thead className="border-b text-xs tracking-wide text-muted-foreground uppercase">
                <tr>
                  <th className="px-3 py-2 font-medium">Metric</th>
                  <th className="px-3 py-2 font-medium">{years[0]}</th>
                  <th className="px-3 py-2 font-medium">{years[1]}</th>
                  <th className="px-3 py-2 font-medium">Change</th>
                </tr>
              </thead>
              <tbody>
                {snapshot.metrics.map((metric) => (
                  <tr key={metric.key} className="border-b last:border-0">
                    <td className="px-3 py-2">
                      <div>{metric.label}</div>
                      <a
                        href={metric.current.sourceUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="font-mono text-[10px] text-muted-foreground underline-offset-2 hover:underline"
                      >
                        us-gaap:{metric.concept}
                      </a>
                    </td>
                    <td className="px-3 py-2 font-mono">{metric.current.display}</td>
                    <td className="px-3 py-2 font-mono">{metric.prior.display}</td>
                    <td className="px-3 py-2 font-mono">{metric.change}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {panel === "risks" && snapshot && (
          <div className="flex flex-col gap-2">
            {snapshot.risks.length === 0 && (
              <p className="text-sm text-muted-foreground">Item 1A is not in the loaded passages.</p>
            )}
            {snapshot.risks.map((risk) => (
              <button
                key={risk.citation.chunkId}
                type="button"
                onClick={() => onOpenCitation(risk.citation)}
                className="rounded-xl border bg-card px-4 py-3 text-left"
              >
                <p className="text-sm leading-6">{risk.text}</p>
                <Badge variant="outline" className="mt-2 font-mono">
                  {risk.citation.locator}
                </Badge>
              </button>
            ))}
          </div>
        )}
        {panel === "brief" && (
          <div className="flex flex-col gap-4">
            {briefError && <p className="text-sm text-destructive">{briefError}</p>}
            {!brief && !briefError && (
              <p className="text-sm text-muted-foreground">
                Generate an analyst brief from this 10-K: business, performance, risks, changes,
                commentary, and takeaways.
              </p>
            )}
            {brief?.sections.map((section) => (
              <section key={section.id}>
                <h2 className="font-heading text-xl">{section.heading}</h2>
                <p className="mt-2 text-sm leading-7 whitespace-pre-wrap">{section.body}</p>
                {section.citations.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {section.citations.map((citation) => (
                      <button key={citation.chunkId + citation.label} type="button" onClick={() => onOpenCitation(citation)}>
                        <Badge variant="outline" className="font-mono">
                          [{citation.label}] {citation.locator}
                        </Badge>
                      </button>
                    ))}
                  </div>
                )}
              </section>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
