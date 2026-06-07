"use client";

import { useState, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sidebar, navItems } from "@/components/acos/sidebar";
import { OverviewSection } from "@/components/acos/overview";
import { Part1Analysis } from "@/components/acos/part1-analysis";
import { Part2ACOS } from "@/components/acos/part2-acos";
import { Part3AFM } from "@/components/acos/part3-afm";
import { Part4Training } from "@/components/acos/part4-training";
import { Part5Learning } from "@/components/acos/part5-learning";
import { Part6Orchestration } from "@/components/acos/part6-orchestration";
import { Part7Multimodal } from "@/components/acos/part7-multimodal";
import { Part8Evolution } from "@/components/acos/part8-evolution";
import { Part9Market } from "@/components/acos/part9-market";
import { Part10Attack } from "@/components/acos/part10-attack";
import { Part11MasterPlan } from "@/components/acos/part11-masterplan";

const sectionComponents: Record<string, React.ComponentType> = {
  overview: OverviewSection,
  part1: Part1Analysis,
  part2: Part2ACOS,
  part3: Part3AFM,
  part4: Part4Training,
  part5: Part5Learning,
  part6: Part6Orchestration,
  part7: Part7Multimodal,
  part8: Part8Evolution,
  part9: Part9Market,
  part10: Part10Attack,
  part11: Part11MasterPlan,
};

  // Read initial section from URL hash (only on first render)
  const getInitialSection = () => {
    if (typeof window === "undefined") return "overview";
    const hash = window.location.hash.replace("#", "");
    return hash && sectionComponents[hash] ? hash : "overview";
  };

export default function Home() {
  const [activeSection, setActiveSection] = useState(getInitialSection);
  const contentRef = useRef<HTMLDivElement>(null);

  const handleSectionChange = useCallback((id: string) => {
    setActiveSection(id);
    // Update URL hash
    if (typeof window !== "undefined") {
      window.location.hash = id;
    }
    // Scroll content to top
    if (contentRef.current) {
      contentRef.current.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, []);

  const ActiveComponent = sectionComponents[activeSection] || OverviewSection;
  const activeNav = navItems.find((n) => n.id === activeSection);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <Sidebar
        activeSection={activeSection}
        onSectionChange={handleSectionChange}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar for mobile offset */}
        <div className="h-14 lg:hidden flex-shrink-0" />

        {/* Content area */}
        <main
          ref={contentRef}
          className="flex-1 overflow-y-auto"
        >
          <AnimatePresence mode="wait">
            <motion.div
              key={activeSection}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
              className="max-w-5xl mx-auto px-4 md:px-6 lg:px-8 py-6 md:py-8"
            >
              {/* Section header breadcrumb */}
              {activeSection !== "overview" && activeNav && (
                <div className="mb-6 flex items-center gap-2 text-xs text-muted-foreground">
                  <button
                    onClick={() => handleSectionChange("overview")}
                    className="hover:text-foreground transition-colors"
                  >
                    ACOS
                  </button>
                  <span>/</span>
                  <span className="text-foreground">{activeNav.label}</span>
                </div>
              )}

              <ActiveComponent />
            </motion.div>
          </AnimatePresence>

          {/* Sticky Footer */}
          <footer className="mt-auto border-t border-border/20 bg-card/30 backdrop-blur-sm">
            <div className="max-w-5xl mx-auto px-4 md:px-6 lg:px-8 py-4">
              <div className="flex flex-col md:flex-row items-center justify-between gap-2">
                <div className="text-xs text-muted-foreground">
                  Avadhan Cognitive Operating System © 2026 | Built by{" "}
                  <span className="text-emerald-400 font-semibold">
                    Brahm AI Research Initiative
                  </span>
                </div>
                <div className="flex items-center gap-4 text-[10px] text-muted-foreground">
                  <span className="font-mono">ACOS v0.1.0-alpha</span>
                  <span>·</span>
                  <span>Next.js 16 + TypeScript</span>
                </div>
              </div>
            </div>
          </footer>
        </main>
      </div>
    </div>
  );
}
