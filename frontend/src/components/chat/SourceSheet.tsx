import { Badge } from "@/components/ui/badge"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import type { Citation } from "@/lib/types"

type SourceSheetProps = {
  citation: Citation | null
  onClose: () => void
}

export function SourceSheet({ citation, onClose }: SourceSheetProps) {
  return (
    <Sheet
      open={citation !== null}
      onOpenChange={(open) => {
        if (!open) onClose()
      }}
    >
      <SheetContent
        side="right"
        className="overflow-y-auto bg-card shadow-2xl"
        style={{ width: "min(28rem, 100vw)", maxWidth: "28rem" }}
      >
        {citation && (
          <>
            <SheetHeader className="pr-8">
              <Badge variant="secondary" className="w-fit font-mono">
                {citation.ticker} · {citation.form}
              </Badge>
              <SheetTitle className="font-heading text-xl">{citation.company}</SheetTitle>
              <SheetDescription>
                {citation.locator ?? citation.section}
                {citation.locator ? "" : ` · Filed ${citation.filingDate}`}
              </SheetDescription>
            </SheetHeader>
            <div className="px-4 pb-8">
              <p className="font-mono text-[11px] text-muted-foreground">
                Filed {citation.filingDate}
                {citation.paragraph ? ` · paragraph ${citation.paragraph}` : ""}
              </p>
              <p className="mt-3 text-sm leading-7 break-words whitespace-pre-wrap">{citation.passage}</p>
              <a
                href={citation.sourceUrl}
                target="_blank"
                rel="noreferrer"
                className="mt-5 inline-block text-sm text-primary underline-offset-2 hover:underline"
              >
                Open the filing on EDGAR
              </a>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
