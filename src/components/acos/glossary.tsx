"use client";

import { useState, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  BookOpen,
  ChevronDown,
  Hash,
  X,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

// ─── Types ──────────────────────────────────────────────────────────────────────

type Category =
  | "Mathematical Foundations"
  | "Memory Systems"
  | "Reasoning Components"
  | "Training & Learning";

interface GlossaryTerm {
  id: string;
  term: string;
  abbreviation: string;
  category: Category;
  shortDef: string;
  fullDef: string;
  related: string[];
}

// ─── Category Config ────────────────────────────────────────────────────────────

const categoryConfig: Record<Category, { color: string; badge: string; border: string; bg: string; text: string }> = {
  "Mathematical Foundations": {
    color: "emerald",
    badge: "bg-emerald-600/15 text-emerald-400 border-emerald-500/25",
    border: "border-emerald-500/20",
    bg: "bg-emerald-500/5",
    text: "text-emerald-400",
  },
  "Memory Systems": {
    color: "teal",
    badge: "bg-teal-600/15 text-teal-400 border-teal-500/25",
    border: "border-teal-500/20",
    bg: "bg-teal-500/5",
    text: "text-teal-400",
  },
  "Reasoning Components": {
    color: "cyan",
    badge: "bg-cyan-600/15 text-cyan-400 border-cyan-500/25",
    border: "border-cyan-500/20",
    bg: "bg-cyan-500/5",
    text: "text-cyan-400",
  },
  "Training & Learning": {
    color: "green",
    badge: "bg-green-600/15 text-green-400 border-green-500/25",
    border: "border-green-500/20",
    bg: "bg-green-500/5",
    text: "text-green-400",
  },
};

// ─── Glossary Data ──────────────────────────────────────────────────────────────

const glossaryTerms: GlossaryTerm[] = [
  {
    id: "hbta",
    term: "HBTA",
    abbreviation: "HBTA",
    category: "Mathematical Foundations",
    shortDef: "Hierarchical Binary Tree Attention - O(N log N) attention mechanism",
    fullDef:
      "Hierarchical Binary Tree Attention replaces the quadratic O(N^2*d) self-attention with an O(Nd^2*logN) mechanism using a gated-sum binary tree structure. Instead of computing all pairwise token interactions, HBTA organizes tokens into a binary tree and propagates information via gated sums at each level. The tree depth is log(N), giving the logarithmic scaling. Combined with FlashAttention-style I/O optimization, HBTA achieves a 77x speedup over standard attention at N=32K sequences.",
    related: ["cayley-retraction", "stiefel-manifold", "gradient-projection"],
  },
  {
    id: "otm",
    term: "OTM",
    abbreviation: "OTM",
    category: "Mathematical Foundations",
    shortDef: "Orthogonal Thread Memory - Stiefel Manifold-based thread isolation",
    fullDef:
      "Orthogonal Thread Memory stores each concurrent reasoning thread's state as a column in a Stiefel matrix S_t on the Stiefel Manifold. The orthogonality constraint S^T*S = I_k ensures that thread states are perfectly isolated: <S_i, S_j> = 0 for all i != j. This mathematical guarantee means zero cross-thread interference, eliminating the memory leaks, context contamination, and gradient bleed that plague standard multi-head attention. OTM is maintained via Cayley retraction steps during optimization.",
    related: ["stiefel-manifold", "cayley-retraction", "qr-reorthogonalization", "working-memory"],
  },
  {
    id: "stiefel-manifold",
    term: "Stiefel Manifold",
    abbreviation: "SM",
    category: "Mathematical Foundations",
    shortDef: "Mathematical space of orthonormal frames",
    fullDef:
      "The Stiefel Manifold V_k(R^d) is the set of all k-tuples of orthonormal vectors in R^d. In ACOS, thread memory matrices live on this manifold, ensuring that the K thread vectors remain mutually orthogonal at all times. The manifold structure provides a natural geometry for thread isolation: the tangent space at any point consists of matrices whose columns are orthogonal to the current frame. Optimization on the Stiefel Manifold requires specialized retraction methods (Cayley, QR) to stay on the manifold after gradient steps.",
    related: ["cayley-retraction", "qr-reorthogonalization", "otm", "working-memory"],
  },
  {
    id: "nsk",
    term: "NSK",
    abbreviation: "NSK",
    category: "Reasoning Components",
    shortDef: "Neuro-Symbolic Kernel - Pingala, Panini, Nyaya components",
    fullDef:
      "The Neuro-Symbolic Kernel is ACOS's reasoning engine, composed of three synergistic components named after ancient Indian scholars: Pingala Gating (routing), Panini Constraints (logical composition), and Nyaya Verifier (plausibility checking). Together, they form a complete reasoning pipeline: Pingala dispatches queries to appropriate threads, Panini composes logical constraints as differentiable products, and Nyaya verifies the output against domain knowledge. The NSK enables ACOS to perform structured, verifiable reasoning rather than pattern matching.",
    related: ["pingala-gating", "panini-constraints", "nyaya-verifier"],
  },
  {
    id: "pingala-gating",
    term: "Pingala Gating",
    abbreviation: "PG",
    category: "Reasoning Components",
    shortDef: "Router mechanism for thread dispatch",
    fullDef:
      "Named after the ancient Indian mathematician who described binary number systems, Pingala Gating is the routing mechanism that dispatches incoming queries to the most appropriate reasoning thread. It uses a learned gating function g(x) that produces a probability distribution over available threads, selecting the thread whose orthogonal subspace best matches the query's semantic direction. The gating is differentiable, enabling end-to-end training of the routing policy alongside the thread memories.",
    related: ["nsk", "otm", "nyaya-verifier", "panini-constraints"],
  },
  {
    id: "panini-constraints",
    term: "Panini Constraints",
    abbreviation: "PC",
    category: "Reasoning Components",
    shortDef: "Differentiable product logic (AND/OR/NOT)",
    fullDef:
      "Named after the ancient Sanskrit grammarian, Panini Constraints implement differentiable logical composition through product operations. They support AND (product of probabilities), OR (complement of product of complements), and NOT (1 - probability) operations on soft truth values. This allows ACOS to compose complex logical rules that are fully differentiable, enabling gradient-based optimization of logical reasoning chains. The key innovation is that these constraints are not symbolic rules but differentiable functions that can be learned from data.",
    related: ["nsk", "nyaya-verifier", "pingala-gating"],
  },
  {
    id: "nyaya-verifier",
    term: "Nyaya Verifier",
    abbreviation: "NV",
    category: "Reasoning Components",
    shortDef: "MLP-based plausibility checker with energy function",
    fullDef:
      "Named after the Nyaya school of Indian logic, the Nyaya Verifier is an MLP-based plausibility checker that evaluates the coherence of reasoning outputs. It uses an energy function E(y) that assigns low energy to plausible outputs and high energy to implausible ones. The verifier acts as a guard: if E(y) exceeds a threshold, the output is flagged for re-evaluation or routed to a different reasoning path. The energy function is trained on positive (plausible) and negative (implausible) examples, learning a boundary that separates valid reasoning from hallucination.",
    related: ["nsk", "panini-constraints", "pingala-gating"],
  },
  {
    id: "cayley-retraction",
    term: "Cayley Retraction",
    abbreviation: "CR",
    category: "Mathematical Foundations",
    shortDef: "Method for staying on Stiefel Manifold",
    fullDef:
      "Cayley Retraction is the primary method ACOS uses to project updated thread memory matrices back onto the Stiefel Manifold after gradient steps. Given a tangent vector A at point S, the Cayley retraction computes: R_S(A) = (I - (1/2)A)^(-1) * (I + (1/2)A) * S. This closed-form update preserves orthogonality exactly (up to numerical precision) and is second-order accurate, meaning it closely approximates the exponential map. Theorem 4.4 in the ACOS paper proves that Cayley retraction maintains the manifold constraint with bounded error.",
    related: ["stiefel-manifold", "qr-reorthogonalization", "otm"],
  },
  {
    id: "qr-reorthogonalization",
    term: "QR Re-orthogonalization",
    abbreviation: "QR",
    category: "Mathematical Foundations",
    shortDef: "Numerical stability maintenance",
    fullDef:
      "QR Re-orthogonalization is the fallback mechanism for maintaining Stiefel Manifold membership when numerical errors accumulate. After many Cayley retraction steps, floating-point errors can cause the thread memory matrix S_t to drift off the manifold. The QR decomposition S_t = Q*R is computed, and the orthogonal factor Q replaces S_t. This is a more expensive operation (O(d*K^2)) than Cayley retraction but provides exact orthogonality restoration. ACOS applies QR re-orthogonalization periodically (every N steps) as a stability guarantee.",
    related: ["cayley-retraction", "stiefel-manifold", "otm"],
  },
  {
    id: "catastrophic-forgetting",
    term: "Catastrophic Forgetting",
    abbreviation: "CF",
    category: "Training & Learning",
    shortDef: "When new learning overwrites old",
    fullDef:
      "Catastrophic forgetting is the phenomenon where a neural network's performance on previously learned tasks degrades severely when trained on new tasks. In standard fine-tuning, gradient updates for new tasks overwrite the weight configurations that encoded old task knowledge. Experiments show Task 1 performance drops from 95% to 18% after learning 10 sequential tasks - an 81% degradation. ACOS solves this through orthogonal gradient projection, ensuring new task gradients lie in the null space of prior task subspaces, preserving 86% of original performance.",
    related: ["gradient-projection", "lyapunov-stability", "semantic-memory"],
  },
  {
    id: "lyapunov-stability",
    term: "Lyapunov Stability",
    abbreviation: "LS",
    category: "Training & Learning",
    shortDef: "Stability analysis for scheduling",
    fullDef:
      "Lyapunov Stability analysis provides the theoretical foundation for ACOS's thread scheduling. A Lyapunov function V(x) is constructed such that V(x) > 0 for all non-equilibrium states and dV/dt <= 0 along system trajectories. This ensures that the scheduling dynamics converge to stable operating points rather than oscillating or diverging. Theorem 5.3 in the ACOS paper proves local Lyapunov stability of the thread scheduling system under the proposed learning rate schedule, providing a mathematical guarantee that the system won't exhibit chaotic scheduling behavior.",
    related: ["catastrophic-forgetting", "gradient-projection", "otm"],
  },
  {
    id: "semantic-memory",
    term: "Semantic Memory",
    abbreviation: "SMem",
    category: "Memory Systems",
    shortDef: "Knowledge graph long-term storage",
    fullDef:
      "Semantic Memory is ACOS's long-term knowledge storage layer, implemented as a knowledge graph that persists across sessions. Unlike episodic memory (which stores specific experiences), semantic memory stores generalized facts, concepts, and relationships. It uses a graph neural network backbone that enables efficient retrieval through graph traversal and embedding similarity. Knowledge is consolidated from working memory and episodic memory into semantic memory during idle cycles, following a consolidation schedule inspired by sleep-dependent memory consolidation in biological systems.",
    related: ["episodic-memory", "working-memory", "catastrophic-forgetting"],
  },
  {
    id: "episodic-memory",
    term: "Episodic Memory",
    abbreviation: "EM",
    category: "Memory Systems",
    shortDef: "HNSW vector store for experiences",
    fullDef:
      "Episodic Memory stores specific experiences and interactions using a Hierarchical Navigable Small World (HNSW) graph for approximate nearest neighbor retrieval. Each episode is encoded as a dense vector and inserted into the HNSW index, enabling sub-linear time retrieval of similar past experiences. This allows ACOS to recall relevant past interactions when facing similar situations, supporting analogical reasoning and experience-based learning. The HNSW structure provides O(log N) retrieval with high recall, making it efficient even with millions of stored episodes.",
    related: ["semantic-memory", "working-memory", "hbta"],
  },
  {
    id: "working-memory",
    term: "Working Memory",
    abbreviation: "WM",
    category: "Memory Systems",
    shortDef: "Stiefel matrix S_t for current context",
    fullDef:
      "Working Memory is ACOS's active context representation, stored as the Stiefel matrix S_t that holds the current thread states. This is the memory that is directly accessed and modified during reasoning. Each column of S_t represents one active reasoning thread, and the orthogonal structure ensures threads don't interfere. Working memory has limited capacity (K threads of dimension d), mimicking the capacity constraints of human working memory. When capacity is reached, the least recently used thread is consolidated to episodic/semantic memory and its slot is recycled via QR re-orthogonalization.",
    related: ["otm", "stiefel-manifold", "semantic-memory", "episodic-memory", "qr-reorthogonalization"],
  },
  {
    id: "gradient-projection",
    term: "Gradient Projection",
    abbreviation: "GP",
    category: "Training & Learning",
    shortDef: "Orthogonal projection for interference-free learning",
    fullDef:
      "Gradient Projection is ACOS's core mechanism for preventing catastrophic forgetting. Before applying a gradient update for a new task, the gradient is projected onto the orthogonal complement of the subspace spanned by prior task gradients: g_new = g - P_S * g, where P_S is the projection matrix for the subspace of previously learned tasks. This ensures that the new gradient has zero component in directions important for old tasks. Corollary 4.5 proves that this projection achieves zero interference when the Stiefel Manifold constraint is maintained. The projection cost is O(d*K) per update, where K is the number of prior tasks.",
    related: ["catastrophic-forgetting", "otm", "stiefel-manifold", "lyapunov-stability"],
  },
];

// ─── Alphabet Index ─────────────────────────────────────────────────────────────

const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

// ─── Component ──────────────────────────────────────────────────────────────────

export function Glossary() {
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedTerms, setExpandedTerms] = useState<Set<string>>(new Set());
  const [selectedCategory, setSelectedCategory] = useState<Category | "All">("All");
  const [activeLetter, setActiveLetter] = useState<string | null>(null);

  const toggleExpand = useCallback((id: string) => {
    setExpandedTerms((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const handleRelatedClick = useCallback(
    (relatedId: string) => {
      // Expand the related term and scroll to it
      setExpandedTerms((prev) => new Set(prev).add(relatedId));
      // Reset search/category to ensure the term is visible
      setSearchQuery("");
      setSelectedCategory("All");
      setActiveLetter(null);
      // Scroll after a tick to allow DOM update
      setTimeout(() => {
        const el = document.getElementById(`glossary-term-${relatedId}`);
        if (el) {
          el.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }, 100);
    },
    []
  );

  const handleLetterClick = useCallback((letter: string) => {
    setActiveLetter((prev) => (prev === letter ? null : letter));
    setSearchQuery("");
  }, []);

  // Filter and group terms
  const filteredTerms = useMemo(() => {
    let terms = glossaryTerms;

    // Filter by category
    if (selectedCategory !== "All") {
      terms = terms.filter((t) => t.category === selectedCategory);
    }

    // Filter by search
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      terms = terms.filter(
        (t) =>
          t.term.toLowerCase().includes(q) ||
          t.abbreviation.toLowerCase().includes(q) ||
          t.shortDef.toLowerCase().includes(q) ||
          t.fullDef.toLowerCase().includes(q)
      );
    }

    // Filter by letter
    if (activeLetter) {
      terms = terms.filter(
        (t) => t.term[0].toUpperCase() === activeLetter
      );
    }

    return terms;
  }, [searchQuery, selectedCategory, activeLetter]);

  // Group filtered terms by category
  const groupedTerms = useMemo(() => {
    const groups: Record<Category, GlossaryTerm[]> = {
      "Mathematical Foundations": [],
      "Memory Systems": [],
      "Reasoning Components": [],
      "Training & Learning": [],
    };

    filteredTerms.forEach((term) => {
      groups[term.category].push(term);
    });

    return Object.entries(groups).filter(([, terms]) => terms.length > 0);
  }, [filteredTerms]);

  // Available letters based on current filters
  const availableLetters = useMemo(() => {
    let terms = glossaryTerms;
    if (selectedCategory !== "All") {
      terms = terms.filter((t) => t.category === selectedCategory);
    }
    return new Set(terms.map((t) => t.term[0].toUpperCase()));
  }, [selectedCategory]);

  // Build a map for quick term lookup (for related terms)
  const termMap = useMemo(() => {
    const map: Record<string, GlossaryTerm> = {};
    glossaryTerms.forEach((t) => {
      map[t.id] = t;
    });
    return map;
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-center"
      >
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-600/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono mb-3">
          <BookOpen className="w-3 h-3" />
          KNOWLEDGE BASE
        </div>
        <h2 className="text-2xl md:text-3xl font-bold text-foreground">
          ACOS Glossary
        </h2>
        <p className="text-sm text-muted-foreground mt-2 max-w-xl mx-auto">
          Interactive reference of key technical terms, mathematical foundations, and system components
        </p>
      </motion.div>

      {/* Search + Filters */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="space-y-3"
      >
        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search terms, abbreviations, or definitions..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setActiveLetter(null);
            }}
            className="w-full pl-10 pr-10 py-2.5 bg-card/50 border border-border/30 rounded-xl text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500/40 transition-all"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 rounded-full bg-muted/50 flex items-center justify-center hover:bg-muted transition-colors"
            >
              <X className="w-3 h-3 text-muted-foreground" />
            </button>
          )}
        </div>

        {/* Category Filter Chips */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setSelectedCategory("All")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-200 ${
              selectedCategory === "All"
                ? "bg-emerald-600/15 text-emerald-400 border-emerald-500/25"
                : "bg-card/30 text-muted-foreground border-border/20 hover:border-border/40 hover:text-foreground"
            }`}
          >
            All ({glossaryTerms.length})
          </button>
          {(Object.keys(categoryConfig) as Category[]).map((cat) => {
            const count = glossaryTerms.filter((t) => t.category === cat).length;
            const config = categoryConfig[cat];
            return (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-200 ${
                  selectedCategory === cat
                    ? `${config.badge}`
                    : "bg-card/30 text-muted-foreground border-border/20 hover:border-border/40 hover:text-foreground"
                }`}
              >
                {cat} ({count})
              </button>
            );
          })}
        </div>
      </motion.div>

      {/* Main Content: Glossary + Alphabet Sidebar */}
      <div className="flex gap-4">
        {/* Alphabet Quick-Jump Tabs */}
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="hidden md:flex flex-col items-center gap-0.5 pt-1 flex-shrink-0"
        >
          {alphabet.map((letter) => {
            const isAvailable = availableLetters.has(letter);
            const isActive = activeLetter === letter;
            return (
              <button
                key={letter}
                onClick={() => isAvailable && handleLetterClick(letter)}
                disabled={!isAvailable}
                className={`w-7 h-7 rounded-md text-[10px] font-mono font-semibold flex items-center justify-center transition-all duration-200 ${
                  isActive
                    ? "bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 shadow-sm shadow-emerald-500/10"
                    : isAvailable
                      ? "text-muted-foreground hover:text-foreground hover:bg-muted/50 border border-transparent"
                      : "text-muted-foreground/20 cursor-default border border-transparent"
                }`}
              >
                {letter}
              </button>
            );
          })}
        </motion.div>

        {/* Terms Grid/List */}
        <div className="flex-1 min-w-0">
          {filteredTerms.length === 0 ? (
            /* Empty State */
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center py-16 text-center"
            >
              <div className="w-16 h-16 rounded-2xl bg-muted/20 flex items-center justify-center mb-4">
                <Search className="w-7 h-7 text-muted-foreground/40" />
              </div>
              <p className="text-sm font-medium text-muted-foreground mb-1">
                No terms match your search
              </p>
              <p className="text-xs text-muted-foreground/60 max-w-xs">
                Try adjusting your search query or clearing the filters
              </p>
              <button
                onClick={() => {
                  setSearchQuery("");
                  setSelectedCategory("All");
                  setActiveLetter(null);
                }}
                className="mt-4 px-4 py-2 rounded-lg text-xs font-medium bg-emerald-600/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-600/20 transition-colors"
              >
                Clear all filters
              </button>
            </motion.div>
          ) : (
            /* Grouped Terms */
            <div className="space-y-6">
              {groupedTerms.map(([category, terms]) => {
                const config = categoryConfig[category as Category];
                return (
                  <div key={category}>
                    {/* Category Header */}
                    <div className="flex items-center gap-2 mb-3">
                      <div className={`w-2 h-2 rounded-full ${config.bg.replace("/5", "/40")} ${config.text.replace("text-", "bg-").replace(/-400/, "-500")}`} />
                      <h3 className={`text-xs font-semibold uppercase tracking-wider ${config.text}`}>
                        {category}
                      </h3>
                      <div className="flex-1 h-px bg-border/20" />
                      <span className="text-[10px] text-muted-foreground font-mono">
                        {terms.length} term{terms.length !== 1 ? "s" : ""}
                      </span>
                    </div>

                    {/* Terms Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {terms.map((term, index) => {
                        const isExpanded = expandedTerms.has(term.id);
                        return (
                          <motion.div
                            key={term.id}
                            id={`glossary-term-${term.id}`}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.3, delay: index * 0.05 }}
                          >
                            <Card
                              className={`card-hover-lift cursor-pointer transition-all duration-200 ${
                                isExpanded
                                  ? `${config.border} ${config.bg}`
                                  : "border-border/20 bg-card/40 hover:border-border/40"
                              }`}
                              onClick={() => toggleExpand(term.id)}
                            >
                              <CardContent className="p-4">
                                {/* Term Header */}
                                <div className="flex items-start justify-between gap-2">
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1">
                                      <h4 className="text-sm font-bold text-foreground">
                                        {term.term}
                                      </h4>
                                      {term.abbreviation !== term.term && (
                                        <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${config.badge}`}>
                                          {term.abbreviation}
                                        </span>
                                      )}
                                    </div>
                                    <p className="text-xs text-muted-foreground leading-relaxed">
                                      {term.shortDef}
                                    </p>
                                  </div>
                                  <motion.div
                                    animate={{ rotate: isExpanded ? 180 : 0 }}
                                    transition={{ duration: 0.2 }}
                                    className="flex-shrink-0 mt-0.5"
                                  >
                                    <ChevronDown className="w-4 h-4 text-muted-foreground" />
                                  </motion.div>
                                </div>

                                {/* Expanded Content */}
                                <AnimatePresence>
                                  {isExpanded && (
                                    <motion.div
                                      initial={{ height: 0, opacity: 0 }}
                                      animate={{ height: "auto", opacity: 1 }}
                                      exit={{ height: 0, opacity: 0 }}
                                      transition={{ duration: 0.25, ease: "easeInOut" }}
                                      className="overflow-hidden"
                                    >
                                      <div className="mt-3 pt-3 border-t border-border/20">
                                        <p className="text-xs text-muted-foreground leading-relaxed mb-3">
                                          {term.fullDef}
                                        </p>

                                        {/* Related Terms */}
                                        {term.related.length > 0 && (
                                          <div>
                                            <div className="flex items-center gap-1.5 mb-2">
                                              <Hash className="w-3 h-3 text-muted-foreground/60" />
                                              <span className="text-[10px] font-medium text-muted-foreground/60 uppercase tracking-wider">
                                                Related
                                              </span>
                                            </div>
                                            <div className="flex flex-wrap gap-1.5">
                                              {term.related.map((relId) => {
                                                const relTerm = termMap[relId];
                                                if (!relTerm) return null;
                                                const relConfig = categoryConfig[relTerm.category];
                                                return (
                                                  <button
                                                    key={relId}
                                                    onClick={(e) => {
                                                      e.stopPropagation();
                                                      handleRelatedClick(relId);
                                                    }}
                                                    className={`px-2 py-1 rounded-md text-[10px] font-medium border transition-all duration-150 hover:scale-105 ${relConfig.badge}`}
                                                  >
                                                    {relTerm.term}
                                                  </button>
                                                );
                                              })}
                                            </div>
                                          </div>
                                        )}
                                      </div>
                                    </motion.div>
                                  )}
                                </AnimatePresence>
                              </CardContent>
                            </Card>
                          </motion.div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Stats Footer */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.3 }}
      >
        <Card className="border-border/20 bg-card/30">
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center justify-center gap-6">
              <div className="text-center">
                <p className="text-lg font-bold text-foreground">{glossaryTerms.length}</p>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Total Terms</p>
              </div>
              <div className="w-px h-8 bg-border/20" />
              <div className="text-center">
                <p className="text-lg font-bold text-emerald-400">4</p>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Categories</p>
              </div>
              <div className="w-px h-8 bg-border/20" />
              <div className="text-center">
                <p className="text-lg font-bold text-teal-400">15</p>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Cross-References</p>
              </div>
              <div className="w-px h-8 bg-border/20" />
              <div className="text-center">
                <p className="text-lg font-bold text-cyan-400">0</p>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Blue Colors Used</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
