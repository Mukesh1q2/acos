"use client";

import {
  useEffect,
  useCallback,
  useRef,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { motion, useInView } from "framer-motion";
import { CheckCircle2, Trophy } from "lucide-react";
import { navItems } from "@/components/acos/sidebar";
import { addNotification } from "@/components/acos/notification-center";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type CompletionMap = Record<string, boolean>;

/* ------------------------------------------------------------------ */
/*  localStorage helpers                                               */
/* ------------------------------------------------------------------ */

const STORAGE_KEY = "acos-section-completion";

function readCompletions(): CompletionMap {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)
      ? parsed
      : {};
  } catch {
    return {};
  }
}

function writeCompletions(completions: CompletionMap) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(completions));
  } catch {
    // Silently fail if localStorage is unavailable
  }
}

/* ------------------------------------------------------------------ */
/*  External store for cross-component reactivity                      */
/* ------------------------------------------------------------------ */

let listeners: Array<() => void> = [];
let cachedCompletions: CompletionMap | null = null;

function getSnapshot(): CompletionMap {
  if (cachedCompletions === null) {
    cachedCompletions = readCompletions();
  }
  return cachedCompletions;
}

const EMPTY_COMPLETIONS: CompletionMap = {};

function getServerSnapshot(): CompletionMap {
  return EMPTY_COMPLETIONS;
}

function setCompletionState(newCompletions: CompletionMap) {
  cachedCompletions = newCompletions;
  writeCompletions(newCompletions);
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void): () => void {
  listeners = [...listeners, listener];
  return () => {
    listeners = listeners.filter((l) => l !== listener);
  };
}

/* ------------------------------------------------------------------ */
/*  Achievement tracking (avoid duplicate notifications)               */
/* ------------------------------------------------------------------ */

const achievementFired = new Set<string>();

/* ------------------------------------------------------------------ */
/*  Public API: markCompleted                                          */
/* ------------------------------------------------------------------ */

function markCompleted(sectionId: string) {
  const current = getSnapshot();
  if (current[sectionId]) return; // Already completed

  const updated = { ...current, [sectionId]: true };
  setCompletionState(updated);

  // Count completed
  const count = Object.values(updated).filter(Boolean).length;
  const total = navItems.length;

  // Achievement: First section completed
  if (count === 1 && !achievementFired.has("first-read")) {
    achievementFired.add("first-read");
    const navItem = navItems.find((n) => n.id === sectionId);
    addNotification({
      type: "achievement",
      title: "First Read!",
      message: `You completed your first section${navItem ? `: ${navItem.shortLabel}` : ""}.`,
    });
  }

  // Achievement: 50% complete
  const halfMark = Math.ceil(total / 2);
  if (count === halfMark && !achievementFired.has("halfway")) {
    achievementFired.add("halfway");
    addNotification({
      type: "achievement",
      title: "Halfway There!",
      message: `You've read ${count} sections. Keep going!`,
    });
  }

  // Achievement: All complete
  if (count === total && !achievementFired.has("completionist")) {
    achievementFired.add("completionist");
    addNotification({
      type: "achievement",
      title: "Completionist!",
      message: `You've read all ${total} sections. Incredible!`,
    });
  }
}

/* ------------------------------------------------------------------ */
/*  Hook: useSectionCompletion                                         */
/* ------------------------------------------------------------------ */

export function useSectionCompletion() {
  const completions = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const isCompleted = useCallback(
    (sectionId: string) => !!completions[sectionId],
    [completions]
  );

  const completionCount = Object.values(completions).filter(Boolean).length;
  const totalSections = navItems.length;

  return {
    completions,
    markCompleted,
    isCompleted,
    completionCount,
    totalSections,
  };
}

/* ------------------------------------------------------------------ */
/*  Provider (listens for storage events from other tabs)              */
/* ------------------------------------------------------------------ */

export function SectionCompletionProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    const handleStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) {
        cachedCompletions = null; // Invalidate cache
        listeners.forEach((l) => l());
      }
    };
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  return <>{children}</>;
}

/* ------------------------------------------------------------------ */
/*  SectionCompletionIndicator — for sidebar nav items                 */
/* ------------------------------------------------------------------ */

export function SectionCompletionIndicator({ sectionId }: { sectionId: string }) {
  const { isCompleted } = useSectionCompletion();

  if (!isCompleted(sectionId)) return null;

  return (
    <motion.span
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: "spring", stiffness: 400, damping: 20 }}
      className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0"
      title="Section completed"
    />
  );
}

