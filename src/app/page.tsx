"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowUp, Brain } from "lucide-react";
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
import { TheoremExplorer } from "@/components/acos/theorem-explorer";
import { RoadmapTimeline } from "@/components/acos/roadmap-timeline";
import { PerformanceComparison } from "@/components/acos/performance-comparison";
import { CommandPalette } from "@/components/acos/command-palette";
import { ChatPanel } from "@/components/acos/chat-panel";
import { SectionToc } from "@/components/acos/section-toc";
import { BookmarkButton, BookmarkedSections } from "@/components/acos/bookmarks";
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
  roadmap: RoadmapTimeline,
  theorems: TheoremExplorer,
  performance: PerformanceComparison,
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

  // Keyboard navigation with Alt+Arrow keys
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle Alt+Arrow for section navigation
      if (!e.altKey) return;
      if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;

      e.preventDefault();
      const currentIndex = navItems.findIndex((n) => n.id === activeSection);
      if (currentIndex < 0) return;

      let nextIndex: number;
      if (e.key === "ArrowDown") {
        nextIndex = Math.min(currentIndex + 1, navItems.length - 1);
      } else {
        nextIndex = Math.max(currentIndex - 1, 0);
      }

      if (nextIndex !== currentIndex) {
        handleSectionChange(navItems[nextIndex].id);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeSection, handleSectionChange]);

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
            className="absolute top-0 left-0 h-full bg-gradient-to-r from-emerald-500 via-teal-400 to-emerald-400"
            initial={{ width: 0 }}
            animate={{ width: `${progressPercent}%` }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          />
          {/* Shimmer on progress */}
          <motion.div
            className="absolute top-0 left-0 h-full animate-shimmer"
            style={{ width: `${progressPercent}%` }}
            transition={{ duration: 0.4 }}
          />
        </div>

        {/* Content area */}
        <main
          ref={contentRef}
          className="flex-1 overflow-y-auto relative bg-dot-grid"
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
                  <div className="ml-auto">
                    <BookmarkButton sectionId={activeSection} />
                  </div>
                </div>
              )}

              <div data-section-content>
                <ActiveComponent />
                {/* Bookmarked Sections in Overview */}
                {activeSection === "overview" && (
                  <div className="mt-10">
                    <BookmarkedSections onNavigate={handleSectionChange} />
                  </div>
                )}
              </div>
            </motion.div>
          </AnimatePresence>

          {/* Sticky Footer */}
          <footer className="mt-auto border-t border-border/20 bg-gradient-to-r from-card/50 via-card/30 to-card/50 backdrop-blur-md">
            <div className="max-w-5xl mx-auto px-4 md:px-6 lg:px-8 py-5">
              <div className="flex flex-col md:flex-row items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-6 h-6 rounded-md bg-emerald-600/20 flex items-center justify-center">
                    <Brain className="w-3.5 h-3.5 text-emerald-400" />
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Avadhan Cognitive Operating System &copy; 2026 | Built by{" "}
                    <span className="text-emerald-400 font-semibold">
                      Brahm AI Research Initiative
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-600/10 border border-emerald-500/15">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-[10px] font-mono text-emerald-400">v0.1.0-alpha</span>
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                    <span>Next.js 16</span>
                    <span className="opacity-30">|</span>
                    <span>TypeScript</span>
                    <span className="opacity-30">|</span>
                    <span>Prisma</span>
                    <span className="opacity-30">|</span>
                    <span className="font-mono">Alt+Arrow Nav</span>
                  </div>
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

      {/* Section Table of Contents (desktop only) */}
      <SectionToc />

      {/* Command Palette */}
      <CommandPalette onSectionChange={handleSectionChange} />

      {/* AI Chat Panel */}
      <ChatPanel />
    </div>
  );
}
