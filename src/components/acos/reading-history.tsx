"use client";

import {
  useEffect,
  useCallback,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Clock, X, History } from "lucide-react";
import { navItems } from "@/components/acos/sidebar";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface HistoryEntry {
  id: string;
  visitedAt: number;
}

/* ------------------------------------------------------------------ */
/*  localStorage helpers                                               */
/* ------------------------------------------------------------------ */

const STORAGE_KEY = "acos-reading-history";
const VISITED_SECTIONS_KEY = "acos-visited-sections";
const MAX_HISTORY = 10;

function readHistory(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeHistory(history: HistoryEntry[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
  } catch {
    // Silently fail if localStorage is unavailable
  }
}

/* ------------------------------------------------------------------ */
/*  External store for cross-component reactivity                      */
/* ------------------------------------------------------------------ */

let listeners: Array<() => void> = [];
let cachedHistory: HistoryEntry[] | null = null;

function getSnapshot(): HistoryEntry[] {
  if (cachedHistory === null) {
    cachedHistory = readHistory();
  }
  return cachedHistory;
}

const EMPTY_HISTORY: HistoryEntry[] = [];

function getServerSnapshot(): HistoryEntry[] {
  return EMPTY_HISTORY;
}

function setHistoryState(newHistory: HistoryEntry[]) {
  cachedHistory = newHistory;
  writeHistory(newHistory);
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void): () => void {
  listeners = [...listeners, listener];
  return () => {
    listeners = listeners.filter((l) => l !== listener);
  };
}

/* ------------------------------------------------------------------ */
/*  Unique visited sections tracker (for achievement notifications)    */
/* ------------------------------------------------------------------ */

let visitedListeners: Array<() => void> = [];
let cachedVisited: string[] | null = null;

function readVisitedSections(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(VISITED_SECTIONS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeVisitedSections(sections: string[]) {
  try {
    localStorage.setItem(VISITED_SECTIONS_KEY, JSON.stringify(sections));
  } catch {
    // Silently fail
  }
}

function getVisitedSnapshot(): string[] {
  if (cachedVisited === null) {
    cachedVisited = readVisitedSections();
  }
  return cachedVisited;
}

const EMPTY_VISITED: string[] = [];

function getVisitedServerSnapshot(): string[] {
  return EMPTY_VISITED;
}

function setVisitedState(newVisited: string[]) {
  cachedVisited = newVisited;
  writeVisitedSections(newVisited);
  visitedListeners.forEach((l) => l());
}

function subscribeVisited(listener: () => void): () => void {
  visitedListeners = [...visitedListeners, listener];
  return () => {
    visitedListeners = visitedListeners.filter((l) => l !== listener);
  };
}

function addVisitedSection(sectionId: string): string[] {
  const current = getVisitedSnapshot();
  if (current.includes(sectionId)) return current;
  const updated = [...current, sectionId];
  setVisitedState(updated);
  return updated;
}

/* ------------------------------------------------------------------ */
/*  Hook: useVisitCount                                                */
/* ------------------------------------------------------------------ */

export function useVisitCount() {
  const visitedSections = useSyncExternalStore(
    subscribeVisited,
    getVisitedSnapshot,
    getVisitedServerSnapshot
  );

  return {
    visitCount: visitedSections.length,
    visitedSections,
    addVisitedSection,
  };
}

/* ------------------------------------------------------------------ */
/*  Relative time helper                                               */
/* ------------------------------------------------------------------ */

function formatRelativeTime(timestamp: number): string {
  const now = Date.now();
  const diffMs = now - timestamp;

  if (diffMs < 60 * 1000) return "just now";

  const diffMinutes = Math.floor(diffMs / (60 * 1000));
  if (diffMinutes < 60) return `${diffMinutes}m ago`;

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

/* ------------------------------------------------------------------ */
/*  Hook: useReadingHistory                                            */
/* ------------------------------------------------------------------ */

export function useReadingHistory() {
  const history = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const addToHistory = useCallback((sectionId: string) => {
    const current = getSnapshot();
    // Remove duplicate if exists
    const filtered = current.filter((entry) => entry.id !== sectionId);
    // Add to front with current timestamp
    const newEntry: HistoryEntry = { id: sectionId, visitedAt: Date.now() };
    // Keep only MAX_HISTORY entries
    const newHistory = [newEntry, ...filtered].slice(0, MAX_HISTORY);
    setHistoryState(newHistory);
  }, []);

  const clearHistory = useCallback(() => {
    setHistoryState([]);
  }, []);

  return { history, addToHistory, clearHistory };
}

/* ------------------------------------------------------------------ */
/*  Provider (listens for storage events from other tabs)              */
/* ------------------------------------------------------------------ */

export function ReadingHistoryProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    const handleStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) {
        cachedHistory = null; // Invalidate cache
        listeners.forEach((l) => l());
      }
    };
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  return <>{children}</>;
}

/* ------------------------------------------------------------------ */
/*  RecentSections — for Overview page                                 */
/* ------------------------------------------------------------------ */

export function RecentSections({
  onNavigate,
}: {
  onNavigate?: (sectionId: string) => void;
}) {
  const { history, clearHistory } = useReadingHistory();

  // Resolve history IDs to nav items
  const historyItems = history
    .map((entry) => {
      const navItem = navItems.find((n) => n.id === entry.id);
      return navItem ? { ...navItem, visitedAt: entry.visitedAt } : null;
    })
    .filter(Boolean) as (typeof navItems[number] & { visitedAt: number })[];

  if (historyItems.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.1 }}
      className="rounded-xl border border-teal-500/20 bg-gradient-to-r from-teal-900/10 to-emerald-900/10 backdrop-blur-sm"
    >
      <div className="px-5 py-4 border-b border-border/20">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-teal-400" />
            <h3 className="text-sm font-semibold text-foreground">
              Recently Visited
            </h3>
            <span className="text-[10px] font-mono text-muted-foreground bg-muted/30 px-1.5 py-0.5 rounded">
              {historyItems.length}
            </span>
          </div>
          <button
            onClick={clearHistory}
            className="text-[10px] text-muted-foreground hover:text-red-400 transition-colors duration-200 flex items-center gap-1"
            aria-label="Clear reading history"
          >
            <X className="w-3 h-3" />
            Clear
          </button>
        </div>
      </div>
      <div className="p-4">
        <div className="flex flex-wrap gap-2">
          <AnimatePresence>
            {historyItems.map((item) => (
              <motion.button
                key={item.id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ duration: 0.2 }}
                onClick={() => onNavigate?.(item.id)}
                className="group flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium
                  bg-teal-500/10 text-teal-400 border border-teal-500/20
                  hover:bg-teal-500/20 hover:border-teal-500/30 transition-all duration-200"
              >
                {item.icon}
                <span>{item.shortLabel}</span>
                <span className="text-[10px] text-muted-foreground ml-0.5">
                  {formatRelativeTime(item.visitedAt)}
                </span>
              </motion.button>
            ))}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/*  HistoryIndicator — small dot for sidebar nav items                 */
/* ------------------------------------------------------------------ */

export function HistoryIndicator({ sectionId }: { sectionId: string }) {
  const { history } = useReadingHistory();

  // Check if section was visited recently (within last 30 minutes)
  const recentEntry = history.find((entry) => entry.id === sectionId);
  if (!recentEntry) return null;

  const isRecent = Date.now() - recentEntry.visitedAt < 30 * 60 * 1000;
  if (!isRecent) return null;

  return (
    <motion.span
      initial={{ scale: 0 }}
      animate={{ scale: 1 }}
      className="w-1.5 h-1.5 rounded-full bg-teal-400 flex-shrink-0"
      title={`Visited ${formatRelativeTime(recentEntry.visitedAt)}`}
    />
  );
}
