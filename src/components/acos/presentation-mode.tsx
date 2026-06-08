"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight, X, Clock, Monitor } from "lucide-react";
import { navItems } from "@/components/acos/sidebar";

/* ------------------------------------------------------------------ */
/*  Presentation Controls — Floating bottom bar                       */
/* ------------------------------------------------------------------ */

interface PresentationControlsProps {
  activeSection: string;
  onSectionChange: (id: string) => void;
  onExit: () => void;
  totalSections: number;
}

function PresentationControls({
  activeSection,
  onSectionChange,
  onExit,
  totalSections,
}: PresentationControlsProps) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Timer
  useEffect(() => {
    timerRef.current = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const currentIndex = navItems.findIndex((n) => n.id === activeSection);
  const currentNav = navItems.find((n) => n.id === activeSection);
  const canGoPrev = currentIndex > 0;
  const canGoNext = currentIndex < navItems.length - 1;

  const goPrev = useCallback(() => {
    if (canGoPrev) onSectionChange(navItems[currentIndex - 1].id);
  }, [canGoPrev, currentIndex, onSectionChange]);

  const goNext = useCallback(() => {
    if (canGoNext) onSectionChange(navItems[currentIndex + 1].id);
  }, [canGoNext, currentIndex, onSectionChange]);

  // Arrow key handlers within controls
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        goPrev();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        goNext();
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [goPrev, goNext]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 40 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[100] flex items-center gap-3 px-4 py-3 rounded-2xl bg-card/90 backdrop-blur-xl border border-border/40 shadow-2xl shadow-black/30"
    >
      {/* Previous */}
      <button
        onClick={goPrev}
        disabled={!canGoPrev}
        className="w-9 h-9 rounded-lg flex items-center justify-center transition-colors duration-200 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-emerald-600/20 text-foreground"
        aria-label="Previous section"
      >
        <ChevronLeft className="w-5 h-5" />
      </button>

      {/* Section info */}
      <div className="flex flex-col items-center min-w-[120px] max-w-[200px]">
        <span className="text-sm font-medium text-foreground truncate w-full text-center">
          {currentNav?.shortLabel ?? "Overview"}
        </span>
        <span className="text-xs text-muted-foreground font-mono">
          {currentIndex + 1}/{totalSections}
        </span>
      </div>

      {/* Next */}
      <button
        onClick={goNext}
        disabled={!canGoNext}
        className="w-9 h-9 rounded-lg flex items-center justify-center transition-colors duration-200 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-emerald-600/20 text-foreground"
        aria-label="Next section"
      >
        <ChevronRight className="w-5 h-5" />
      </button>

      {/* Divider */}
      <div className="w-px h-6 bg-border/30" />

      {/* Timer */}
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-mono">
        <Clock className="w-3.5 h-3.5 text-emerald-400" />
        <span>{formatTime(elapsedSeconds)}</span>
      </div>

      {/* Divider */}
      <div className="w-px h-6 bg-border/30" />

      {/* Exit */}
      <button
        onClick={onExit}
        className="w-9 h-9 rounded-lg flex items-center justify-center transition-colors duration-200 hover:bg-red-500/20 text-muted-foreground hover:text-red-400"
        aria-label="Exit presentation mode"
      >
        <X className="w-4 h-4" />
      </button>
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/*  Presentation Toggle Button — for breadcrumb area                  */
/* ------------------------------------------------------------------ */

interface PresentationToggleButtonProps {
  onToggle: () => void;
}

export function PresentationToggleButton({ onToggle }: PresentationToggleButtonProps) {
  return (
    <button
      onClick={onToggle}
      className="w-7 h-7 rounded-md flex items-center justify-center text-muted-foreground hover:text-emerald-400 hover:bg-emerald-600/10 transition-colors duration-200"
      aria-label="Toggle presentation mode"
      title="Presentation mode (P)"
    >
      <Monitor className="w-3.5 h-3.5" />
    </button>
  );
}

/* ------------------------------------------------------------------ */
/*  Main PresentationMode Wrapper                                     */
/* ------------------------------------------------------------------ */

interface PresentationModeProps {
  isActive: boolean;
  onExit: () => void;
  activeSection: string;
  onSectionChange: (id: string) => void;
}

export function PresentationMode({
  isActive,
  onExit,
  activeSection,
  onSectionChange,
}: PresentationModeProps) {
  return (
    <AnimatePresence>
      {isActive && (
        <PresentationControls
          activeSection={activeSection}
          onSectionChange={onSectionChange}
          onExit={onExit}
          totalSections={navItems.length}
        />
      )}
    </AnimatePresence>
  );
}
