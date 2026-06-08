"use client";

import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FlaskConical,
  BarChart3,
  Clock,
  Layers,
  TrendingUp,
  AlertTriangle,
  Play,
  RotateCw,
  CheckCircle,
  XCircle,
  Minus,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  AlertCircle,
  Zap,
  DollarSign,
  Cpu,
  Target,
  ArrowUpRight,
  ArrowDownRight,
  Minus as Neutral,
  Eye,
  Shield,
  Scale,
  Thermometer,
  GitCompare,
  Activity,
  Timer,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";

/* ------------------------------------------------------------------ */
/*  TypeScript Types                                                   */
/* ------------------------------------------------------------------ */

interface BenchmarkResult {
  system: string;
  category: string;
  accuracy: number;
  stderr: number;
  n_questions: number;
  scores: number[];
}

interface LatencyEntry {
  system: string;
  latency_ms: number;
  latency_s: number;
}

interface TokenEntry {
  system: string;
  avg_tokens: number;
  total_cost_usd: number;
}

interface EfficiencyEntry {
  system: string;
  accuracy_per_token: number;
  accuracy_per_dollar: number;
  avg_accuracy: number;
}

interface AblationModule {
  module: string;
  category_results: Record<string, { with_module: number; without_module: number; delta: number }>;
  avg_delta: number;
  classification: "helps" | "hurts" | "neutral";
}

interface PairwiseResult {
  category: string;
  acos_mean: number;
  baseline_mean: number;
  mean_diff: number;
  cohens_d: number;
  p_value: number;
  significance: string;
  ci_lower: number;
  ci_upper: number;
  winner: string;
}

interface SignificanceResult {
  baseline: string;
  pairwise: PairwiseResult[];
  avg_diff: number;
  overall_winner: string;
}

interface FailureCategories {
  Timeout: number;
  Hallucination: number;
  "Wrong Answer": number;
  "Empty Response": number;
}

interface SystemFailure {
  categories: FailureCategories;
  total_failure_rate: number;
}

interface FailureExample {
  category: string;
  system: string;
  question: string;
  ground_truth: string;
  system_answer: string;
}

interface ScientificValidationData {
  title: string;
  version: string;
  mode: string;
  seed: number;
  generated_at: string;
  benchmark_results: BenchmarkResult[];
  latency_cost: {
    latency: LatencyEntry[];
    tokens: TokenEntry[];
    efficiency: EfficiencyEntry[];
  };
  ablation: {
    modules: AblationModule[];
    summary: { helps: number; hurts: number; neutral: number };
  };
  statistical_significance: SignificanceResult[];
  failure_analysis: {
    systems: Record<string, SystemFailure>;
    examples: FailureExample[];
  };
  execution_time_ms: number;
  error?: string;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const SYSTEMS = ["ACOS", "Direct LLM", "LLM+RAG", "ReAct", "LangGraph", "CrewAI", "MultiAgent"];
const CATEGORIES = ["MMLU", "GSM8K", "HotpotQA", "ARC", "Logic", "Commonsense"];

const SYSTEM_COLORS: Record<string, string> = {
  ACOS: "from-emerald-400 to-teal-400",
  "Direct LLM": "from-slate-400 to-slate-500",
  "LLM+RAG": "from-sky-400 to-sky-500",
  ReAct: "from-amber-400 to-orange-400",
  LangGraph: "from-violet-400 to-purple-400",
  CrewAI: "from-rose-400 to-pink-400",
  MultiAgent: "from-cyan-400 to-blue-400",
};

const SYSTEM_BAR_COLORS: Record<string, string> = {
  ACOS: "bg-emerald-500",
  "Direct LLM": "bg-slate-400",
  "LLM+RAG": "bg-sky-400",
  ReAct: "bg-amber-400",
  LangGraph: "bg-violet-400",
  CrewAI: "bg-rose-400",
  MultiAgent: "bg-cyan-400",
};

/* ------------------------------------------------------------------ */
/*  Helper: Heatmap Color                                              */
/* ------------------------------------------------------------------ */

function getHeatmapColor(value: number): { bg: string; text: string } {
  if (value >= 0.7) return { bg: "bg-emerald-500/20", text: "text-emerald-400" };
  if (value >= 0.6) return { bg: "bg-green-500/15", text: "text-green-400" };
  if (value >= 0.5) return { bg: "bg-yellow-500/15", text: "text-yellow-400" };
  if (value >= 0.4) return { bg: "bg-orange-500/15", text: "text-orange-400" };
  return { bg: "bg-red-500/15", text: "text-red-400" };
}

function getWinnerBadge(winner: string) {
  if (winner === "ACOS wins") {
    return (
      <Badge className="text-[9px] font-mono bg-emerald-500/15 text-emerald-400 border-emerald-500/25">
        <CheckCircle className="w-2.5 h-2.5 mr-0.5" /> ACOS wins
      </Badge>
    );
  }
  if (winner.includes("wins") && winner !== "ACOS wins") {
    return (
      <Badge className="text-[9px] font-mono bg-red-500/15 text-red-400 border-red-500/25">
        <XCircle className="w-2.5 h-2.5 mr-0.5" /> {winner}
      </Badge>
    );
  }
  return (
    <Badge className="text-[9px] font-mono bg-slate-500/15 text-slate-400 border-slate-500/25">
      <Minus className="w-2.5 h-2.5 mr-0.5" /> Tie
    </Badge>
  );
}

function getSignificanceBadge(significance: string) {
  switch (significance) {
    case "highly_significant":
      return <Badge className="text-[9px] font-mono bg-emerald-500/15 text-emerald-400 border-emerald-500/25">p &lt; 0.01</Badge>;
    case "significant":
      return <Badge className="text-[9px] font-mono bg-green-500/15 text-green-400 border-green-500/25">p &lt; 0.05</Badge>;
    case "marginal":
      return <Badge className="text-[9px] font-mono bg-amber-500/15 text-amber-400 border-amber-500/25">p &lt; 0.10</Badge>;
    default:
      return <Badge className="text-[9px] font-mono bg-slate-500/15 text-slate-400 border-slate-500/25">n.s.</Badge>;
  }
}

function getClassificationIcon(classification: string) {
  if (classification === "helps") {
    return (
      <div className="flex items-center gap-1">
        <ArrowUpRight className="w-3.5 h-3.5 text-emerald-400" />
        <span className="text-[10px] font-mono text-emerald-400 uppercase font-bold">Helps</span>
      </div>
    );
  }
  if (classification === "hurts") {
    return (
      <div className="flex items-center gap-1">
        <ArrowDownRight className="w-3.5 h-3.5 text-red-400" />
        <span className="text-[10px] font-mono text-red-400 uppercase font-bold">Hurts</span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1">
      <Minus className="w-3.5 h-3.5 text-slate-400" />
      <span className="text-[10px] font-mono text-slate-400 uppercase font-bold">Neutral</span>
    </div>
  );
}

function getClassificationBarColor(classification: string): string {
  if (classification === "helps") return "bg-emerald-500";
  if (classification === "hurts") return "bg-red-500";
  return "bg-slate-400";
}

/* ------------------------------------------------------------------ */
/*  Loading Skeleton                                                   */
/* ------------------------------------------------------------------ */

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Skeleton className="w-10 h-10 rounded-lg" />
        <div className="space-y-2">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-3 w-64" />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-64 rounded-xl" />
      <Skeleton className="h-48 rounded-xl" />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Tab 1: Benchmark Results                                           */
/* ------------------------------------------------------------------ */

function BenchmarkResultsTab({ data }: { data: ScientificValidationData }) {
  // Build a matrix: system → category → accuracy
  const matrix: Record<string, Record<string, number>> = {};
  data.benchmark_results.forEach((r) => {
    if (!matrix[r.system]) matrix[r.system] = {};
    matrix[r.system][r.category] = r.accuracy;
  });

  // Find best system per category for highlighting
  const bestPerCategory: Record<string, string> = {};
  CATEGORIES.forEach((cat) => {
    let bestSystem = "";
    let bestScore = -1;
    SYSTEMS.forEach((sys) => {
      const score = matrix[sys]?.[cat] ?? 0;
      if (score > bestScore) {
        bestScore = score;
        bestSystem = sys;
      }
    });
    bestPerCategory[cat] = bestSystem;
  });

  // Average accuracy per system
  const avgPerSystem: Record<string, number> = {};
  SYSTEMS.forEach((sys) => {
    const scores = CATEGORIES.map((cat) => matrix[sys]?.[cat] ?? 0);
    avgPerSystem[sys] = scores.reduce((a, b) => a + b, 0) / scores.length;
  });

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="p-4 rounded-xl bg-card/50 border border-border/30"
        >
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-4 h-4 text-emerald-400" />
            <span className="text-[10px] text-muted-foreground font-mono uppercase">ACOS Avg</span>
          </div>
          <div className="text-2xl font-bold text-emerald-400">
            {(avgPerSystem["ACOS"] * 100).toFixed(1)}%
          </div>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="p-4 rounded-xl bg-card/50 border border-border/30"
        >
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-teal-400" />
            <span className="text-[10px] text-muted-foreground font-mono uppercase">Best Baseline</span>
          </div>
          <div className="text-2xl font-bold text-foreground">
            {(Math.max(...SYSTEMS.filter((s) => s !== "ACOS").map((s) => avgPerSystem[s])) * 100).toFixed(1)}%
          </div>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="p-4 rounded-xl bg-card/50 border border-border/30"
        >
          <div className="flex items-center gap-2 mb-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <span className="text-[10px] text-muted-foreground font-mono uppercase">Categories</span>
          </div>
          <div className="text-2xl font-bold text-foreground">{CATEGORIES.length}</div>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.3 }}
          className="p-4 rounded-xl bg-card/50 border border-border/30"
        >
          <div className="flex items-center gap-2 mb-2">
            <Cpu className="w-4 h-4 text-amber-400" />
            <span className="text-[10px] text-muted-foreground font-mono uppercase">Systems</span>
          </div>
          <div className="text-2xl font-bold text-foreground">{SYSTEMS.length}</div>
        </motion.div>
      </div>

