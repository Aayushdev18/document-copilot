import { Badge } from "@/components/ui/badge"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { filedOn } from "@/lib/companies"
import { sectionTrail } from "@/lib/sources"
import type { Citation } from "@/lib/types"

type SourceSheetProps = {
  citation: Citation | null
  onClose: () => void
}

export function SourceSheet({ citation, onClose }: SourceSheetProps) {
  const year = citation?.filingDate?.slice(0, 4) ?? ""
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
                {citation.ticker ? `${citation.ticker} · ` : ""}
                {citation.form}
              </Badge>
              <SheetTitle className="font-heading text-xl">{citation.company}</SheetTitle>
              <SheetDescription>Source for this answer</SheetDescription>
            </SheetHeader>
            <div className="flex flex-col gap-4 px-4 pb-8">
              <div>
                <p className="text-[11px] tracking-[0.14em] text-muted-foreground uppercase">Filing</p>
                <p className="mt-1 text-sm leading-6">
                  {citation.company} {year} {citation.form}
                  {citation.filingDate ? ` · Filed ${filedOn(citation.filingDate)}` : ""}
                </p>
              </div>
              <div>
                <p className="text-[11px] tracking-[0.14em] text-muted-foreground uppercase">Section</p>
                <p className="mt-1 text-sm leading-6">
                  {citation.locator ?? sectionTrail(citation.section)}
                </p>
              </div>
              <div>
                <p className="text-[11px] tracking-[0.14em] text-muted-foreground uppercase">
                  Retrieved passage
                </p>
                <p className="mt-1 text-sm leading-7 break-words whitespace-pre-wrap">{citation.passage}</p>
              </div>
              <a
                href={citation.sourceUrl}
                target="_blank"
                rel="noreferrer"
                className="text-sm text-primary underline-offset-2 hover:underline"
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
