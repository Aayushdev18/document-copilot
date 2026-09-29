import { BriefPanel } from "@/components/desk/BriefPanel"
import { ComparePanel } from "@/components/desk/ComparePanel"
import { FinancialPanel } from "@/components/desk/FinancialPanel"
import { RiskPanel } from "@/components/desk/RiskPanel"
import { Button } from "@/components/ui/button"
import { filedOn, filingLabel, shortCompany } from "@/lib/companies"
import type { AnalystBrief, Citation, CompanySnapshot, DeskPanel, Filing } from "@/lib/types"

type Panel = DeskPanel

type CompanyDeskProps = {
  filings: Filing[]
  ticker: string
  panel: Panel
  snapshots: Record<string, CompanySnapshot>
  brief: AnalystBrief | null
  briefError: string | null
  briefing: boolean
  onSelect: (ticker: string) => void
  onPanel: (panel: Panel) => void
  onBrief: () => void
  onOpenCitation: (citation: Citation) => void
}

const TABS = [
  ["snapshot", "Financials"],
  ["risks", "Risks"],
  ["chat", "Chat"],
  ["brief", "Brief"],
  ["compare", "Compare"],
] as const

export function CompanyDesk({
  filings,
  ticker,
  panel,
  snapshots,
  brief,
  briefError,
  briefing,
  onSelect,
  onPanel,
  onBrief,
  onOpenCitation,
}: CompanyDeskProps) {
  const snapshot = snapshots[ticker] ?? null
  const filing = filings.find((item) => item.ticker === ticker)
  const year = snapshot?.filingDate.slice(0, 4) ?? snapshot?.metrics[0]?.current.year
  const sourceFacts = snapshot
    ? [
        ["Source", "SEC EDGAR"],
        ["Filing", year ? filingLabel(year, snapshot.form) : snapshot.form],
        ["Filed", filedOn(snapshot.filingDate)],
        ["Passages", filing ? String(filing.passageCount) : "—"],
      ]
    : []

  return (
    <div className={panel === "chat" ? "shrink-0" : "flex min-h-0 flex-1 flex-col"}>
      <div className="border-b bg-card/40">
        <div className="mx-auto flex w-full max-w-5xl flex-col gap-3 px-4 py-4 md:px-8">
          <div className="flex gap-2 overflow-x-auto pb-1">
            {filings.map((item) => {
              const active = item.ticker === ticker
              return (
                <button
                  key={item.ticker}
                  type="button"
                  onClick={() => onSelect(item.ticker)}
                  className={`shrink-0 rounded-full border px-3 py-1.5 text-left text-sm ${
                    active ? "border-primary bg-primary text-primary-foreground" : "bg-card"
                  }`}
                >
                  <span className="font-mono text-[11px]">{item.ticker}</span>
                  <span className="ml-2">{shortCompany(item.company)}</span>
                </button>
              )
            })}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {TABS.map(([id, label]) => (
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
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {sourceFacts.map(([label, value]) => (
                <div key={label} className="rounded-xl border bg-card px-3 py-2">
                  <p className="text-[10px] tracking-[0.14em] text-muted-foreground uppercase">{label}</p>
                  {label === "Source" ? (
                    <a
                      href={snapshot.sourceUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="text-sm font-medium underline-offset-2 hover:underline"
                    >
                      {value}
                    </a>
                  ) : (
                    <p className="text-sm font-medium">{value}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      {panel !== "chat" && (
        <div className="min-h-0 flex-1 overflow-y-auto">
          {!snapshot && panel !== "compare" && (
            <p className="px-4 py-8 text-sm text-muted-foreground">Loading the filing…</p>
          )}
          {panel === "snapshot" && snapshot && <FinancialPanel snapshot={snapshot} />}
          {panel === "risks" && snapshot && (
            <RiskPanel snapshot={snapshot} onOpenCitation={onOpenCitation} />
          )}
          {panel === "brief" && (
            <BriefPanel
              company={snapshot?.company ?? ticker}
              brief={brief}
              briefError={briefError}
              briefing={briefing}
              onBrief={onBrief}
              onOpenCitation={onOpenCitation}
            />
          )}
          {panel === "compare" && (
            <ComparePanel
              filings={filings}
              snapshots={snapshots}
              onOpenCitation={onOpenCitation}
            />
          )}
        </div>
      )}
    </div>
  )
}
