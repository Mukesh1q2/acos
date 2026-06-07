"use client";

import {
  useEffect,
  useCallback,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ListTodo, X, ListX } from "lucide-react";
import { navItems } from "@/components/acos/sidebar";
import { toast } from "sonner";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface ReadingListItem {
  sectionId: string;
  addedAt: number;
  note?: string;
}

/* ------------------------------------------------------------------ */
/*  localStorage helpers                                               */
/* ------------------------------------------------------------------ */

const STORAGE_KEY = "acos-reading-list";

function readList(): ReadingListItem[] {
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

function writeList(list: ReadingListItem[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  } catch {
    // Silently fail if localStorage is unavailable
  }
}

/* ------------------------------------------------------------------ */
/*  External store for cross-component reactivity                      */
/* ------------------------------------------------------------------ */

let listeners: Array<() => void> = [];
let cachedList: ReadingListItem[] | null = null;

function getSnapshot(): ReadingListItem[] {
  if (cachedList === null) {
    cachedList = readList();
  }
  return cachedList;
}

const EMPTY_LIST: ReadingListItem[] = [];

function getServerSnapshot(): ReadingListItem[] {
  return EMPTY_LIST;
}

function setListState(newList: ReadingListItem[]) {
  cachedList = newList;
  writeList(newList);
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void): () => void {
  listeners = [...listeners, listener];
  return () => {
    listeners = listeners.filter((l) => l !== listener);
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
/*  Hook: useReadingList                                               */
/* ------------------------------------------------------------------ */

export function useReadingList() {
  const readingList = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const addToList = useCallback((sectionId: string, note?: string) => {
    const current = getSnapshot();
    // Do not add duplicates
    if (current.some((item) => item.sectionId === sectionId)) return;
    const newItem: ReadingListItem = {
      sectionId,
      addedAt: Date.now(),
      ...(note ? { note } : {}),
    };
    setListState([newItem, ...current]);
  }, []);

  const removeFromList = useCallback((sectionId: string) => {
    const current = getSnapshot();
    setListState(current.filter((item) => item.sectionId !== sectionId));
  }, []);

  const isInList = useCallback(
    (sectionId: string) => readingList.some((item) => item.sectionId === sectionId),
    [readingList]
  );

  const clearList = useCallback(() => {
    setListState([]);
  }, []);

  // Sorted by addedAt descending (newest first)
  const sortedList = [...readingList].sort((a, b) => b.addedAt - a.addedAt);

  return { readingList: sortedList, addToList, removeFromList, isInList, clearList };
}

/* ------------------------------------------------------------------ */
/*  Provider (listens for storage events from other tabs)              */
/* ------------------------------------------------------------------ */

export function ReadingListProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    const handleStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) {
        cachedList = null; // Invalidate cache
        listeners.forEach((l) => l());
      }
    };
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  return <>{children}</>;
}

/* ------------------------------------------------------------------ */
/*  ReadingListButton — for breadcrumb area (next to BookmarkButton)   */
/* ------------------------------------------------------------------ */

export function ReadingListButton({ sectionId }: { sectionId: string }) {
  const { isInList, addToList, removeFromList } = useReadingList();
  const inList = isInList(sectionId);

  const handleClick = () => {
    if (inList) {
      removeFromList(sectionId);
    } else {
      const navItem = navItems.find((n) => n.id === sectionId);
      addToList(sectionId);
      toast.success(`Added "${navItem?.shortLabel ?? sectionId}" to reading list`);
    }
  };

  return (
    <motion.button
      onClick={handleClick}
      className={`
        flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium
        transition-all duration-200 border
        ${
          inList
            ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20"
            : "bg-muted/30 text-muted-foreground border-border/30 hover:text-foreground hover:bg-muted/50"
        }
      `}
      whileTap={{ scale: 0.95 }}
      aria-label={inList ? "Remove from reading list" : "Add to reading list"}
    >
      <ListTodo
        className={`w-3.5 h-3.5 transition-all duration-200 ${
          inList ? "text-emerald-400" : ""
        }`}
      />
      <span>{inList ? "In List" : "Read Later"}</span>
    </motion.button>
  );
}

/* ------------------------------------------------------------------ */
/*  ReadingListPanel — for Overview page                                */
/* ------------------------------------------------------------------ */

export function ReadingListPanel({
  onNavigate,
}: {
  onNavigate?: (sectionId: string) => void;
}) {
  const { readingList, removeFromList, clearList } = useReadingList();

  // Resolve list IDs to nav items
  const listItems = readingList
    .map((entry) => {
      const navItem = navItems.find((n) => n.id === entry.sectionId);
      return navItem
        ? { ...navItem, addedAt: entry.addedAt, note: entry.note }
        : null;
    })
    .filter(Boolean) as (typeof navItems[number] & { addedAt: number; note?: string })[];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.2 }}
      className="rounded-xl border border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-cyan-900/10 backdrop-blur-sm"
    >
      <div className="px-5 py-4 border-b border-border/20">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ListTodo className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-semibold text-foreground">
              Reading List
            </h3>
            {listItems.length > 0 && (
              <span className="text-[10px] font-mono text-muted-foreground bg-muted/30 px-1.5 py-0.5 rounded">
                {listItems.length}
              </span>
            )}
          </div>
          {listItems.length > 0 && (
            <button
              onClick={clearList}
              className="text-[10px] text-muted-foreground hover:text-red-400 transition-colors duration-200 flex items-center gap-1"
              aria-label="Clear reading list"
            >
              <ListX className="w-3 h-3" />
              Clear All
            </button>
          )}
        </div>
      </div>
      <div className="p-4">
        {listItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <ListTodo className="w-8 h-8 text-muted-foreground/30 mb-3" />
            <p className="text-xs text-muted-foreground max-w-[240px]">
              No items in your reading list. Add sections to read later.
            </p>
          </div>
        ) : (
          <div className="space-y-1.5 max-h-64 overflow-y-auto">
            <AnimatePresence>
              {listItems.map((item) => (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }}
                  transition={{ duration: 0.2 }}
                  className="group flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-muted/20 transition-colors cursor-pointer"
                  onClick={() => onNavigate?.(item.id)}
                >
                  <span className="text-muted-foreground flex-shrink-0">
                    {item.icon}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-foreground truncate">
                        {item.shortLabel}
                      </span>
                      <span className="text-[10px] text-muted-foreground flex-shrink-0">
                        {formatRelativeTime(item.addedAt)}
                      </span>
                    </div>
                    {item.note && (
                      <p className="text-[10px] text-muted-foreground truncate mt-0.5">
                        {item.note}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFromList(item.id);
                    }}
                    className="flex-shrink-0 w-5 h-5 rounded flex items-center justify-center
                      opacity-0 group-hover:opacity-100 transition-opacity duration-200
                      hover:bg-red-500/20 text-muted-foreground hover:text-red-400"
                    aria-label={`Remove ${item.shortLabel} from reading list`}
                  >
                    <X className="w-3 h-3" />
                  </button>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </motion.div>
  );
}