/* ------------------------------------------------------------------ */
/*  OverallCompletionBadge — for Overview section                      */
/* ------------------------------------------------------------------ */

export function OverallCompletionBadge() {
  const { completionCount, totalSections } = useSectionCompletion();
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true });
  const [animatedValue, setAnimatedValue] = useState(0);
  const prevAnimatedRef = useRef(0);

  const percent = totalSections > 0 ? (completionCount / totalSections) * 100 : 0;
  const hasAnimated = useRef(false);

  useEffect(() => {
    if (!isInView) return;
    if (hasAnimated.current && Math.abs(prevAnimatedRef.current - percent) < 0.5) return;

    const startTime = Date.now();
    const from = hasAnimated.current ? prevAnimatedRef.current : 0;
    const to = percent;
    const duration = 1200;

    const step = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = from + (to - from) * eased;
      prevAnimatedRef.current = current;
      setAnimatedValue(current);
      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        hasAnimated.current = true;
      }
    };
    requestAnimationFrame(step);
  }, [isInView, percent]);

  // SVG circle params
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (animatedValue / 100) * circumference;

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="rounded-xl border border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10 backdrop-blur-sm overflow-hidden"
    >
      <div className="px-5 py-4 border-b border-border/20">
        <div className="flex items-center gap-2">
          <Trophy className="w-4 h-4 text-emerald-400" />
          <h3 className="text-sm font-semibold text-foreground">
            Reading Progress
          </h3>
          <span className="text-[10px] font-mono text-muted-foreground bg-muted/30 px-1.5 py-0.5 rounded">
            {completionCount}/{totalSections}
          </span>
        </div>
      </div>
      <div className="p-5 flex items-center gap-6">
        {/* Circular progress ring */}
        <div className="relative w-28 h-28 flex-shrink-0">
          <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
            {/* Background ring */}
            <circle
              cx="50"
              cy="50"
              r={radius}
              fill="none"
              stroke="oklch(1 0 0 / 8%)"
              strokeWidth="5"
            />
            {/* Progress ring */}
            <circle
              cx="50"
              cy="50"
              r={radius}
              fill="none"
              stroke="oklch(0.696 0.17 162.48)"
              strokeWidth="5"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              style={{ transition: "stroke-dashoffset 0.05s ease-out" }}
            />
          </svg>
          {/* Center label */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-bold bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
              {completionCount}
            </span>
            <span className="text-[10px] text-muted-foreground font-mono">
              of {totalSections}
            </span>
          </div>
        </div>

        {/* Stats */}
        <div className="flex-1 space-y-3">
          <div>
            <div className="text-xs text-muted-foreground mb-1">Sections Completed</div>
            <div className="text-lg font-bold text-foreground">
              {completionCount} <span className="text-sm font-normal text-muted-foreground">sections</span>
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground mb-1">Completion Rate</div>
            <div className="text-lg font-bold text-emerald-400">
              {totalSections > 0 ? Math.round((completionCount / totalSections) * 100) : 0}%
            </div>
          </div>
          {/* Mini progress bar */}
          <div className="h-1.5 rounded-full bg-muted/30 overflow-hidden">
            <motion.div
              className="h-full rounded-full bg-gradient-to-r from-emerald-500 via-teal-400 to-emerald-400"
              initial={{ width: 0 }}
              animate={{ width: `${totalSections > 0 ? (completionCount / totalSections) * 100 : 0}%` }}
              transition={{ duration: 0.8, ease: "easeOut" }}
            />
          </div>
          {completionCount === totalSections && totalSections > 0 && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center gap-1.5 text-emerald-400"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span className="text-xs font-medium">All sections completed!</span>
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/*  useScrollCompletion — scroll detection hook                         */
/* ------------------------------------------------------------------ */

export function useScrollCompletion(
  contentRef: React.RefObject<HTMLDivElement | null>,
  activeSection: string
) {
  const { isCompleted, markCompleted: markDone } = useSectionCompletion();
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const el = contentRef.current;
    if (!el) return;

    const handleScroll = () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      debounceTimerRef.current = setTimeout(() => {
        const scrollTop = el.scrollTop;
        const scrollHeight = el.scrollHeight;
        const clientHeight = el.clientHeight;

        // Within 200px of bottom
        if (scrollHeight - scrollTop - clientHeight < 200) {
          if (!isCompleted(activeSection)) {
            markDone(activeSection);
          }
        }
      }, 300);
    };

    el.addEventListener("scroll", handleScroll, { passive: true });
    return () => {
      el.removeEventListener("scroll", handleScroll);
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [contentRef, activeSection, isCompleted, markDone]);
}