      {/* Heatmap Table */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
      >
        <Card className="border-border/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Thermometer className="w-4 h-4 text-emerald-400" />
              Accuracy Heatmap
              <span className="text-[10px] text-muted-foreground font-mono font-normal ml-2">
                (green = high, red = low, bold = best in category)
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs font-mono">System</TableHead>
                    {CATEGORIES.map((cat) => (
                      <TableHead key={cat} className="text-xs font-mono text-center">
                        {cat}
                      </TableHead>
                    ))}
                    <TableHead className="text-xs font-mono text-center">Avg</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {SYSTEMS.map((sys) => {
                    const isAcos = sys === "ACOS";
                    return (
                      <TableRow key={sys} className={isAcos ? "bg-emerald-500/5" : ""}>
                        <TableCell className="text-xs font-semibold">
                          <span className={isAcos ? "text-emerald-400" : "text-foreground"}>
                            {sys}
                          </span>
                          {isAcos && (
                            <Badge className="ml-1.5 text-[8px] font-mono bg-emerald-500/15 text-emerald-400 border-emerald-500/25">
                              SUT
                            </Badge>
                          )}
                        </TableCell>
                        {CATEGORIES.map((cat) => {
                          const val = matrix[sys]?.[cat] ?? 0;
                          const colors = getHeatmapColor(val);
                          const isBest = bestPerCategory[cat] === sys;
                          return (
                            <TableCell key={cat} className="text-center">
                              <div className={`inline-flex items-center justify-center px-2 py-1 rounded-md ${colors.bg} ${isBest ? "ring-1 ring-emerald-500/30" : ""}`}>
                                <span className={`text-xs font-mono font-bold ${colors.text}`}>
                                  {(val * 100).toFixed(1)}%
                                </span>
                              </div>
                            </TableCell>
                          );
                        })}
                        <TableCell className="text-center">
                          <span className={`text-xs font-mono font-bold ${isAcos ? "text-emerald-400" : "text-foreground"}`}>
                            {(avgPerSystem[sys] * 100).toFixed(1)}%
                          </span>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Per-Category Bar Chart */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.3 }}
      >
        <Card className="border-border/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-teal-400" />
              Accuracy by Category
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {CATEGORIES.map((cat) => {
                const systems = SYSTEMS.map((sys) => ({
                  system: sys,
                  accuracy: matrix[sys]?.[cat] ?? 0,
                })).sort((a, b) => b.accuracy - a.accuracy);

                return (
                  <div key={cat}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-mono font-semibold text-foreground">{cat}</span>
                    </div>
                    <div className="space-y-1.5">
                      {systems.map((s) => {
                        const isAcos = s.system === "ACOS";
                        const barColor = isAcos ? "bg-emerald-500" : SYSTEM_BAR_COLORS[s.system] || "bg-slate-400";
                        return (
                          <div key={s.system} className="flex items-center gap-2">
                            <span className={`text-[10px] font-mono w-24 truncate ${isAcos ? "text-emerald-400 font-bold" : "text-muted-foreground"}`}>
                              {s.system}
                            </span>
                            <div className="flex-1 h-2.5 rounded-full bg-muted/20 overflow-hidden">
                              <motion.div
                                className={`h-full rounded-full ${barColor}`}
                                initial={{ width: 0 }}
                                animate={{ width: `${s.accuracy * 100}%` }}
                                transition={{ duration: 0.8, ease: "easeOut" }}
                              />
                            </div>
                            <span className={`text-[10px] font-mono font-bold w-12 text-right ${isAcos ? "text-emerald-400" : "text-foreground"}`}>
                              {(s.accuracy * 100).toFixed(1)}%
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Tab 2: Latency & Cost Analysis                                     */
/* ------------------------------------------------------------------ */

function LatencyCostTab({ data }: { data: ScientificValidationData }) {
  const { latency, tokens, efficiency } = data.latency_cost;

  // Sort by latency for bar chart
  const sortedByLatency = [...latency].sort((a, b) => a.latency_ms - b.latency_ms);
  const maxLatency = Math.max(...latency.map((l) => l.latency_ms));

  // Sort by tokens
  const sortedByTokens = [...tokens].sort((a, b) => a.avg_tokens - b.avg_tokens);
  const maxTokens = Math.max(...tokens.map((t) => t.avg_tokens));

  // Sort by efficiency
  const sortedByEfficiency = [...efficiency].sort((a, b) => b.accuracy_per_dollar - a.accuracy_per_dollar);
  const maxEfficiency = Math.max(...efficiency.map((e) => e.accuracy_per_dollar));

  return (
    <div className="space-y-6">
      {/* Latency Bar Chart */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <Card className="border-border/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Timer className="w-4 h-4 text-emerald-400" />
              Latency Comparison
              <span className="text-[10px] text-muted-foreground font-mono font-normal ml-2">
                (lower is better)
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {sortedByLatency.map((entry) => {
                const isAcos = entry.system === "ACOS";
                const barColor = isAcos ? "bg-emerald-500" : SYSTEM_BAR_COLORS[entry.system] || "bg-slate-400";
                const widthPct = (entry.latency_ms / maxLatency) * 100;
                return (
                  <div key={entry.system} className="flex items-center gap-3">
                    <span className={`text-xs font-mono w-24 truncate ${isAcos ? "text-emerald-400 font-bold" : "text-muted-foreground"}`}>
                      {entry.system}
                    </span>
                    <div className="flex-1 h-6 rounded-md bg-muted/20 overflow-hidden relative">
                      <motion.div
                        className={`h-full rounded-md ${barColor} ${isAcos ? "opacity-90" : "opacity-60"}`}
                        initial={{ width: 0 }}
                        animate={{ width: `${widthPct}%` }}
                        transition={{ duration: 0.8, ease: "easeOut" }}
                      />
                      <span className="absolute inset-0 flex items-center justify-end pr-2 text-[10px] font-mono text-white font-bold mix-blend-difference">
                        {entry.latency_s.toFixed(2)}s
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Token Usage */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
      >
        <Card className="border-border/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" />
              Token Usage Comparison
              <span className="text-[10px] text-muted-foreground font-mono font-normal ml-2">
                (lower is more efficient)
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {sortedByTokens.map((entry) => {
                const isAcos = entry.system === "ACOS";
                const barColor = isAcos ? "bg-emerald-500" : SYSTEM_BAR_COLORS[entry.system] || "bg-slate-400";
                const widthPct = (entry.avg_tokens / maxTokens) * 100;
                return (
                  <div key={entry.system} className="flex items-center gap-3">
                    <span className={`text-xs font-mono w-24 truncate ${isAcos ? "text-emerald-400 font-bold" : "text-muted-foreground"}`}>
                      {entry.system}
                    </span>
                    <div className="flex-1 h-6 rounded-md bg-muted/20 overflow-hidden relative">
                      <motion.div
                        className={`h-full rounded-md ${barColor} ${isAcos ? "opacity-90" : "opacity-60"}`}
                        initial={{ width: 0 }}
                        animate={{ width: `${widthPct}%` }}
                        transition={{ duration: 0.8, ease: "easeOut" }}
                      />
                      <span className="absolute inset-0 flex items-center justify-end pr-2 text-[10px] font-mono text-white font-bold mix-blend-difference">
                        {entry.avg_tokens.toLocaleString()} tokens
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Cost Efficiency */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
      >
        <Card className="border-border/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-green-400" />
              Cost Efficiency (Accuracy per Dollar)
              <span className="text-[10px] text-muted-foreground font-mono font-normal ml-2">
                (higher is better)
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {sortedByEfficiency.map((entry) => {
                const isAcos = entry.system === "ACOS";
                const barColor = isAcos ? "bg-emerald-500" : SYSTEM_BAR_COLORS[entry.system] || "bg-slate-400";
                const widthPct = (entry.accuracy_per_dollar / maxEfficiency) * 100;
                return (
                  <div key={entry.system} className="flex items-center gap-3">
                    <span className={`text-xs font-mono w-24 truncate ${isAcos ? "text-emerald-400 font-bold" : "text-muted-foreground"}`}>
                      {entry.system}
                    </span>
                    <div className="flex-1 h-6 rounded-md bg-muted/20 overflow-hidden relative">
                      <motion.div
                        className={`h-full rounded-md ${barColor} ${isAcos ? "opacity-90" : "opacity-60"}`}
                        initial={{ width: 0 }}
                        animate={{ width: `${widthPct}%` }}
                        transition={{ duration: 0.8, ease: "easeOut" }}
                      />
                      <span className="absolute inset-0 flex items-center justify-end pr-2 text-[10px] font-mono text-white font-bold mix-blend-difference">
                        {entry.accuracy_per_dollar.toFixed(2)}
                      </span>
                    </div>
                    <span className="text-[10px] font-mono text-muted-foreground w-16 text-right">
                      {(entry.avg_accuracy * 100).toFixed(1)}% acc
                    </span>
                  </div>
                );
              })}
            </div>
            <div className="mt-4 pt-4 border-t border-border/20">
              <p className="text-[10px] text-muted-foreground font-mono">
                ⚠️ ACOS has higher per-query cost due to its multi-pass cognitive pipeline.
                The accuracy-per-dollar metric reveals whether this cost is justified by improved results.
              </p>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Tab 3: Ablation Results                                            */
/* ------------------------------------------------------------------ */

function AblationResultsTab({ data }: { data: ScientificValidationData }) {
  const { modules, summary } = data.ablation;

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-3">
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20"
        >
          <div className="flex items-center gap-2 mb-2">
            <ArrowUpRight className="w-4 h-4 text-emerald-400" />
            <span className="text-[10px] text-muted-foreground font-mono uppercase">Helps</span>
          </div>
          <div className="text-2xl font-bold text-emerald-400">{summary.helps}</div>
          <p className="text-[10px] text-muted-foreground mt-1">Removal hurts performance</p>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="p-4 rounded-xl bg-red-500/5 border border-red-500/20"
        >
          <div className="flex items-center gap-2 mb-2">
            <ArrowDownRight className="w-4 h-4 text-red-400" />
            <span className="text-[10px] text-muted-foreground font-mono uppercase">Hurts</span>
          </div>
          <div className="text-2xl font-bold text-red-400">{summary.hurts}</div>
          <p className="text-[10px] text-muted-foreground mt-1">Removal improves performance</p>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="p-4 rounded-xl bg-slate-500/5 border border-slate-500/20"
        >
          <div className="flex items-center gap-2 mb-2">
            <Minus className="w-4 h-4 text-slate-400" />
            <span className="text-[10px] text-muted-foreground font-mono uppercase">Neutral</span>
          </div>
          <div className="text-2xl font-bold text-slate-400">{summary.neutral}</div>
          <p className="text-[10px] text-muted-foreground mt-1">No significant effect</p>
        </motion.div>
      </div>

      {/* Honesty Note */}
      <div className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/20">
        <div className="flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
          <p className="text-[10px] text-amber-300/80 font-mono">
            HONESTY POLICY: If removing a module <em>improves</em> performance, it is shown in <span className="text-red-400 font-bold">RED</span>.
            This means the module may be adding unnecessary overhead. We do not greenwash results.
          </p>
        </div>
      </div>

      {/* Module Impact Bar Chart */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
      >
        <Card className="border-border/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Layers className="w-4 h-4 text-emerald-400" />
              Module Impact: Which modules help? Which hurt?
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {modules.map((mod) => {
                const maxDelta = Math.max(...modules.map((m) => Math.abs(m.avg_delta)), 0.01);
                const widthPct = (Math.abs(mod.avg_delta) / maxDelta) * 100;
                const barColor = getClassificationBarColor(mod.classification);
                return (
                  <div key={mod.module} className="flex items-center gap-3">
                    <span className="text-xs font-mono w-36 truncate text-foreground">
                      {mod.module}
                    </span>
                    <div className="flex-1 flex items-center">
                      {/* Center-aligned bar: negative goes left, positive goes right */}
                      <div className="w-1/2 flex justify-end pr-1">
                        {mod.avg_delta < 0 && (
                          <motion.div
                            className="h-5 rounded-l-md bg-red-500"
                            initial={{ width: 0 }}
                            animate={{ width: `${(Math.abs(mod.avg_delta) / maxDelta) * 100}%` }}
                            transition={{ duration: 0.8, ease: "easeOut" }}
                          />
                        )}
                      </div>
                      <div className="w-px h-6 bg-border/50" />
                      <div className="w-1/2 flex justify-start pl-1">
                        {mod.avg_delta >= 0 && (
                          <motion.div
                            className="h-5 rounded-r-md bg-emerald-500"
                            initial={{ width: 0 }}
                            animate={{ width: `${(mod.avg_delta / maxDelta) * 100}%` }}
                            transition={{ duration: 0.8, ease: "easeOut" }}
                          />
                        )}
                      </div>
                    </div>
                    <span className="text-xs font-mono font-bold w-14 text-right flex items-center justify-end gap-1">
                      <span className={mod.avg_delta > 0 ? "text-emerald-400" : mod.avg_delta < 0 ? "text-red-400" : "text-slate-400"}>
                        {mod.avg_delta > 0 ? "+" : ""}{(mod.avg_delta * 100).toFixed(1)}%
                      </span>
                    </span>
                    {getClassificationIcon(mod.classification)}
                  </div>
                );
              })}
            </div>
            {/* Center label */}
            <div className="flex justify-center mt-3">
              <span className="text-[9px] text-muted-foreground font-mono">
                ◄ Hurts performance | Helps performance ►
              </span>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Detailed Ablation Table */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.3 }}
      >
        <Card className="border-border/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Activity className="w-4 h-4 text-teal-400" />
              Ablation Details per Category
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs font-mono">Module</TableHead>
                    {CATEGORIES.map((cat) => (
                      <TableHead key={cat} className="text-xs font-mono text-center">
                        {cat}
                      </TableHead>
                    ))}
                    <TableHead className="text-xs font-mono text-center">Avg Δ</TableHead>
                    <TableHead className="text-xs font-mono text-center">Verdict</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {modules.map((mod) => (
                    <TableRow key={mod.module}>
                      <TableCell className="text-xs font-mono font-semibold">
                        {mod.module}
                      </TableCell>
                      {CATEGORIES.map((cat) => {
                        const delta = mod.category_results[cat]?.delta ?? 0;
                        const colorClass = delta > 0.005
                          ? "text-emerald-400"
                          : delta < -0.005
                            ? "text-red-400"
                            : "text-slate-400";
                        return (
                          <TableCell key={cat} className="text-center">
                            <span className={`text-xs font-mono font-bold ${colorClass}`}>
                              {delta > 0 ? "+" : ""}{(delta * 100).toFixed(1)}%
                            </span>
                          </TableCell>
                        );
                      })}
                      <TableCell className="text-center">
                        <span className={`text-xs font-mono font-bold ${
                          mod.avg_delta > 0 ? "text-emerald-400" : mod.avg_delta < 0 ? "text-red-400" : "text-slate-400"
                        }`}>
                          {mod.avg_delta > 0 ? "+" : ""}{(mod.avg_delta * 100).toFixed(1)}%
                        </span>
                      </TableCell>
                      <TableCell className="text-center">
                        {getClassificationIcon(mod.classification)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Tab 4: Statistical Significance                                    */
/* ------------------------------------------------------------------ */

function StatisticalSignificanceTab({ data }: { data: ScientificValidationData }) {
  const { statistical_significance } = data;

  return (
    <div className="space-y-6">
      {/* Overview */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20"
        >
          <div className="text-[10px] text-muted-foreground font-mono uppercase mb-1">ACOS Wins</div>
          <div className="text-2xl font-bold text-emerald-400">
            {statistical_significance.filter((s) => s.overall_winner === "ACOS wins").length}
          </div>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="p-4 rounded-xl bg-red-500/5 border border-red-500/20"
        >
          <div className="text-[10px] text-muted-foreground font-mono uppercase mb-1">Baseline Wins</div>
          <div className="text-2xl font-bold text-red-400">
            {statistical_significance.filter((s) => s.overall_winner !== "ACOS wins" && s.overall_winner !== "Tie").length}
          </div>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="p-4 rounded-xl bg-slate-500/5 border border-slate-500/20"
        >
          <div className="text-[10px] text-muted-foreground font-mono uppercase mb-1">Ties</div>
          <div className="text-2xl font-bold text-slate-400">
            {statistical_significance.filter((s) => s.overall_winner === "Tie").length}
          </div>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.3 }}
          className="p-4 rounded-xl bg-card/50 border border-border/30"
        >
          <div className="text-[10px] text-muted-foreground font-mono uppercase mb-1">Baselines Tested</div>
          <div className="text-2xl font-bold text-foreground">{statistical_significance.length}</div>
        </motion.div>
      </div>

      {/* Honesty Note */}
      <div className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/20">
        <div className="flex items-start gap-2">
          <Shield className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
          <p className="text-[10px] text-amber-300/80 font-mono">
            HONESTY POLICY: If ACOS loses to a baseline with statistical significance, it is shown in{" "}
            <span className="text-red-400 font-bold">RED</span>. We report results as they are — no cherry-picking.
          </p>
        </div>
      </div>

      {/* Pairwise Comparison Cards */}
      <div className="space-y-4">
        {statistical_significance.map((result, idx) => {
          const isAcosWin = result.overall_winner === "ACOS wins";
          const isTie = result.overall_winner === "Tie";

          return (
            <motion.div
              key={result.baseline}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: idx * 0.1 }}
            >
              <Card className={`border-border/30 ${isAcosWin ? "border-l-2 border-l-emerald-500" : !isTie ? "border-l-2 border-l-red-500" : "border-l-2 border-l-slate-500"}`}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <GitCompare className="w-4 h-4 text-teal-400" />
                      ACOS vs {result.baseline}
                    </CardTitle>
                    <div className="flex items-center gap-2">
                      {getWinnerBadge(result.overall_winner)}
                      <Badge className="text-[10px] font-mono bg-card text-foreground border-border/30">
                        Δ = {result.avg_diff > 0 ? "+" : ""}{(result.avg_diff * 100).toFixed(1)}%
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="text-[10px] font-mono">Category</TableHead>
                          <TableHead className="text-[10px] font-mono text-center">ACOS</TableHead>
                          <TableHead className="text-[10px] font-mono text-center">{result.baseline}</TableHead>
                          <TableHead className="text-[10px] font-mono text-center">Mean Δ</TableHead>
                          <TableHead className="text-[10px] font-mono text-center">Cohen&apos;s d</TableHead>
                          <TableHead className="text-[10px] font-mono text-center">p-value</TableHead>
                          <TableHead className="text-[10px] font-mono text-center">95% CI</TableHead>
                          <TableHead className="text-[10px] font-mono text-center">Significance</TableHead>
                          <TableHead className="text-[10px] font-mono text-center">Winner</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {result.pairwise.map((pw) => (
                          <TableRow key={pw.category}>
                            <TableCell className="text-xs font-mono font-semibold">{pw.category}</TableCell>
                            <TableCell className="text-center">
                              <span className="text-xs font-mono text-emerald-400">{(pw.acos_mean * 100).toFixed(1)}%</span>
                            </TableCell>
                            <TableCell className="text-center">
                              <span className="text-xs font-mono text-foreground">{(pw.baseline_mean * 100).toFixed(1)}%</span>
                            </TableCell>
                            <TableCell className="text-center">
                              <span className={`text-xs font-mono font-bold ${pw.mean_diff > 0 ? "text-emerald-400" : pw.mean_diff < 0 ? "text-red-400" : "text-slate-400"}`}>
                                {pw.mean_diff > 0 ? "+" : ""}{(pw.mean_diff * 100).toFixed(1)}%
                              </span>
                            </TableCell>
                            <TableCell className="text-center">
                              <span className="text-xs font-mono">
                                {pw.cohens_d.toFixed(2)}
                              </span>
                            </TableCell>
                            <TableCell className="text-center">
                              <span className="text-xs font-mono">{pw.p_value.toFixed(4)}</span>
                            </TableCell>
                            <TableCell className="text-center">
                              <span className="text-[10px] font-mono text-muted-foreground">
                                [{(pw.ci_lower * 100).toFixed(1)}%, {(pw.ci_upper * 100).toFixed(1)}%]
                              </span>
                            </TableCell>
                            <TableCell className="text-center">
                              {getSignificanceBadge(pw.significance)}
                            </TableCell>
                            <TableCell className="text-center">
                              {getWinnerBadge(pw.winner)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>

                  {/* CI Visualization */}
                  <div className="mt-4 pt-4 border-t border-border/20">
                    <h4 className="text-[10px] text-muted-foreground font-mono uppercase mb-3">
                      Confidence Intervals for Mean Difference (ACOS − {result.baseline})
                    </h4>
                    <div className="space-y-2">
                      {result.pairwise.map((pw) => {
                        // Normalize CI to a range around 0
                        const range = Math.max(Math.abs(pw.ci_lower), Math.abs(pw.ci_upper), 0.1);
                        const leftPos = ((pw.ci_lower + range) / (2 * range)) * 100;
                        const rightPos = ((pw.ci_upper + range) / (2 * range)) * 100;
                        const meanPos = ((pw.mean_diff + range) / (2 * range)) * 100;
                        const crossesZero = pw.ci_lower <= 0 && pw.ci_upper >= 0;

                        return (
                          <div key={pw.category} className="flex items-center gap-2">
                            <span className="text-[10px] font-mono w-20 text-muted-foreground">{pw.category}</span>
                            <div className="flex-1 relative h-5">
                              {/* Zero line */}
                              <div className="absolute top-0 bottom-0 left-1/2 w-px bg-border/50" />
                              {/* CI bar */}
                              <div
                                className={`absolute top-1 h-3 rounded-sm ${crossesZero ? "bg-slate-500/30" : pw.mean_diff > 0 ? "bg-emerald-500/30" : "bg-red-500/30"}`}
                                style={{ left: `${leftPos}%`, width: `${rightPos - leftPos}%` }}
                              />
                              {/* Mean dot */}
                              <div
                                className={`absolute top-0.5 w-4 h-4 rounded-full border-2 ${pw.mean_diff > 0 ? "bg-emerald-500 border-emerald-400" : pw.mean_diff < 0 ? "bg-red-500 border-red-400" : "bg-slate-400 border-slate-300"}`}
                                style={{ left: `calc(${meanPos}% - 8px)` }}
                              />
                            </div>
                            <span className="text-[10px] font-mono text-muted-foreground w-20 text-right">
                              {crossesZero ? "includes 0" : pw.mean_diff > 0 ? "above 0" : "below 0"}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Tab 5: Failure Analysis                                            */
/* ------------------------------------------------------------------ */

function FailureAnalysisTab({ data }: { data: ScientificValidationData }) {
  const { systems, examples } = data.failure_analysis;
  const [expandedExample, setExpandedExample] = useState<number | null>(null);

  // Get sorted systems by total failure rate
  const sortedSystems = Object.entries(systems).sort((a, b) => a[1].total_failure_rate - b[1].total_failure_rate);
  const maxFailureRate = Math.max(...Object.values(systems).map((s) => s.total_failure_rate), 0.01);

  const failureCategories: (keyof FailureCategories)[] = ["Timeout", "Hallucination", "Wrong Answer", "Empty Response"];
  const failureCategoryColors: Record<string, string> = {
    Timeout: "bg-amber-500",
    Hallucination: "bg-purple-500",
    "Wrong Answer": "bg-red-500",
    "Empty Response": "bg-slate-400",
  };

  return (
    <div className="space-y-6">
      {/* Overall Failure Rate by System */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <Card className="border-border/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              Total Failure Rate by System
              <span className="text-[10px] text-muted-foreground font-mono font-normal ml-2">
                (lower is better)
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {sortedSystems.map(([system, failure]) => {
                const isAcos = system === "ACOS";
                const barColor = isAcos ? "bg-emerald-500" : SYSTEM_BAR_COLORS[system] || "bg-slate-400";
                const widthPct = (failure.total_failure_rate / maxFailureRate) * 100;
                return (
                  <div key={system} className="flex items-center gap-3">
                    <span className={`text-xs font-mono w-24 truncate ${isAcos ? "text-emerald-400 font-bold" : "text-muted-foreground"}`}>
                      {system}
                    </span>
                    <div className="flex-1 h-6 rounded-md bg-muted/20 overflow-hidden relative">
                      <motion.div
                        className={`h-full rounded-md ${barColor} ${isAcos ? "opacity-90" : "opacity-60"}`}
                        initial={{ width: 0 }}
                        animate={{ width: `${widthPct}%` }}
                        transition={{ duration: 0.8, ease: "easeOut" }}
                      />
                      <span className="absolute inset-0 flex items-center justify-end pr-2 text-[10px] font-mono text-white font-bold mix-blend-difference">
                        {(failure.total_failure_rate * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Failure Breakdown by Category */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
      >
        <Card className="border-border/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-red-400" />
              Failure Breakdown by Category
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs font-mono">System</TableHead>
                    {failureCategories.map((cat) => (
                      <TableHead key={cat} className="text-xs font-mono text-center">
                        <div className="flex items-center justify-center gap-1">
                          <div className={`w-2 h-2 rounded-full ${failureCategoryColors[cat]}`} />
                          {cat}
                        </div>
                      </TableHead>
                    ))}
                    <TableHead className="text-xs font-mono text-center">Total</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sortedSystems.map(([system, failure]) => {
                    const isAcos = system === "ACOS";
                    return (
                      <TableRow key={system} className={isAcos ? "bg-emerald-500/5" : ""}>
                        <TableCell className="text-xs font-mono font-semibold">
                          <span className={isAcos ? "text-emerald-400" : "text-foreground"}>{system}</span>
                        </TableCell>
                        {failureCategories.map((cat) => {
                          const val = failure.categories[cat];
                          const colorClass = val > 0.15 ? "text-red-400" : val > 0.08 ? "text-amber-400" : "text-emerald-400";
                          return (
                            <TableCell key={cat} className="text-center">
                              <span className={`text-xs font-mono font-bold ${colorClass}`}>
                                {(val * 100).toFixed(1)}%
                              </span>
                            </TableCell>
                          );
                        })}
                        <TableCell className="text-center">
                          <span className={`text-xs font-mono font-bold ${isAcos ? "text-emerald-400" : "text-foreground"}`}>
                            {(failure.total_failure_rate * 100).toFixed(1)}%
                          </span>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Stacked failure bars */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.15 }}
      >
        <Card className="border-border/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Layers className="w-4 h-4 text-purple-400" />
              Failure Composition
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {sortedSystems.map(([system, failure]) => {
                const isAcos = system === "ACOS";
                const total = failure.total_failure_rate;
                return (
                  <div key={system} className="flex items-center gap-3">
                    <span className={`text-xs font-mono w-24 truncate ${isAcos ? "text-emerald-400 font-bold" : "text-muted-foreground"}`}>
                      {system}
                    </span>
                    <div className="flex-1 h-5 rounded-md bg-muted/20 overflow-hidden flex">
                      {failureCategories.map((cat) => {
                        const val = failure.categories[cat];
                        const widthPct = total > 0 ? (val / maxFailureRate) * 100 : 0;
                        return (
                          <motion.div
                            key={cat}
                            className={`h-full ${failureCategoryColors[cat]}`}
                            initial={{ width: 0 }}
                            animate={{ width: `${widthPct}%` }}
                            transition={{ duration: 0.8, ease: "easeOut" }}
                          />
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
            {/* Legend */}
            <div className="flex flex-wrap gap-3 mt-4 pt-3 border-t border-border/20">
              {failureCategories.map((cat) => (
                <div key={cat} className="flex items-center gap-1.5">
                  <div className={`w-2.5 h-2.5 rounded-sm ${failureCategoryColors[cat]}`} />
                  <span className="text-[10px] font-mono text-muted-foreground">{cat}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Example Failures */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
      >
        <Card className="border-border/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Eye className="w-4 h-4 text-rose-400" />
              Example Failures
              <Badge className="text-[10px] font-mono bg-red-500/15 text-red-400 border-red-500/25">
                {examples.length}
              </Badge>
            </CardTitle>
            <CardDescription className="text-[10px] font-mono">
              Real examples of where systems failed, with ground truth for comparison
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
              {examples.map((ex, i) => {
                const isExpanded = expandedExample === i;
                const catColor: Record<string, string> = {
                  Timeout: "bg-amber-500/15 text-amber-400 border-amber-500/25",
                  Hallucination: "bg-purple-500/15 text-purple-400 border-purple-500/25",
                  "Wrong Answer": "bg-red-500/15 text-red-400 border-red-500/25",
                  "Empty Response": "bg-slate-500/15 text-slate-400 border-slate-500/25",
                };
                return (
                  <div
                    key={i}
                    className="p-3 rounded-lg bg-card/50 border border-border/30 cursor-pointer hover:bg-card/80 transition-colors"
                    onClick={() => setExpandedExample(isExpanded ? null : i)}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Badge className={`text-[9px] font-mono ${catColor[ex.category] || "bg-slate-500/15 text-slate-400 border-slate-500/25"}`}>
                          {ex.category}
                        </Badge>
                        <span className="text-xs font-mono text-muted-foreground">{ex.system}</span>
                      </div>
                      {isExpanded ? (
                        <ChevronUp className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                      )}
                    </div>
                    <p className="text-xs text-foreground mt-2 font-medium">{ex.question}</p>
                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="overflow-hidden"
                        >
                          <div className="mt-3 pt-3 border-t border-border/20 space-y-2">
                            <div>
                              <span className="text-[10px] font-mono text-emerald-400 uppercase font-bold">Ground Truth</span>
                              <p className="text-xs text-emerald-300 mt-0.5">{ex.ground_truth}</p>
                            </div>
                            <div>
                              <span className="text-[10px] font-mono text-red-400 uppercase font-bold">System Answer</span>
                              <p className="text-xs text-red-300 mt-0.5">
                                {ex.system_answer || <span className="italic text-slate-500">[empty response]</span>}
                              </p>
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export function ScientificValidation() {
  const [data, setData] = useState<ScientificValidationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [runningFull, setRunningFull] = useState(false);
  const [runningQuick, setRunningQuick] = useState(false);

  /** Fetch existing results from DB (fast, no benchmark run) */
  const fetchResults = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/scientific-validation?mode=results");
      const json = await res.json();
      if (json.error && !json.benchmark_results?.length) {
        setError(json.error);
      } else {
        setData(json);
        setError(null);
      }
    } catch (err) {
      setError("Failed to fetch scientific validation data. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  /** Run a quick benchmark (5 questions per category) */
  const runQuickBenchmark = useCallback(async () => {
    setRunningQuick(true);
    setError(null);
    try {
      const res = await fetch("/api/scientific-validation?mode=quick");
      const json = await res.json();
      if (json.error && !json.benchmark_results?.length) {
        setError(json.error);
      } else {
        setData(json);
        setError(null);
      }
    } catch (err) {
      setError("Quick benchmark failed. The server may be busy — please try again.");
    } finally {
      setRunningQuick(false);
    }
  }, []);

  const runFullValidation = useCallback(async () => {
    setRunningFull(true);
    setError(null);
    try {
      const res = await fetch("/api/scientific-validation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: "report", seed: 42, quick: false }),
      });
      const json = await res.json();
      if (json.error && !json.benchmark_results?.length) {
        setError(json.error);
      } else {
        setData(json);
        setError(null);
      }
    } catch (err) {
      setError("Full validation run failed. Please try again.");
    } finally {
      setRunningFull(false);
    }
  }, []);

  // On first load, just fetch existing results (fast, no benchmark run)
  useEffect(() => {
    fetchResults();
  }, [fetchResults]);

  // Initial loading state (fetching existing results from DB)
  if (loading && !data) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-lg bg-emerald-600/10 border border-emerald-500/20 flex items-center justify-center">
            <FlaskConical className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-foreground">Scientific Validation</h2>
            <p className="text-xs text-muted-foreground font-mono">Loading results...</p>
          </div>
        </div>
        <DashboardSkeleton />
      </div>
    );
  }

  // No data yet — show friendly empty state with Run Quick Benchmark button
  const hasData = data && data.benchmark_results && data.benchmark_results.length > 0;
  if (!hasData && !runningQuick && !runningFull) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-lg bg-emerald-600/10 border border-emerald-500/20 flex items-center justify-center">
            <FlaskConical className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-foreground">Scientific Validation</h2>
            <p className="text-xs text-muted-foreground font-mono">No benchmark data yet</p>
          </div>
        </div>

        <Card className="border-border/30">
          <CardContent className="p-6 flex flex-col items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <FlaskConical className="w-8 h-8 text-emerald-400" />
            </div>
            <div className="text-center space-y-2">
              <h3 className="text-base font-semibold text-foreground">No Benchmark Data Yet</h3>
              <p className="text-sm text-muted-foreground max-w-md">
                Run a quick benchmark to compare ACOS against 6 baseline systems across 6 categories.
                This uses 5 questions per category (30 total) and takes about 1-2 minutes.
              </p>
            </div>
            {error && (
              <div className="w-full p-3 rounded-lg bg-red-500/5 border border-red-500/20 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-xs text-red-400 font-medium">Error</p>
                  <p className="text-[11px] text-red-400/80">{error}</p>
                </div>
              </div>
            )}
            <div className="flex items-center gap-3">
              <Button
                onClick={runQuickBenchmark}
                className="gap-2 bg-emerald-600 hover:bg-emerald-500"
              >
                <Zap className="w-4 h-4" />
                Run Quick Benchmark
              </Button>
              <Button
                onClick={fetchResults}
                variant="outline"
                className="gap-2"
              >
                <RotateCw className="w-4 h-4" />
                Refresh
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-600/10 border border-emerald-500/20 flex items-center justify-center">
            <FlaskConical className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-foreground">Scientific Validation</h2>
            <p className="text-xs text-muted-foreground font-mono">
              Rigorous benchmarking with honest reporting
              {data.generated_at && (
                <span className="ml-2">· {new Date(data.generated_at).toLocaleString()}</span>
              )}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                onClick={fetchResults}
                variant="outline"
                size="sm"
                disabled={loading || runningQuick}
                className="gap-1.5"
              >
                <RotateCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                Refresh
              </Button>
            </TooltipTrigger>
            <TooltipContent>Reload latest results from DB</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                onClick={runQuickBenchmark}
                variant="outline"
                size="sm"
                disabled={runningQuick || runningFull}
                className="gap-1.5"
              >
                <Zap className={`w-3.5 h-3.5 ${runningQuick ? "animate-pulse" : ""}`} />
                {runningQuick ? "Running..." : "Quick Benchmark"}
              </Button>
            </TooltipTrigger>
            <TooltipContent>Run quick 5-question benchmark per category</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                onClick={runFullValidation}
                variant="default"
                size="sm"
                disabled={runningFull || runningQuick}
                className="gap-1.5 bg-emerald-600 hover:bg-emerald-500"
              >
                <Play className={`w-3.5 h-3.5 ${runningFull ? "animate-pulse" : ""}`} />
                {runningFull ? "Running..." : "Full Validation"}
              </Button>
            </TooltipTrigger>
            <TooltipContent>Run full 50-question benchmark + ablation</TooltipContent>
          </Tooltip>
        </div>
      </div>

      {/* Honesty Banner */}
      <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
        <div className="flex items-start gap-2">
          <Shield className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" />
          <div>
            <span className="text-[10px] font-mono text-emerald-400 uppercase font-bold">Honesty-First Reporting</span>
            <p className="text-[10px] text-muted-foreground font-mono mt-0.5">
              Results are reported truthfully. If ACOS loses to a baseline, it will be shown in{" "}
              <span className="text-red-400 font-bold">RED</span>. If a module hurts performance, it will be flagged. No greenwashing.
            </p>
          </div>
        </div>
      </div>

      {/* Error banner (non-fatal) */}
      {error && (
        <div className="p-3 rounded-lg bg-red-500/5 border border-red-500/20 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
          <span className="text-xs text-red-400">{error}</span>
          <Button
            onClick={fetchResults}
            variant="ghost"
            size="sm"
            className="ml-auto text-xs text-red-400"
          >
            Retry
          </Button>
        </div>
      )}

      {/* Running overlay for Quick Benchmark */}
      <AnimatePresence>
        {runningQuick && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center"
          >
            <Card className="border-emerald-500/30 shadow-xl">
              <CardContent className="p-8 flex flex-col items-center gap-4">
                <div className="w-12 h-12 rounded-full border-2 border-emerald-500/30 border-t-emerald-500 animate-spin" />
                <div className="text-center">
                  <p className="text-sm font-semibold text-foreground">Running Quick Benchmark</p>
                  <p className="text-xs text-muted-foreground font-mono mt-1">5 questions × 7 systems × 6 categories</p>
                  <p className="text-xs text-muted-foreground font-mono">This takes about 1-2 minutes...</p>
                  <Progress value={33} className="w-48 mt-3 h-1.5" />
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Running overlay for Full Validation */}
      <AnimatePresence>
        {runningFull && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center"
          >
            <Card className="border-emerald-500/30 shadow-xl">
              <CardContent className="p-8 flex flex-col items-center gap-4">
                <div className="w-12 h-12 rounded-full border-2 border-emerald-500/30 border-t-emerald-500 animate-spin" />
                <div className="text-center">
                  <p className="text-sm font-semibold text-foreground">Running Full Validation</p>
                  <p className="text-xs text-muted-foreground font-mono mt-1">50 questions × 7 systems × 6 categories</p>
                  <p className="text-xs text-muted-foreground font-mono">This may take several minutes...</p>
                  <Progress value={20} className="w-48 mt-3 h-1.5" />
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Tabs */}
      <Tabs defaultValue="benchmarks" className="w-full">
        <TabsList className="w-full flex-wrap h-auto gap-1 p-1 bg-muted/50">
          <TabsTrigger value="benchmarks" className="text-xs gap-1.5">
            <Target className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Benchmarks</span>
            <span className="sm:hidden">Bench</span>
          </TabsTrigger>
          <TabsTrigger value="latency" className="text-xs gap-1.5">
            <Clock className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Latency & Cost</span>
            <span className="sm:hidden">Cost</span>
          </TabsTrigger>
          <TabsTrigger value="ablation" className="text-xs gap-1.5">
            <Layers className="w-3.5 h-3.5" />
            Ablation
          </TabsTrigger>
          <TabsTrigger value="significance" className="text-xs gap-1.5">
            <Scale className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Significance</span>
            <span className="sm:hidden">Stats</span>
          </TabsTrigger>
          <TabsTrigger value="failures" className="text-xs gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Failures</span>
            <span className="sm:hidden">Fail</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="benchmarks">
          <BenchmarkResultsTab data={data} />
        </TabsContent>

        <TabsContent value="latency">
          <LatencyCostTab data={data} />
        </TabsContent>

        <TabsContent value="ablation">
          <AblationResultsTab data={data} />
        </TabsContent>

        <TabsContent value="significance">
          <StatisticalSignificanceTab data={data} />
        </TabsContent>

        <TabsContent value="failures">
          <FailureAnalysisTab data={data} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
