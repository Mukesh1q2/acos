"use client";

import { useState, useEffect, useCallback, useSyncExternalStore, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { HelpCircle, ChevronRight, ChevronLeft, X } from "lucide-react";
import { Button } from "@/components/ui/button";

/* ------------------------------------------------------------------ */
/*  External Store for completion state (avoids hydration mismatch)     */
/* ------------------------------------------------------------------ */

const STORAGE_KEY = "acos-onboarding-complete";

let completionListeners: Array<() => void> = [];
let cachedCompletion: boolean | null = null;

function readCompletion(): boolean {
  if (typeof window === "undefined") return false;
  if (cachedCompletion === null) {
    cachedCompletion = localStorage.getItem(STORAGE_KEY) === "true";
  }
  return cachedCompletion;
}

function writeCompletion(value: boolean) {
  cachedCompletion = value;
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_KEY, String(value));
  }
  completionListeners.forEach((l) => l());
}

function subscribeCompletion(listener: () => void) {
  completionListeners.push(listener);
  return () => {
    completionListeners = completionListeners.filter((l) => l !== listener);
  };
}

function useCompletionSnapshot() {
  return readCompletion();
}

function getServerSnapshot() {
  return false;
}

/* ------------------------------------------------------------------ */
/*  Tour step definitions                                              */
/* ------------------------------------------------------------------ */

interface TourStep {
  target: string; // CSS selector
  title: string;
  description: string;
  position: "top" | "bottom" | "left" | "right" | "center";
}

const TOUR_STEPS: TourStep[] = [
  {
    target: "[data-tour='sidebar']",
    title: "Welcome to ACOS",
    description:
      "This sidebar is your main navigation hub. It lets you jump between all 16 sections of the ACOS analysis, from the Overview to the Glossary.",
    position: "right",
  },
  {
    target: "[data-tour='sidebar-nav']",
    title: "Explore Sections",
    description:
      "Each item here represents a deep-dive section. Click any section to navigate. Bookmarked sections show a star icon, and recently visited ones have a subtle indicator.",
    position: "right",
  },
  {
    target: "[data-tour='architecture-diagram']",
    title: "Interactive Architecture",
    description:
      "The ACOS Stack diagram is fully interactive. Hover over each layer to see details, and click to expand in-depth information about that component.",
    position: "bottom",
  },
  {
    target: "[data-tour='chat-fab']",
    title: "AI Assistant",
    description:
      "Click this button to open the AI Assistant panel. Ask any question about ACOS, AFM, HBTA, or the theorems and get instant answers.",
    position: "left",
  },
  {
    target: "[data-tour='command-palette-hint']",
    title: "Quick Navigation",
    description:
      "Press Ctrl+K (or Cmd+K on Mac) to open the Command Palette. Search for any section or content instantly without leaving your keyboard.",
    position: "bottom",
  },
  {
    target: "[data-tour='bookmark-progress']",
    title: "Bookmarks & Progress",
    description:
      "Use the bookmark button to save sections for quick access. The progress bar at the top shows your position across all sections, and the reading progress bar tracks your scroll within a section.",
    position: "bottom",
  },
];

/* ------------------------------------------------------------------ */
/*  useOnboarding hook                                                 */
/* ------------------------------------------------------------------ */

export function useOnboarding() {
  const isComplete = useSyncExternalStore(
    subscribeCompletion,
    useCompletionSnapshot,
    getServerSnapshot
  );

  const startTour = useCallback(() => {
    writeCompletion(false);
    // Dispatch custom event so the tour component opens
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("acos-start-tour"));
    }
  }, []);

  const resetTour = useCallback(() => {
    writeCompletion(false);
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("acos-start-tour"));
    }
  }, []);

  return { isComplete, startTour, resetTour };
}

/* ------------------------------------------------------------------ */
/*  Spotlight highlight component                                      */
/* ------------------------------------------------------------------ */

interface HighlightRect {
  top: number;
  left: number;
  width: number;
  height: number;
}

function getHighlightRect(selector: string): HighlightRect | null {
  const el = document.querySelector(selector);
  if (!el) return null;
  const rect = el.getBoundingClientRect();
  return {
    top: rect.top,
    left: rect.left,
    width: rect.width,
    height: rect.height,
  };
}

/* ------------------------------------------------------------------ */
/*  Tooltip card positioning logic                                     */
/* ------------------------------------------------------------------ */

