"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { List, ChevronRight, ChevronDown } from "lucide-react";

interface Heading {
  id: string;
  text: string;
  level: number;
}

export function SectionToc() {
  const [headings, setHeadings] = useState<Heading[]>([]);
  const [activeId, setActiveId] = useState<string>("");
  const [collapsed, setCollapsed] = useState(false);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const rafRef = useRef<number | null>(null);

  // Scan for h2/h3 headings with IDs
  const scanHeadings = useCallback(() => {
    const mainContent = document.querySelector("[data-section-content]");
    if (!mainContent) return;

    const elements = mainContent.querySelectorAll("h2[id], h3[id]");
    const found: Heading[] = [];
    elements.forEach((el) => {
      const htmlEl = el as HTMLElement;
      const id = htmlEl.id;
      const text = htmlEl.textContent || "";
      const level = parseInt(htmlEl.tagName.charAt(1), 10);
      if (id && text) {
        found.push({ id, text, level });
      }
    });
    setHeadings(found);
  }, []);

  // Set up MutationObserver to re-scan when DOM changes
  useEffect(() => {
    // Schedule initial scan after paint to avoid synchronous setState in effect
    rafRef.current = requestAnimationFrame(() => {
      scanHeadings();
    });

    // Re-scan when DOM changes (section switches)
    const mutationObserver = new MutationObserver(() => {
      // Small delay to let React render
      setTimeout(scanHeadings, 300);
    });

    const mainContent = document.querySelector("[data-section-content]");
    if (mainContent) {
      mutationObserver.observe(mainContent, {
        childList: true,
        subtree: true,
      });
    }

    return () => {
      mutationObserver.disconnect();
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, [scanHeadings]);

  // IntersectionObserver for tracking active heading
  useEffect(() => {
    if (headings.length === 0) return;

    // Clean up previous observer
    if (observerRef.current) {
      observerRef.current.disconnect();
    }

    const elements = headings
      .map((h) => document.getElementById(h.id))
      .filter(Boolean) as HTMLElement[];

    if (elements.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        // Find the topmost visible heading
        const visibleEntries = entries.filter((entry) => entry.isIntersecting);
        if (visibleEntries.length > 0) {
          // Pick the one closest to the top
          const topEntry = visibleEntries.reduce((closest, entry) => {
            if (!closest) return entry;
            return entry.boundingClientRect.top < closest.boundingClientRect.top
              ? entry
              : closest;
          }, visibleEntries[0]);
          setActiveId(topEntry.target.id);
        }
      },
      {
        root: null,
        rootMargin: "-80px 0px -60% 0px",
        threshold: 0.1,
      }
    );

    elements.forEach((el) => observer.observe(el));
    observerRef.current = observer;

    return () => {
      observer.disconnect();
    };
  }, [headings]);

  const scrollToHeading = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  // Don't render if no headings
  if (headings.length === 0) return null;

  return (
    <div className="hidden lg:block fixed right-6 top-1/2 -translate-y-1/2 z-30 w-[180px]">
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3, delay: 0.5 }}
        className="rounded-lg border border-border/30 bg-card/80 backdrop-blur-md shadow-lg shadow-black/10"
      >
        {/* Header */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-between px-3 py-2.5 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
        >
          <div className="flex items-center gap-1.5">
            <List className="w-3 h-3" />
            <span>On this page</span>
          </div>
          {collapsed ? (
            <ChevronRight className="w-3 h-3" />
          ) : (
            <ChevronDown className="w-3 h-3" />
          )}
        </button>

        {/* Heading list */}
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <nav className="px-2 pb-2.5 space-y-0.5 max-h-[50vh] overflow-y-auto">
                {headings.map((heading) => {
                  const isActive = activeId === heading.id;
                  const isH3 = heading.level === 3;

                  return (
                    <button
                      key={heading.id}
                      onClick={() => scrollToHeading(heading.id)}
                      className={`
                        w-full text-left text-[11px] leading-relaxed py-1 px-2 rounded transition-all duration-200
                        ${
                          isH3 ? "pl-5" : "pl-2"
                        }
                        ${
                          isActive
                            ? "text-emerald-400 bg-emerald-500/10 font-medium"
                            : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                        }
                      `}
                    >
                      <div className="flex items-center gap-1.5">
                        {isActive && (
                          <motion.div
                            layoutId="toc-active"
                            className="w-1 h-1 rounded-full bg-emerald-400 flex-shrink-0"
                            transition={{
                              type: "spring",
                              stiffness: 300,
                              damping: 30,
                            }}
                          />
                        )}
                        {!isActive && (
                          <div className="w-1 h-1 rounded-full bg-transparent flex-shrink-0" />
                        )}
                        <span className="truncate">{heading.text}</span>
                      </div>
                    </button>
                  );
                })}
              </nav>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
