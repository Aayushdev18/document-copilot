import { useState } from "react"

import type { CompanySnapshot, Filing } from "@/lib/types"
import { shortCompany } from "@/lib/companies"
import { changeTone, formatChange, metricByKey } from "@/lib/insights"

const ROWS = [
  { key: "revenue", label: "Revenue", field: "current" },
  { key: "revenue", label: "Revenue Growth", field: "change" },
  { key: "net_income", label: "Net Income Growth", field: "change" },
  { key: "operating_income", label: "Operating Income", field: "current" },
  { key: "operating_income", label: "Operating Income Growth", field: "change" },
  { key: "debt", label: "Debt Change", field: "change" },
] as const

type ComparePanelProps = {
  filings: Filing[]
  snapshots: Record<string, CompanySnapshot>
}

function cell(snapshot: CompanySnapshot, key: string, field: "current" | "change"): string {
  const metric = metricByKey(snapshot, key)
  if (!metric) return "—"
  if (field === "current") return metric.current.display
  return formatChange(metric.change)
}

export function ComparePanel({ filings, snapshots }: ComparePanelProps) {
  const [selected, setSelected] = useState<string[]>(["AAPL", "MSFT", "NVDA"])
  const chosen = filings.filter((filing) => selected.includes(filing.ticker))

  function toggle(ticker: string) {
    setSelected((current) => {
      if (current.includes(ticker)) {
        if (current.length === 1) return current
        return current.filter((item) => item !== ticker)
      }
      return [...current, ticker]
    })
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-5 px-4 py-6 md:px-8">
      <header>
        <p className="text-xs tracking-[0.16em] text-muted-foreground uppercase">Compare Companies</p>
        <h2 className="mt-1 font-heading text-3xl tracking-tight">Latest 10-K facts, side by side</h2>
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
            {ROWS.map((row) => (
              <tr key={row.label} className="border-b last:border-0">
                <td className="px-3 py-2">{row.label}</td>
                {chosen.map((filing) => {
                  const snapshot = snapshots[filing.ticker]
                  const value = snapshot ? cell(snapshot, row.key, row.field) : "…"
                  const metric = snapshot ? metricByKey(snapshot, row.key) : undefined
                  const tone = row.field === "change" && metric ? changeTone(metric.change) : "flat"
                  let color = ""
                  if (tone === "up") color = "text-primary"
                  if (tone === "down") color = "text-destructive"
                  return (
                    <td key={filing.ticker} className={`px-3 py-2 font-mono ${color}`}>
                      {value}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