function getTooltipPosition(
  highlightRect: HighlightRect | null,
  position: TourStep["position"],
  tooltipWidth: number,
  tooltipHeight: number
): { top: number; left: number } {
  if (!highlightRect) {
    return { top: window.innerHeight / 2 - tooltipHeight / 2, left: window.innerWidth / 2 - tooltipWidth / 2 };
  }

  const GAP = 16;
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  let top = 0;
  let left = 0;

  switch (position) {
    case "bottom":
      top = highlightRect.top + highlightRect.height + GAP;
      left = highlightRect.left + highlightRect.width / 2 - tooltipWidth / 2;
      break;
    case "top":
      top = highlightRect.top - tooltipHeight - GAP;
      left = highlightRect.left + highlightRect.width / 2 - tooltipWidth / 2;
      break;
    case "right":
      top = highlightRect.top + highlightRect.height / 2 - tooltipHeight / 2;
      left = highlightRect.left + highlightRect.width + GAP;
      break;
    case "left":
      top = highlightRect.top + highlightRect.height / 2 - tooltipHeight / 2;
      left = highlightRect.left - tooltipWidth - GAP;
      break;
    case "center":
      top = vh / 2 - tooltipHeight / 2;
      left = vw / 2 - tooltipWidth / 2;
      break;
  }

  // Clamp to viewport
  top = Math.max(12, Math.min(top, vh - tooltipHeight - 12));
  left = Math.max(12, Math.min(left, vw - tooltipWidth - 12));

  return { top, left };
}

/* ------------------------------------------------------------------ */
/*  Main OnboardingTour component                                      */
/* ------------------------------------------------------------------ */

