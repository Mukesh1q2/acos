"use client";

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { navItems } from "@/components/acos/sidebar";
import {
  Search,
  Clock,
  X,
  Command,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Section Search Index: section IDs -> key terms / concepts          */
/* ------------------------------------------------------------------ */

const sectionSearchIndex: Record<string, string[]> = {
  overview: [
    "attention",
    "memory",
    "orthogonal",
    "cognitive",
    "innovation",
    "speedup",
    "retention",
    "interference",
    "ACOS",
    "stack",
    "architecture",
  ],
  part1: [
    "whitepaper",
    "HBTA",
    "complexity",
    "theorem",
    "proven",
    "plausible",
    "mathematical",
    "foundations",
    "approximation",
    "crossover",
  ],
  part2: [
    "ACOS",
    "cognitive kernel",
    "meta-controller",
    "OTM",
    "scheduler",
    "Lyapunov",
    "knowledge fabric",
    "memory consolidation",
  ],
  part3: [
    "AFM",
    "Mamba",
    "SSM",
    "backbone",
    "NSK",
    "LoRA",
    "adapter",
    "foundation model",
    "Stiefel",
  ],
  part4: [
    "training",
    "Path C",
    "ACOS first",
    "AFM later",
    "curriculum",
    "schedule",
    "hardware",
    "GPU",
  ],
  part5: [
    "continuous learning",
    "orthogonal projection",
    "gradient",
    "catastrophic forgetting",
    "replay",
    "consolidation",
  ],
  part6: [
    "orchestration",
    "routing",
    "Pingala",
    "local cloud",
    "model selection",
    "cost optimization",
  ],
  part7: [
    "multimodal",
    "vision",
    "audio",
    "text",
    "embedding",
    "capability matrix",
  ],
  part8: [
    "self-evolution",
    "prompt evolution",
    "reflection",
    "critique",
    "agent",
    "speculation",
  ],
  part9: [
    "market",
    "competitor",
    "patent",
    "open source",
    "GTM",
    "commercialization",
    "pricing",
  ],
  part10: [
    "attack",
    "risk",
    "adversarial",
    "security",
    "privacy",
    "threat model",
  ],
  part11: [
    "master plan",
    "MVP",
    "milestone",
    "roadmap",
    "beta",
    "launch",
    "6-month",
  ],
  roadmap: [
    "timeline",
    "milestone",
    "M1",
    "M2",
    "M3",
    "M4",
    "M5",
    "M6",
    "deliverable",
  ],
  theorems: [
    "theorem",
    "proof",
    "HBTA complexity",
    "Cayley retraction",
    "Lyapunov stability",
    "bounded convergence",
    "approximation error",
    "zero interference",
  ],
  performance: [
    "benchmark",
    "comparison",
    "attention scaling",
    "thread isolation",
    "memory efficiency",
    "learning stability",
    "chart",
  ],
  glossary: [
    "glossary",
    "definition",
    "HBTA",
    "OTM",
    "NSK",
    "Pingala",
    "Panini",
    "Nyaya",
    "Stiefel",
  ],
};

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface ContentMatch {
  sectionId: string;
  keyword: string;
}

interface CommandPaletteProps {
  onSectionChange: (id: string) => void;
}

/* ------------------------------------------------------------------ */
/*  Recent Searches Helpers                                            */
/* ------------------------------------------------------------------ */

const RECENT_KEY = "acos-recent-searches";
const MAX_RECENT = 5;

function getRecentSearches(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((v): v is string => typeof v === "string").slice(0, MAX_RECENT);
  } catch {
    return [];
  }
}

function addRecentSearch(query: string): void {
  if (!query.trim()) return;
  try {
    const current = getRecentSearches();
    const filtered = current.filter((s) => s.toLowerCase() !== query.toLowerCase());
    const updated = [query, ...filtered].slice(0, MAX_RECENT);
    localStorage.setItem(RECENT_KEY, JSON.stringify(updated));
  } catch {
    // silently ignore storage errors
  }
}

function clearRecentSearches(): void {
  try {
    localStorage.removeItem(RECENT_KEY);
  } catch {
    // silently ignore
  }
}

/* ------------------------------------------------------------------ */
/*  Command Palette Component                                          */
/* ------------------------------------------------------------------ */

