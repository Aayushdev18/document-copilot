import { useState } from "react"

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"

const STEPS = [
  {
    title: "SEC EDGAR",
    detail: "The latest 10-K for Apple, Microsoft, NVIDIA, Amazon, and Alphabet.",
  },
  {
    title: "Ingestion",
    detail: "Filing text and the annual XBRL facts are loaded onto the desk.",
  },
  {
    title: "Chunking",
    detail: "Item 1, Item 1A, and Item 7 are split into passages.",
  },
  {
    title: "Retrieval",
    detail: "The question is matched to those passages with full-text search.",
  },
  {
    title: "Grounded answer",
    detail: "The reply uses only a retrieved passage or an XBRL fact from that filing.",
  },
  {
    title: "Cited response",
    detail: "Each [1] opens the exact passage that was used.",
  },
]

export function HowItWorks() {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-3 text-left text-xs text-sidebar-foreground/70 underline-offset-2 hover:text-sidebar-foreground hover:underline"
      >
        How it works
      </button>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="overflow-y-auto bg-card sm:max-w-md">
          <SheetHeader>
            <SheetTitle className="font-heading text-2xl">How Driftwood works</SheetTitle>
            <SheetDescription>
              A question is answered only from the loaded 10-K. The number in the answer is the
              passage that was retrieved.
            </SheetDescription>
          </SheetHeader>
          <ol className="flex flex-col gap-3 px-4 pb-8">
            {STEPS.map((step, index) => (
              <li key={step.title} className="rounded-xl border bg-background px-3 py-3">
                <p className="font-mono text-[11px] text-muted-foreground">
                  {String(index + 1).padStart(2, "0")}
                </p>
                <p className="mt-1 text-sm font-medium">{step.title}</p>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">{step.detail}</p>
              </li>
            ))}
          </ol>
          <p className="px-4 pb-6 text-xs leading-5 text-muted-foreground">
            Dollar figures are the filing&apos;s XBRL facts, with the accession on the source. A
            model drafts the prose when an API key is configured, and it still has to cite a
            retrieved passage. HTML filings do not have stable page numbers, so the locator is the
            10-K item and paragraph.
          </p>
        </SheetContent>
      </Sheet>
    </>
  )
}
