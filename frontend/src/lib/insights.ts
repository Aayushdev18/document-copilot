import type { CompanySnapshot, FinancialMetric } from "@/lib/types"

export function metricByKey(snapshot: CompanySnapshot, key: string): FinancialMetric | undefined {
  return snapshot.metrics.find((metric) => metric.key === key)
}

export function formatChange(change: string): string {
  if (change.startsWith("-")) return `−${change.slice(1)}`
  return change
}

export function changeTone(change: string): "up" | "down" | "flat" {
  if (change.startsWith("+")) return "up"
  if (change.startsWith("-") || change.startsWith("−")) return "down"
  return "flat"
}

function percent(change: string): number | null {
  const value = Number(change.replace("%", "").replace("−", "-"))
  return Number.isFinite(value) ? value : null
}

function movement(change: string, up: string, down: string, flat: string): string {
  const tone = changeTone(change)
  let word = flat
  if (tone === "up") word = up
  if (tone === "down") word = down
  const amount = change.replace("+", "").replace("-", "").replace("−", "")
  return `${word} ${amount}`
}

export function financialInsight(metrics: FinancialMetric[]): string {
  const revenue = metrics.find((metric) => metric.key === "revenue")
  const net = metrics.find((metric) => metric.key === "net_income")
  if (!revenue || !net) {
    return "The loaded 10-K facts do not include both revenue and net income."
  }
  const revenuePct = percent(revenue.change)
  const netPct = percent(net.change)
  let ending = "."
  if (revenuePct !== null && netPct !== null) {
    if (netPct > revenuePct && netPct > 0 && revenuePct > 0) {
      ending = ", indicating stronger bottom-line growth than revenue growth."
    } else if (revenuePct > netPct && revenuePct > 0 && netPct > 0) {
      ending = ", so revenue grew faster than net income."
    } else if (revenuePct > 0 && netPct < 0) {
      ending = ", so the revenue increase did not carry through to net income."
    } else if (revenuePct < 0 && netPct < 0) {
      ending = ", so both revenue and net income contracted."
    }
  }
  const revenueMove = movement(revenue.change, "increased", "decreased", "was unchanged")
  const netMove = movement(net.change, "grew", "fell", "was unchanged")
  return `Revenue ${revenueMove} YoY, while net income ${netMove}${ending}`
}