export function CommandPalette({ onSectionChange }: CommandPaletteProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const inputRefRef = useRef<HTMLInputElement | null>(null);

  // Load recent searches on mount and when dialog opens
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  // Sync recent searches when dialog opens
  useEffect(() => {
    if (open) {
      queueMicrotask(() => {
        setRecentSearches(getRecentSearches());
        setQuery("");
      });
    }
  }, [open]);

  const runCommand = useCallback(
    (command: () => void) => {
      setOpen(false);
      command();
    },
    []
  );

  const handleSelect = useCallback(
    (sectionId: string, searchQuery?: string) => {
      if (searchQuery && searchQuery.trim()) {
        addRecentSearch(searchQuery.trim());
      }
      runCommand(() => onSectionChange(sectionId));
    },
    [onSectionChange, runCommand]
  );

  const removeRecentSearch = useCallback((term: string) => {
    const current = getRecentSearches();
    const updated = current.filter((s) => s !== term);
    try {
      localStorage.setItem(RECENT_KEY, JSON.stringify(updated));
    } catch {
      // silently ignore
    }
    setRecentSearches(updated);
  }, []);

  const handleClearRecent = useCallback(() => {
    clearRecentSearches();
    setRecentSearches([]);
  }, []);

  // ---- Search logic ----

  // Fuzzy match: case-insensitive partial match
  const fuzzyMatch = useCallback(
    (text: string, q: string): boolean => {
      return text.toLowerCase().includes(q.toLowerCase());
    },
    []
  );

  // Filter nav items by query (match on label or shortLabel)
  const filteredNavItems = useMemo(() => {
    if (!query.trim()) return navItems;
    const q = query.trim().toLowerCase();
    return navItems.filter(
      (item) =>
        item.label.toLowerCase().includes(q) ||
        item.shortLabel.toLowerCase().includes(q)
    );
  }, [query]);

  // Search content keywords when query is at least 1 character
  const contentMatches: ContentMatch[] = useMemo(() => {
    if (!query.trim()) return [];
    const q = query.trim().toLowerCase();
    const matches: ContentMatch[] = [];

    for (const [sectionId, keywords] of Object.entries(sectionSearchIndex)) {
      for (const keyword of keywords) {
        if (fuzzyMatch(keyword, q)) {
          matches.push({ sectionId, keyword });
        }
      }
    }

    // Deduplicate: same section+keyword combo
    const seen = new Set<string>();
    return matches.filter((m) => {
      const key = `${m.sectionId}::${m.keyword}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [query, fuzzyMatch]);

  // Group content matches by section
  const matchesBySection = useMemo(() => {
    const grouped: Record<string, ContentMatch[]> = {};
    for (const match of contentMatches) {
      if (!grouped[match.sectionId]) {
        grouped[match.sectionId] = [];
      }
      grouped[match.sectionId].push(match);
    }
    return grouped;
  }, [contentMatches]);

  // Highlight matched text within a phrase/keyword
  const highlightMatch = useCallback(
    (text: string) => {
      if (!query.trim()) return text;
      const lowerText = text.toLowerCase();
      const lowerQuery = query.trim().toLowerCase();
      const index = lowerText.indexOf(lowerQuery);
      if (index === -1) return text;

      return (
        <>
          {text.slice(0, index)}
          <span className="text-emerald-400 font-semibold">
            {text.slice(index, index + query.trim().length)}
          </span>
          {text.slice(index + query.trim().length)}
        </>
      );
    },
    [query]
  );

  const hasQuery = query.trim().length > 0;
  const hasContentResults = contentMatches.length > 0;
  const hasRecentSearches = recentSearches.length > 0 && !hasQuery;

  // Get the icon for a nav item by id
  const getNavIcon = useCallback(
    (sectionId: string) => {
      const item = navItems.find((n) => n.id === sectionId);
      return item?.icon ?? <Search className="w-4 h-4" />;
    },
    []
  );

  // Detect macOS
  const isMac = typeof navigator !== "undefined" && /Mac|iPod|iPhone|iPad/.test(navigator.userAgent);
  const modKey = isMac ? "Cmd" : "Ctrl";

  return (
    <CommandDialog
      open={open}
      onOpenChange={setOpen}
      title="Search ACOS"
      description="Search sections and content across the ACOS documentation"
    >
      {/* Custom header with Search badge and keyboard hint */}
      <div className="flex items-center justify-between px-4 pt-3 pb-1">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 rounded-md bg-emerald-600/20 px-2 py-0.5 text-[11px] font-semibold text-emerald-400 border border-emerald-500/30">
            <Search className="w-3 h-3" />
            Search
          </span>
          <span className="text-xs text-muted-foreground">ACOS Documentation</span>
        </div>
        <span className="text-[10px] text-muted-foreground/60 font-mono flex items-center gap-1">
          <Command className="w-3 h-3" />
          K
        </span>
      </div>

      <CommandInput
        placeholder={`Search sections, keywords, concepts... (${modKey}+K)`}
        value={query}
        onValueChange={setQuery}
      />
      <CommandList className="max-h-[400px]">
        <CommandEmpty>No results found.</CommandEmpty>

        {/* Recent searches when input is empty */}
        {hasRecentSearches && (
          <CommandGroup heading="Recent Searches">
            <div className="flex flex-wrap gap-1.5 px-2 py-2">
              {recentSearches.map((term) => (
                <button
                  key={term}
                  onClick={() => {
                    setQuery(term);
                    // Focus the input after setting query
                    setTimeout(() => {
                      const input = document.querySelector<HTMLInputElement>(
                        '[data-slot="command-input"]'
                      );
                      input?.focus();
                    }, 0);
                  }}
                  className="group inline-flex items-center gap-1 rounded-full bg-slate-800/80 border border-slate-700/50 px-2.5 py-1 text-xs text-slate-300 hover:bg-emerald-600/20 hover:border-emerald-500/40 hover:text-emerald-300 transition-all duration-150"
                >
                  <Clock className="w-3 h-3 opacity-50" />
                  <span>{term}</span>
                  <span
                    role="button"
                    tabIndex={0}
                    onClick={(e) => {
                      e.stopPropagation();
                      removeRecentSearch(term);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.stopPropagation();
                        removeRecentSearch(term);
                      }
                    }}
                    className="ml-0.5 opacity-0 group-hover:opacity-100 transition-opacity hover:text-red-400"
                  >
                    <X className="w-3 h-3" />
                  </span>
                </button>
              ))}
              <button
                onClick={handleClearRecent}
                className="inline-flex items-center gap-1 rounded-full px-2 py-1 text-[10px] text-muted-foreground/60 hover:text-red-400 transition-colors"
              >
                Clear all
              </button>
            </div>
          </CommandGroup>
        )}

        {/* Section results */}
        <CommandGroup heading="Sections">
          {filteredNavItems.map((item) => (
            <CommandItem
              key={item.id}
              onSelect={() => handleSelect(item.id, query)}
              className="flex items-center gap-2 group"
            >
              <span className="flex-shrink-0 text-muted-foreground group-data-[selected=true]:text-emerald-400 transition-colors">
                {item.icon}
              </span>
              <span className="text-sm">
                {hasQuery ? highlightMatch(item.label) : item.label}
              </span>
              <span className="ml-auto text-[10px] text-muted-foreground/50 font-mono">
                {navItems.indexOf(item) + 1 <= 9
                  ? `${navItems.indexOf(item) + 1}`
                  : ""}
              </span>
            </CommandItem>
          ))}
        </CommandGroup>

        {/* Content keyword search results */}
        {hasQuery && hasContentResults && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Content">
              {Object.entries(matchesBySection).map(
                ([sectionId, matches]) => {
                  const navItem = navItems.find((n) => n.id === sectionId);
                  if (!navItem) return null;

                  return matches.map((match, idx) => (
                    <CommandItem
                      key={`${sectionId}-content-${idx}`}
                      onSelect={() => handleSelect(sectionId, query)}
                      className="flex items-center gap-2 pl-4 group"
                    >
                      <Search className="w-3.5 h-3.5 text-emerald-400/70 flex-shrink-0 group-data-[selected=true]:text-emerald-400 transition-colors" />
                      <span className="text-sm">
                        {highlightMatch(match.keyword)}
                      </span>
                      <span className="ml-auto flex items-center gap-1.5">
                        <span className="text-[10px] text-muted-foreground/50">
                          in
                        </span>
                        <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400/70 font-medium">
                          <span className="flex-shrink-0 scale-75">
                            {navItem.icon}
                          </span>
                          {navItem.shortLabel}
                        </span>
                      </span>
                    </CommandItem>
                  ));
                }
              )}
            </CommandGroup>
          </>
        )}

        {/* Keyboard shortcuts group */}
        <CommandSeparator />
        <CommandGroup heading="Keyboard Shortcuts">
          <CommandItem disabled>
            <Search className="w-4 h-4" />
            <span>Toggle Command Palette</span>
            <span className="ml-auto text-xs text-muted-foreground font-mono">
              {modKey}+K
            </span>
          </CommandItem>
          <CommandItem disabled>
            <span className="w-4 h-4 flex items-center justify-center text-[10px] text-muted-foreground font-mono">
              ↑↓
            </span>
            <span>Navigate results</span>
            <span className="ml-auto text-xs text-muted-foreground font-mono">
              Arrow Keys
            </span>
          </CommandItem>
          <CommandItem disabled>
            <span className="w-4 h-4 flex items-center justify-center text-[10px] text-muted-foreground font-mono">
              ↵
            </span>
            <span>Select result</span>
            <span className="ml-auto text-xs text-muted-foreground font-mono">
              Enter
            </span>
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
