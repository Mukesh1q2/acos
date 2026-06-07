"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowUp } from "lucide-react";
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
import { CommandPalette } from "@/components/acos/command-palette";
import { ChatPanel } from "@/components/acos/chat-panel";
import { Progress } from "@/components/ui/progress";

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
  const [showScrollTop, setShowScrollTop] = useState(false);

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

  // Scroll-to-top visibility tracking
  useEffect(() => {
    const el = contentRef.current;
    if (!el) return;
    const handleScroll = () => {
      setShowScrollTop(el.scrollTop > 300);
    };
    el.addEventListener("scroll", handleScroll, { passive: true });
    return () => el.removeEventListener("scroll", handleScroll);
  }, []);

  const scrollToTop = useCallback(() => {
    if (contentRef.current) {
      contentRef.current.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, []);

  const ActiveComponent = sectionComponents[activeSection] || OverviewSection;
  const activeNav = navItems.find((n) => n.id === activeSection);

  // Progress calculation
  const currentIndex = navItems.findIndex((n) => n.id === activeSection);
  const progressPercent = currentIndex >= 0 ? ((currentIndex + 1) / navItems.length) * 100 : 0;

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

        {/* Progress bar */}
        <div className="relative h-1 bg-muted/30 flex-shrink-0">
          <motion.div
            className="absolute top-0 left-0 h-full bg-gradient-to-r from-emerald-500 to-teal-400"
            initial={{ width: 0 }}
            animate={{ width: `${progressPercent}%` }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          />
        </div>

        {/* Content area */}
        <main
          ref={contentRef}
          className="flex-1 overflow-y-auto relative"
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
                  Avadhan Cognitive Operating System &copy; 2026 | Built by{" "}
                  <span className="text-emerald-400 font-semibold">
                    Brahm AI Research Initiative
                  </span>
                </div>
                <div className="flex items-center gap-4 text-[10px] text-muted-foreground">
                  <span className="font-mono">ACOS v0.1.0-alpha</span>
                  <span className="opacity-50">|</span>
                  <span>Next.js 16 + TypeScript</span>
                </div>
              </div>
            </div>
          </footer>
        </main>
      </div>

      {/* Scroll to top button */}
      <AnimatePresence>
        {showScrollTop && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.2 }}
            onClick={scrollToTop}
            className="fixed bottom-[5.5rem] right-6 z-40 w-10 h-10 rounded-full bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-500/20 flex items-center justify-center transition-colors duration-200"
            aria-label="Scroll to top"
          >
            <ArrowUp className="w-4 h-4" />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Command Palette */}
      <CommandPalette onSectionChange={handleSectionChange} />

      {/* AI Chat Panel */}
      <ChatPanel />
    </div>
  );
}