export function OnboardingTour() {
  const [isOpen, setIsOpen] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [highlightRect, setHighlightRect] = useState<HighlightRect | null>(null);
  const [tooltipPos, setTooltipPos] = useState<{ top: number; left: number }>({ top: 0, left: 0 });
  const tooltipRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number>(0);

  // Listen for the custom event to start the tour
  useEffect(() => {
    const handleStart = () => {
      setCurrentStep(0);
      setIsOpen(true);
    };
    window.addEventListener("acos-start-tour", handleStart);
    return () => window.removeEventListener("acos-start-tour", handleStart);
  }, []);

  // Auto-start on first visit
  useEffect(() => {
    const timer = setTimeout(() => {
      if (!readCompletion()) {
        setCurrentStep(0);
        setIsOpen(true);
      }
    }, 1200);
    return () => clearTimeout(timer);
  }, []);

  // Update highlight position
  const updatePositions = useCallback(() => {
    if (!isOpen) return;
    const step = TOUR_STEPS[currentStep];
    const rect = getHighlightRect(step.target);
    setHighlightRect(rect);

    const tooltipEl = tooltipRef.current;
    const tw = tooltipEl?.offsetWidth || 320;
    const th = tooltipEl?.offsetHeight || 200;
    const pos = getTooltipPosition(rect, step.position, tw, th);
    setTooltipPos(pos);
  }, [isOpen, currentStep]);

  // Update positions when step changes or on resize
  useEffect(() => {
    requestAnimationFrame(() => updatePositions());
    const handleResize = () => updatePositions();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [updatePositions]);

  // Continuous position tracking with rAF while open
  useEffect(() => {
    if (!isOpen) return;
    const track = () => {
      updatePositions();
      rafRef.current = requestAnimationFrame(track);
    };
    rafRef.current = requestAnimationFrame(track);
    return () => cancelAnimationFrame(rafRef.current);
  }, [isOpen, updatePositions]);

  const closeTour = useCallback(() => {
    setIsOpen(false);
    writeCompletion(true);
  }, []);

  const goNext = useCallback(() => {
    if (currentStep < TOUR_STEPS.length - 1) {
      setCurrentStep((s) => s + 1);
    } else {
      closeTour();
    }
  }, [currentStep, closeTour]);

  const goBack = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep((s) => s - 1);
    }
  }, [currentStep]);

  const step = TOUR_STEPS[currentStep];
  const totalSteps = TOUR_STEPS.length;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Dark overlay with spotlight cutout */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="fixed inset-0 z-[9998]"
            style={{ pointerEvents: "auto" }}
          >
            {/* SVG overlay with spotlight hole */}
            <svg
              className="absolute inset-0 w-full h-full"
              style={{ pointerEvents: "none" }}
            >
              <defs>
                <mask id="tour-spotlight-mask">
                  <rect x="0" y="0" width="100%" height="100%" fill="white" />
                  {highlightRect && (
                    <rect
                      x={highlightRect.left - 6}
                      y={highlightRect.top - 6}
                      width={highlightRect.width + 12}
                      height={highlightRect.height + 12}
                      rx="8"
                      fill="black"
                    />
                  )}
                </mask>
              </defs>
              <rect
                x="0"
                y="0"
                width="100%"
                height="100%"
                fill="rgba(0,0,0,0.6)"
                mask="url(#tour-spotlight-mask)"
              />
            </svg>

            {/* Click on overlay (outside spotlight) does nothing - blocks interaction */}
            <div
              className="absolute inset-0"
              onClick={(e) => {
                // Only close if clicking directly on overlay, not on tooltip
                if (e.target === e.currentTarget) {
                  // Do nothing - user must use Skip button
                }
              }}
            />
          </motion.div>

          {/* Pulsing emerald ring around highlighted element */}
          {highlightRect && (
            <motion.div
              key={`ring-${currentStep}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="fixed z-[9999] pointer-events-none"
              style={{
                top: highlightRect.top - 6,
                left: highlightRect.left - 6,
                width: highlightRect.width + 12,
                height: highlightRect.height + 12,
                borderRadius: 8,
              }}
            >
              {/* Pulsing border */}
              <motion.div
                className="absolute inset-0 rounded-lg border-2 border-emerald-400"
                animate={{
                  opacity: [0.4, 1, 0.4],
                  boxShadow: [
                    "0 0 0 0 rgba(52,211,153,0)",
                    "0 0 0 6px rgba(52,211,153,0.3)",
                    "0 0 0 0 rgba(52,211,153,0)",
                  ],
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  ease: "easeInOut",
                }}
              />
            </motion.div>
          )}

          {/* Tooltip card */}
          <motion.div
            ref={tooltipRef}
            key={`tooltip-${currentStep}`}
            initial={{ opacity: 0, y: 8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.95 }}
            transition={{ duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="fixed z-[10000] w-[320px]"
            style={{
              top: tooltipPos.top,
              left: tooltipPos.left,
            }}
          >
            <div className="relative bg-slate-900 border border-emerald-500/30 rounded-xl shadow-2xl shadow-black/40 overflow-hidden">
              {/* Arrow pointer toward target */}
              {step.position === "bottom" && (
                <div className="absolute -top-2 left-1/2 -translate-x-1/2">
                  <div className="w-0 h-0 border-l-[8px] border-l-transparent border-r-[8px] border-r-transparent border-b-[8px] border-b-slate-900" />
                </div>
              )}
              {step.position === "top" && (
                <div className="absolute -bottom-2 left-1/2 -translate-x-1/2">
                  <div className="w-0 h-0 border-l-[8px] border-l-transparent border-r-[8px] border-r-transparent border-t-[8px] border-t-slate-900" />
                </div>
              )}
              {step.position === "left" && (
                <div className="absolute -right-2 top-1/2 -translate-y-1/2">
                  <div className="w-0 h-0 border-t-[8px] border-t-transparent border-b-[8px] border-b-transparent border-l-[8px] border-l-slate-900" />
                </div>
              )}
              {step.position === "right" && (
                <div className="absolute -left-2 top-1/2 -translate-y-1/2">
                  <div className="w-0 h-0 border-t-[8px] border-t-transparent border-b-[8px] border-b-transparent border-r-[8px] border-r-slate-900" />
                </div>
              )}

              {/* Header with step number */}
              <div className="flex items-center justify-between px-4 pt-4 pb-2">
                <div className="flex items-center gap-2">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-500 text-xs font-bold text-white">
                    {currentStep + 1}
                  </span>
                  <h3 className="text-sm font-semibold text-foreground">
                    {step.title}
                  </h3>
                </div>
                <button
                  onClick={closeTour}
                  className="text-muted-foreground hover:text-foreground transition-colors p-1 rounded-md hover:bg-muted/50"
                  aria-label="Skip tour"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Description */}
              <div className="px-4 pb-3">
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {step.description}
                </p>
              </div>

              {/* Progress dots */}
              <div className="flex items-center justify-center gap-1.5 pb-2">
                {Array.from({ length: totalSteps }).map((_, i) => (
                  <div
                    key={i}
                    className={`h-1.5 rounded-full transition-all duration-300 ${
                      i === currentStep
                        ? "w-4 bg-emerald-400"
                        : i < currentStep
                          ? "w-1.5 bg-emerald-600"
                          : "w-1.5 bg-slate-700"
                    }`}
                  />
                ))}
              </div>

              {/* Footer with navigation buttons */}
              <div className="flex items-center justify-between px-4 py-3 border-t border-border/20 bg-slate-950/50">
                <span className="text-[10px] text-muted-foreground font-mono">
                  {currentStep + 1}/{totalSteps}
                </span>
                <div className="flex items-center gap-2">
                  {currentStep > 0 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={goBack}
                      className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
                    >
                      <ChevronLeft className="w-3 h-3 mr-0.5" />
                      Back
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={closeTour}
                    className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
                  >
                    Skip
                  </Button>
                  <Button
                    size="sm"
                    onClick={goNext}
                    className="h-7 px-3 text-xs bg-emerald-600 hover:bg-emerald-500 text-white"
                  >
                    {currentStep === totalSteps - 1 ? "Finish" : "Next"}
                    {currentStep < totalSteps - 1 && (
                      <ChevronRight className="w-3 h-3 ml-0.5" />
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

/* ------------------------------------------------------------------ */
/*  Help button for sidebar                                            */
/* ------------------------------------------------------------------ */

export function TourHelpButton() {
  const { startTour } = useOnboarding();

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={startTour}
      className="w-full justify-start gap-2 text-muted-foreground hover:text-foreground"
    >
      <HelpCircle className="w-4 h-4" />
      <span className="text-xs">Help Tour</span>
    </Button>
  );
}
