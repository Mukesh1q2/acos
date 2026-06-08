"use client";

import { useState, useCallback, Suspense } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { GitCompare, ArrowLeftRight, X } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { navItems } from "@/components/acos/sidebar";
import { LoadingSkeleton } from "@/components/acos/loading-skeleton";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface SectionCompareProps {
  sectionComponents: Record<string, React.ComponentType>;
  onSectionChange: (id: string) => void;
}

/* ------------------------------------------------------------------ */
/*  SectionCompare Component                                           */
/* ------------------------------------------------------------------ */

export function SectionCompare({
  sectionComponents,
  onSectionChange,
}: SectionCompareProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [sectionA, setSectionA] = useState<string>("");
  const [sectionB, setSectionB] = useState<string>("");

  const handleSwap = useCallback(() => {
    setSectionA((prev) => {
      const temp = prev;
      setSectionB(sectionB);
      return sectionB;
    });
  }, [sectionB]);

  const handleClose = useCallback(() => {
    setIsOpen(false);
  }, []);

  const ComponentA = sectionA ? sectionComponents[sectionA] : null;
  const ComponentB = sectionB ? sectionComponents[sectionB] : null;

  // Get label for section
  const getLabel = (id: string) => {
    const item = navItems.find((n) => n.id === id);
    return item?.shortLabel ?? id;
  };

  return (
    <>
      {/* Trigger button */}
      <button
        onClick={() => setIsOpen(true)}
        className="flex items-center justify-center w-8 h-8 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-all duration-200"
        aria-label="Compare sections"
      >
        <GitCompare className="w-4 h-4" />
      </button>

      {/* Compare Dialog */}
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="max-w-[95vw] lg:max-w-[90vw] h-[85vh] flex flex-col p-0 gap-0 bg-background border-border/40">
          <DialogHeader className="px-6 py-4 border-b border-border/20 flex-shrink-0">
            <div className="flex items-center justify-between">
              <div>
                <DialogTitle className="flex items-center gap-2 text-base">
                  <GitCompare className="w-5 h-5 text-emerald-400" />
                  Section Comparison
                </DialogTitle>
                <DialogDescription className="text-xs text-muted-foreground mt-1">
                  View two sections side-by-side for comparison
                </DialogDescription>
              </div>
            </div>

            {/* Selectors row */}
            <div className="flex items-center gap-3 mt-4">
              <div className="flex-1">
                <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-mono mb-1 block">
                  Section A
                </label>
                <Select value={sectionA} onValueChange={setSectionA}>
                  <SelectTrigger className="w-full text-xs h-9">
                    <SelectValue placeholder="Select section..." />
                  </SelectTrigger>
                  <SelectContent>
                    {navItems.map((item) => (
                      <SelectItem
                        key={item.id}
                        value={item.id}
                        disabled={item.id === sectionB}
                      >
                        <span className="flex items-center gap-2">
                          {item.icon}
                          <span>{item.shortLabel}</span>
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Swap button */}
              <button
                onClick={handleSwap}
                disabled={!sectionA || !sectionB}
                className="mt-5 w-9 h-9 rounded-full border border-border/40 bg-muted/30 hover:bg-emerald-500/10 hover:border-emerald-500/30 text-muted-foreground hover:text-emerald-400 transition-all duration-200 flex items-center justify-center disabled:opacity-30 disabled:cursor-not-allowed"
                aria-label="Swap sections"
              >
                <ArrowLeftRight className="w-4 h-4" />
              </button>

              <div className="flex-1">
                <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-mono mb-1 block">
                  Section B
                </label>
                <Select value={sectionB} onValueChange={setSectionB}>
                  <SelectTrigger className="w-full text-xs h-9">
                    <SelectValue placeholder="Select section..." />
                  </SelectTrigger>
                  <SelectContent>
                    {navItems.map((item) => (
                      <SelectItem
                        key={item.id}
                        value={item.id}
                        disabled={item.id === sectionA}
                      >
                        <span className="flex items-center gap-2">
                          {item.icon}
                          <span>{item.shortLabel}</span>
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </DialogHeader>

          {/* Split layout content */}
          <div className="flex-1 min-h-0 flex flex-col lg:flex-row">
            {/* Panel A */}
            <div className="flex-1 min-h-0 flex flex-col border-r-0 lg:border-r border-border/20">
              <div className="px-4 py-2 border-b border-border/10 bg-muted/10 flex items-center justify-between flex-shrink-0">
                <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">
                  {sectionA ? getLabel(sectionA) : "Select Section A"}
                </span>
                {sectionA && (
                  <button
                    onClick={() => {
                      setIsOpen(false);
                      onSectionChange(sectionA);
                    }}
                    className="text-[10px] text-emerald-400 hover:text-emerald-300 transition-colors"
                  >
                    View full page
                  </button>
                )}
              </div>
              <ScrollArea className="flex-1 min-h-0">
                <div className="p-4 max-w-4xl mx-auto">
                  {ComponentA ? (
                    <Suspense
                      fallback={
                        <LoadingSkeleton cards={3} showTitle />
                      }
                    >
                      <ComponentA />
                    </Suspense>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-20 text-center">
                      <GitCompare className="w-10 h-10 text-muted-foreground/15 mb-3" />
                      <p className="text-xs text-muted-foreground">
                        Select a section above to view it here
                      </p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </div>

            {/* Panel B */}
            <div className="flex-1 min-h-0 flex flex-col border-t lg:border-t-0 border-border/20">
              <div className="px-4 py-2 border-b border-border/10 bg-muted/10 flex items-center justify-between flex-shrink-0">
                <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">
                  {sectionB ? getLabel(sectionB) : "Select Section B"}
                </span>
                {sectionB && (
                  <button
                    onClick={() => {
                      setIsOpen(false);
                      onSectionChange(sectionB);
                    }}
                    className="text-[10px] text-emerald-400 hover:text-emerald-300 transition-colors"
                  >
                    View full page
                  </button>
                )}
              </div>
              <ScrollArea className="flex-1 min-h-0">
                <div className="p-4 max-w-4xl mx-auto">
                  {ComponentB ? (
                    <Suspense
                      fallback={
                        <LoadingSkeleton cards={3} showTitle />
                      }
                    >
                      <ComponentB />
                    </Suspense>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-20 text-center">
                      <GitCompare className="w-10 h-10 text-muted-foreground/15 mb-3" />
                      <p className="text-xs text-muted-foreground">
                        Select a section above to view it here
                      </p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
