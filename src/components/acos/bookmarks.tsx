"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bookmark, Star, X } from "lucide-react";
import { navItems } from "@/components/acos/sidebar";

/* ------------------------------------------------------------------ */
/*  localStorage helpers                                               */
/* ------------------------------------------------------------------ */

const STORAGE_KEY = "acos-bookmarks";

function readBookmarks(): string[] {
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

function writeBookmarks(bookmarks: string[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(bookmarks));
  } catch {
    // Silently fail if localStorage is unavailable
  }
}

/* ------------------------------------------------------------------ */
/*  External store for cross-component reactivity                      */
/* ------------------------------------------------------------------ */

let listeners: Array<() => void> = [];
let cachedBookmarks: string[] | null = null;

function getSnapshot(): string[] {
  if (cachedBookmarks === null) {
    cachedBookmarks = readBookmarks();
  }
  return cachedBookmarks;
}

const EMPTY_BOOKMARKS: string[] = [];

function getServerSnapshot(): string[] {
  return EMPTY_BOOKMARKS;
}

function setBookmarksState(newBookmarks: string[]) {
  cachedBookmarks = newBookmarks;
  writeBookmarks(newBookmarks);
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void): () => void {
  listeners = [...listeners, listener];
  return () => {
    listeners = listeners.filter((l) => l !== listener);
  };
}

/* ------------------------------------------------------------------ */
/*  Hook: useBookmarks                                                 */
/* ------------------------------------------------------------------ */

export function useBookmarks() {
  const bookmarks = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const isBookmarked = useCallback(
    (sectionId: string) => bookmarks.includes(sectionId),
    [bookmarks]
  );

  const toggleBookmark = useCallback((sectionId: string) => {
    const current = getSnapshot();
    if (current.includes(sectionId)) {
      setBookmarksState(current.filter((id) => id !== sectionId));
    } else {
      setBookmarksState([...current, sectionId]);
    }
  }, []);

  return { bookmarks, isBookmarked, toggleBookmark };
}

/* ------------------------------------------------------------------ */
/*  Provider (listens for storage events from other tabs)              */
/* ------------------------------------------------------------------ */

export function BookmarksProvider({ children }: { children: ReactNode }) {
  // Listen for storage events from other tabs/windows
  useEffect(() => {
    const handleStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) {
        cachedBookmarks = null; // Invalidate cache
        listeners.forEach((l) => l());
      }
    };
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  return <>{children}</>;
}

/* ------------------------------------------------------------------ */
/*  BookmarkButton — for breadcrumb area                               */
/* ------------------------------------------------------------------ */

export function BookmarkButton({ sectionId }: { sectionId: string }) {
  const { isBookmarked, toggleBookmark } = useBookmarks();
  const bookmarked = isBookmarked(sectionId);

  return (
    <motion.button
      onClick={() => toggleBookmark(sectionId)}
      className={`
        flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium
        transition-all duration-200 border
        ${
          bookmarked
            ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20"
            : "bg-muted/30 text-muted-foreground border-border/30 hover:text-foreground hover:bg-muted/50"
        }
      `}
      whileTap={{ scale: 0.95 }}
      aria-label={bookmarked ? "Remove bookmark" : "Add bookmark"}
    >
      <Bookmark
        className={`w-3.5 h-3.5 transition-all duration-200 ${
          bookmarked ? "fill-emerald-400 text-emerald-400" : "fill-none"
        }`}
      />
      <span>{bookmarked ? "Bookmarked" : "Bookmark"}</span>
    </motion.button>
  );
}

/* ------------------------------------------------------------------ */
/*  BookmarkedSections — for Overview page                             */
/* ------------------------------------------------------------------ */

export function BookmarkedSections({
  onNavigate,
}: {
  onNavigate?: (sectionId: string) => void;
}) {
  const { bookmarks, toggleBookmark } = useBookmarks();

  // Resolve bookmark IDs to nav items
  const bookmarkedItems = bookmarks
    .map((id) => navItems.find((n) => n.id === id))
    .filter(Boolean) as (typeof navItems)[number][];

  if (bookmarkedItems.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="rounded-xl border border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10 backdrop-blur-sm"
    >
      <div className="px-5 py-4 border-b border-border/20">
        <div className="flex items-center gap-2">
          <Star className="w-4 h-4 text-emerald-400 fill-emerald-400" />
          <h3 className="text-sm font-semibold text-foreground">
            Bookmarked Sections
          </h3>
          <span className="text-[10px] font-mono text-muted-foreground bg-muted/30 px-1.5 py-0.5 rounded">
            {bookmarkedItems.length}
          </span>
        </div>
      </div>
      <div className="p-4">
        <div className="flex flex-wrap gap-2">
          <AnimatePresence>
            {bookmarkedItems.map((item) => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ duration: 0.2 }}
                className="group relative flex items-center gap-1.5"
              >
                <button
                  onClick={() => onNavigate?.(item.id)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium
                    bg-emerald-500/10 text-emerald-400 border border-emerald-500/20
                    hover:bg-emerald-500/20 hover:border-emerald-500/30 transition-all duration-200"
                >
                  {item.icon}
                  <span>{item.shortLabel}</span>
                </button>
                <button
                  onClick={() => toggleBookmark(item.id)}
                  className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-card border border-border/40
                    flex items-center justify-center opacity-0 group-hover:opacity-100
                    transition-opacity duration-200 hover:bg-red-500/20 hover:border-red-500/30"
                  aria-label={`Remove bookmark for ${item.shortLabel}`}
                >
                  <X className="w-2.5 h-2.5 text-muted-foreground" />
                </button>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
}
