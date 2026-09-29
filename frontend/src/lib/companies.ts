export function shortCompany(company: string): string {
  return company
    .replace("Amazon.com, Inc.", "Amazon")
    .replace(/, Inc\.| Corporation| Inc\./g, "")
}

export function filedOn(iso: string): string {
  const [year, month, day] = iso.split("-").map(Number)
  if (!year || !month || !day) return iso
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(year, month - 1, day)))
}

export function filingLabel(year: string, form: string): string {
  return `${year} ${form}`
}
