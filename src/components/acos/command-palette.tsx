"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
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
import { Brain, Keyboard, Search } from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Content index: section IDs -> key phrases / content snippets       */
/* ------------------------------------------------------------------ */

const contentIndex: Record<string, string[]> = {
  overview: [
    "ACOS Cognitive Stack Architecture",
    "Orthogonal Thread Memory",
    "Hierarchical Binary Tree Attention",
    "Neuro-Symbolic Kernel",
    "77x Attention Speedup",
    "250x Memory Reduction",
  ],
  part1: [
    "Whitepaper Analysis",
    "Component Classification",
    "Implementation Complexity",
    "Dependency Map",
    "Mathematical Foundations",
    "HBTA Crossover Analysis",
    "Proven vs Plausible Theorems",
  ],
  part2: [
    "ACOS Design Philosophy",
    "Cognitive Kernel Details",
    "Inter-Thread Communication",
    "Memory Consolidation",
    "Knowledge Fabric Sources",
    "Stiefel Manifold",
    "Cayley Retraction",
  ],
  part3: [
    "AFM Architecture",
    "Attention Flow Manager",
    "Hierarchical Binary Tree Attention",
    "HBTA Complexity O(Nd^2 log N)",
    "Hybrid Attention Mechanism",
    "Tree-Structured Key-Value Cache",
  ],
  part4: [
    "Training Strategy",
    "Orthogonal Fine-Tuning",
    "Cayley Transform Initialization",
    "Gradient Projection",
    "Continual Learning without Forgetting",
    "Stiefel Manifold Optimization",
  ],
  part5: [
    "Continuous Learning",
    "Orthogonal Thread Memory",
    "Task Isolation via OTM",
    "Knowledge Consolidation",
    "Thread Lifecycle Management",
    "Zero Catastrophic Forgetting",
  ],
  part6: [
    "Model Orchestration",
    "3-Level Routing",
    "Intent Classification",
    "Capability Matching",
    "Cost Optimization",
    "Local + Cloud Execution",
    "Model Selection Strategy",
  ],
  part7: [
    "Multimodal Platform",
    "Vision-Language Integration",
    "Audio Processing Pipeline",
    "Capability Matrix",
    "Full-Stack Vision",
    "Cross-Modal Attention",
  ],
  part8: [
    "Self-Evolution",
    "Prompt Evolution",
    "Self-Modifying System",
    "Reflection and Self-Critique",
    "Agent Evolution Cycle",
    "Safety-Speculation Spectrum",
  ],
  part9: [
    "Market Strategy",
    "Dual-Track GTM",
    "Competitor Comparison",
    "Patent Opportunities",
    "Open Source Strategy",
    "Commercialization Path",
  ],
  part10: [
    "Attack Analysis",
    "5 Critical Risks",
    "Risk Heatmap",
    "Adversarial Robustness",
    "Security Vulnerabilities",
    "Mitigation Strategies",
  ],
  part11: [
    "Master Plan",
    "6-Month MVP Roadmap",
    "Probability Assessment",
    "Commercialization Strategy",
    "Strategic Paths",
    "Infrastructure Design",
    "Risk Analysis",
  ],
  roadmap: [
    "Roadmap Timeline",
    "Month 1 HBTA/OTM Layer",
    "Month 2 Cognitive Kernel",
    "Month 3 Upload and Learn",
    "Month 4 Chat Interface",
    "Month 5 CUDA Optimization",
    "Month 6 Beta Launch",
  ],
  theorems: [
    "Theorem Explorer",
    "Theorem 3.4 HBTA Complexity",
    "Theorem 4.4 Cayley Retraction",
    "Theorem 5.3 Local Lyapunov Stability",
    "Theorem 6.1 Bounded Convergence",
    "Theorem 3.6 HBTA Approximation Error",
    "Corollary 4.5 Zero Interference",
  ],
  performance: [
    "Performance Comparison",
    "Attention Scaling O(N^2 d) vs O(N d^2 log N)",
    "Thread Isolation Metrics",
    "Memory Efficiency 250x Reduction",
    "Learning Stability Analysis",
  ],
  glossary: [
    "Glossary of Terms",
    "ACOS Terminology",
    "Technical Definitions",
    "Abbreviation Reference",
  ],
};

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface ContentMatch {
  sectionId: string;
  phrase: string;
}

interface CommandPaletteProps {
  onSectionChange: (id: string) => void;
}

/* ------------------------------------------------------------------ */
/*  Command Palette Component                                          */
/* ------------------------------------------------------------------ */

export function CommandPalette({ onSectionChange }: CommandPaletteProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

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

  const runCommand = useCallback(
    (command: () => void) => {
      setOpen(false);
      command();
    },
    []
  );

  // Search content when query is longer than 2 characters
  const contentMatches: ContentMatch[] = useMemo(() => {
    if (query.length <= 2) return [];
    const lowerQuery = query.toLowerCase();
    const matches: ContentMatch[] = [];

    for (const [sectionId, phrases] of Object.entries(contentIndex)) {
      for (const phrase of phrases) {
        if (phrase.toLowerCase().includes(lowerQuery)) {
          matches.push({ sectionId, phrase });
        }
      }
    }

    return matches;
  }, [query]);

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

  // Highlight matched text within a phrase
  const highlightMatch = useCallback(
    (phrase: string) => {
      if (query.length <= 2) return phrase;
      const lowerPhrase = phrase.toLowerCase();
      const lowerQuery = query.toLowerCase();
      const index = lowerPhrase.indexOf(lowerQuery);
      if (index === -1) return phrase;

      return (
        <>
          {phrase.slice(0, index)}
          <span className="text-emerald-400 font-semibold">
            {phrase.slice(index, index + query.length)}
          </span>
          {phrase.slice(index + query.length)}
        </>
      );
    },
    [query]
  );

  const hasContentResults = contentMatches.length > 0;

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput
        placeholder="Search content..."
        value={query}
        onValueChange={setQuery}
      />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        {/* Section results */}
        <CommandGroup heading="Sections">
          {navItems.map((item, i) => (
            <CommandItem
              key={item.id}
              onSelect={() => runCommand(() => onSectionChange(item.id))}
            >
              <Brain className="w-4 h-4 text-muted-foreground" />
              <span>{item.label}</span>
              <span className="ml-auto text-xs text-muted-foreground font-mono">
                {i + 1 <= 9 ? `${i + 1}` : ""}
              </span>
            </CommandItem>
          ))}
        </CommandGroup>

        {/* Content search results */}
        {hasContentResults && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Content">
              {Object.entries(matchesBySection).map(([sectionId, matches]) => {
                const navItem = navItems.find((n) => n.id === sectionId);
                if (!navItem) return null;

                return matches.map((match, idx) => (
                  <CommandItem
                    key={`${sectionId}-content-${idx}`}
                    onSelect={() =>
                      runCommand(() => onSectionChange(sectionId))
                    }
                    className="pl-8"
                  >
                    <Search className="w-3.5 h-3.5 text-emerald-400/70" />
                    <span className="text-sm">
                      {highlightMatch(match.phrase)}
                    </span>
                    <span className="ml-auto text-[10px] text-muted-foreground/70 font-mono">
                      {navItem.shortLabel}
                    </span>
                  </CommandItem>
                ));
              })}
            </CommandGroup>
          </>
        )}

        <CommandSeparator />
        <CommandGroup heading="Keyboard Shortcuts">
          <CommandItem disabled>
            <Keyboard className="w-4 h-4" />
            <span>Toggle Command Palette</span>
            <span className="ml-auto text-xs text-muted-foreground font-mono">
              Ctrl+K
            </span>
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
