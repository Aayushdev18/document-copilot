import { useState } from "react"

import type { CompanySnapshot, FinancialMetric } from "@/lib/types"
import { changeTone, financialInsight, formatChange, metricByKey } from "@/lib/insights"

const HIGHLIGHTS = [
  ["revenue", "Revenue"],
  ["net_income", "Net income"],
  ["operating_income", "Operating income"],
] as const

const CHART_METRICS = [
  ["revenue", "Revenue"],
  ["net_income", "Net Income"],
  ["operating_income", "Operating Income"],
  ["eps", "EPS"],
] as const

function toneClass(change: string): string {
  const tone = changeTone(change)
  if (tone === "up") return "text-primary"
  if (tone === "down") return "text-destructive"
  return "text-foreground"
}

function PerformanceChart({ metric }: { metric: FinancialMetric }) {
  const max = Math.max(Math.abs(metric.prior.value), Math.abs(metric.current.value), 1)
  const rows = [
    { point: metric.prior, current: false },
    { point: metric.current, current: true },
  ]
  return (
    <div className="flex flex-col gap-3">
      {rows.map((row) => {
        const width = Math.max(6, (Math.abs(row.point.value) / max) * 100)
        return (
          <div key={row.point.year} className="grid grid-cols-[3.25rem_1fr_auto] items-center gap-3">
            <span className="font-mono text-xs text-muted-foreground">{row.point.year}</span>
            <div className="h-8 overflow-hidden rounded-md bg-muted">
              <div
                className={row.current ? "h-8 rounded-md bg-primary" : "h-8 rounded-md bg-primary/35"}
                style={{ width: `${width}%` }}
              />
            </div>
            <span className="font-mono text-sm">{row.point.display}</span>
          </div>
        )
      })}
    </div>
  )
}

export function FinancialPanel({ snapshot }: { snapshot: CompanySnapshot }) {
  const [chartKey, setChartKey] = useState<(typeof CHART_METRICS)[number][0]>("revenue")
  const chart = metricByKey(snapshot, chartKey) ?? snapshot.metrics[0]
  const insightCards = [
    ["revenue", "Revenue Growth"],
    ["net_income", "Net Income Growth"],
    ["debt", "Debt Change"],
  ]
    .map(([key, label]) => {
      const metric = metricByKey(snapshot, key)
      return metric ? { label, change: metric.change } : null
    })
    .filter((card): card is { label: string; change: string } => card !== null)

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-6 md:px-8">
      <header>
        <h2 className="font-heading text-3xl tracking-tight text-balance">{snapshot.company}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{snapshot.industry}</p>
        <p className="mt-3 max-w-3xl text-sm leading-7">{snapshot.overview}</p>
        <p className="mt-2 text-xs text-muted-foreground">From Item 1 of the loaded 10-K.</p>
      </header>

      <div className="grid gap-3 sm:grid-cols-3">
        {HIGHLIGHTS.map(([key, label]) => {
          const metric = metricByKey(snapshot, key)
          if (!metric) return null
          return (
            <div key={key} className="rounded-xl border bg-card px-4 py-3">
              <p className="text-xs tracking-wide text-muted-foreground uppercase">{label}</p>
              <p className="mt-1 font-heading text-2xl">{metric.current.display}</p>
              <p className={`mt-1 font-mono text-xs ${toneClass(metric.change)}`}>
                {formatChange(metric.change)} vs {metric.prior.year}
              </p>
            </div>
          )
        })}
      </div>

      <div className="overflow-x-auto rounded-xl border bg-card">
        <table className="w-full min-w-[36rem] text-left text-sm">
          <thead className="border-b text-xs tracking-wide text-muted-foreground uppercase">
            <tr>
              <th className="px-3 py-2 font-medium">Metric</th>
              <th className="px-3 py-2 font-medium">{snapshot.metrics[0]?.current.year}</th>
              <th className="px-3 py-2 font-medium">{snapshot.metrics[0]?.prior.year}</th>
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
                <td className={`px-3 py-2 font-mono ${toneClass(metric.change)}`}>
                  {formatChange(metric.change)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <section className="rounded-2xl border bg-card p-5">
        <p className="text-xs tracking-[0.16em] text-muted-foreground uppercase">AI Financial Insights</p>
        <p className="mt-3 max-w-3xl text-base leading-7">{financialInsight(snapshot.metrics)}</p>
        <p className="mt-2 text-xs text-muted-foreground">
          Composed from this 10-K&apos;s annual XBRL facts. No figures are estimated.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {insightCards.map((card) => (
            <div key={card.label} className="rounded-xl border bg-background px-4 py-3">
              <p className="text-xs text-muted-foreground">{card.label}</p>
              <p className={`mt-1 font-heading text-2xl ${toneClass(card.change)}`}>
                {formatChange(card.change)}
              </p>
            </div>
          ))}
        </div>
      </section>

      {chart && (
        <section className="rounded-2xl border bg-card p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <h3 className="font-heading text-xl">Financial Performance</h3>
            <div className="flex flex-wrap gap-2">
              {CHART_METRICS.map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setChartKey(key)}
                  className={`rounded-full border px-3 py-1 text-xs ${
                    chartKey === key ? "border-primary bg-primary text-primary-foreground" : "bg-background"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <div className="mt-5">
            <PerformanceChart metric={chart} />
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            {chart.label} for the two fiscal years in the latest 10-K. Bar length is the reported
            amount, not a forecast.
          </p>
        </section>
      )}
    </div>
  )
}
