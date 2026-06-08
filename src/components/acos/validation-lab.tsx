"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { motion, AnimatePresence, useInView } from "framer-motion";
import {
  FlaskConical,
  Trophy,
  BarChart3,
  GitCompare,
  AlertTriangle,
  Sparkles,
  Gauge,
  FileText,
  Play,
  RotateCw,
  CheckCircle,
  XCircle,
  Minus,
  ChevronDown,
  ChevronUp,
  Clock,
  Shield,
  Brain,
  Target,
  TrendingUp,
  Activity,
  Zap,
  Eye,
  ArrowRight,
  Circle,
  AlertCircle,
  Lightbulb,
  Cpu,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";

/* ------------------------------------------------------------------ */
/*  TypeScript Types                                                   */
/* ------------------------------------------------------------------ */

interface BenchmarkScore {
  metric: string;
  value: number;
  stderr: number;
  min_value: number;
  max_value: number;
  sample_size: number;
}

interface BenchmarkResult {
  id: string;
  benchmark_name: string;
  category: string;
  system_name: string;
  scores: BenchmarkScore[];
  overall_score: number;
  execution_time_ms: number;
  test_case_count: number;
  timestamp: string;
}

interface SignificanceResult {
  test_name: string;
  statistic: number;
  p_value: number;
  significance_level: string;
  confidence_interval_diff: [number, number];
  effect_size_cohens_d: number;
  sample_size_a: number;
  sample_size_b: number;
}

interface SystemBenchmarkTrace {
  system_name: string;
  system_type: string;
  scores: number[];
  mean_score: number;
  std_score: number;
  median_score: number;
  min_score: number;
  max_score: number;
}

interface ComparisonResult {
  id: string;
  system_a_name: string;
  system_b_name: string;
  benchmark_name: string;
  system_a_trace: SystemBenchmarkTrace | null;
  system_b_trace: SystemBenchmarkTrace | null;
  significance: SignificanceResult | null;
  winner: string;
  margin: number;
  n_cases: number;
}

interface TournamentResult {
  id: string;
  systems: string[];
  comparisons: ComparisonResult[];
  rankings: [string, number][];
  best_system: string;
  worst_system: string;
  n_cases: number;
  total_execution_time_ms: number;
}

interface FailureReport {
  id: string;
  failure_type: string;
  detected: boolean;
  severity: number;
  description: string;
  affected_components: string[];
  evidence: Record<string, unknown>[];
  recommended_actions: string[];
}

interface FailureAnalysisReport {
  id: string;
  system_name: string;
  failure_reports: FailureReport[];
  total_failures_detected: number;
  most_severe_failure: string | null;
  overall_health: number;
  recommendations: string[];
}

interface EmergenceIndicator {
  name: string;
  acos_value: number;
  best_baseline_value: number;
  improvement_factor: number;
  is_emergent: boolean;
  threshold: number;
}

interface EmergenceReport {
  id: string;
  emergence_type: string;
  indicators: EmergenceIndicator[];
  emergence_score: number;
  strongest_emergence: string;
  analysis_summary: string;
}

interface EmergenceAnalysisResult {
  id: string;
  reports: EmergenceReport[];
  overall_emergence_score: number;
  emergent_capabilities: string[];
  non_emergent_capabilities: string[];
}

interface CognitiveMetricResult {
  metric_name: string;
  value: number;
  interpretation: string;
  percentile_vs_baseline: number;
  is_above_baseline: boolean;
}

interface CognitiveMetricsResult {
  id: string;
  system_name: string;
  metrics: CognitiveMetricResult[];
  overall_cognitive_score: number;
  strengths: string[];
  weaknesses: string[];
}

interface CostAnalysis {
  system_costs: Record<string, number>;
  performance_per_cost: Record<string, number>;
  most_efficient: string;
}

interface ValidationSummary {
  overall_score: number | null;
  conclusion: string;
  strengths_count: number;
  weaknesses_count: number;
  recommendations_count: number;
  execution_time_ms: number;
  tournament_winner: string | null;
  rankings: [string, number][];
  emergence_score: number;
  emergent_capabilities: string[];
  health_score: number;
  failures_detected: number;
  acos_category_scores: Record<string, number>;
}

interface ValidationData {
  id: string;
  title: string;
  version: string;
  experiment_design: {
    n_systems: number;
    n_benchmarks: number;
    n_test_cases: number;
    systems_tested: string[];
    benchmarks_run: string[];
    methodology: string;
  } | null;
  benchmark_results: BenchmarkResult[];
  comparison_results: ComparisonResult[];
  tournament_result: TournamentResult | null;
  cognitive_metrics: CognitiveMetricsResult | null;
  failure_analysis: FailureAnalysisReport | null;
  emergence_analysis: EmergenceAnalysisResult | null;
  cost_analysis: CostAnalysis | null;
  strengths: string[];
  weaknesses: string[];
  recommended_changes: string[];
  conclusion: string;
  total_execution_time_ms: number;
  generated_at: string;
  summary: ValidationSummary;
  error?: string;
  timestamp?: string;
}

/* ------------------------------------------------------------------ */
/*  Animated Counter Hook                                              */
/* ------------------------------------------------------------------ */

function useAnimatedCounter(target: number, duration: number = 1200) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true });
  const hasStarted = useRef(false);

  useEffect(() => {
    if (!isInView) return;
    if (hasStarted.current) return;
    hasStarted.current = true;

    const startTime = Date.now();
    const step = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(eased * target);
      if (progress < 1) {
        requestAnimationFrame(step);
      }
    };
    requestAnimationFrame(step);
  }, [isInView, target, duration]);

  return { count, ref };
}

/* ------------------------------------------------------------------ */
/*  Confidence Bar                                                     */
/* ------------------------------------------------------------------ */

function ConfidenceBar({ value, colorClass = "bg-emerald-500" }: { value: number; colorClass?: string }) {
  const percentage = Math.round(Math.min(Math.max(value, 0), 1) * 100);
  return (
    <div className="w-full h-2 rounded-full bg-muted/30 overflow-hidden">
      <motion.div
        className={`h-full rounded-full ${colorClass}`}
        initial={{ width: 0 }}
        animate={{ width: `${percentage}%` }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Severity Badge                                                     */
/* ------------------------------------------------------------------ */

function SeverityBadge({ severity }: { severity: number }) {
  let color: string;
  let label: string;
  if (severity >= 0.8) { color = "bg-red-500/15 text-red-400 border-red-500/25"; label = "Critical"; }
  else if (severity >= 0.5) { color = "bg-amber-500/15 text-amber-400 border-amber-500/25"; label = "High"; }
  else if (severity >= 0.2) { color = "bg-yellow-500/15 text-yellow-400 border-yellow-500/25"; label = "Medium"; }
  else { color = "bg-emerald-500/15 text-emerald-400 border-emerald-500/25"; label = "Low"; }

  return (
    <Badge className={`text-[10px] font-mono ${color}`}>
      {label} ({(severity * 100).toFixed(0)}%)
    </Badge>
  );
}

/* ------------------------------------------------------------------ */
/*  Circular Gauge                                                     */
/* ------------------------------------------------------------------ */

function CircularGauge({ value, size = 100, label }: { value: number; size?: number; label: string }) {
  const [animatedValue, setAnimatedValue] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true });

  useEffect(() => {
    if (!isInView) return;
    const startTime = Date.now();
    const duration = 1400;
    const step = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setAnimatedValue(eased * value);
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [isInView, value]);

  const radius = (size - 16) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - animatedValue * circumference;
  const percentage = Math.round(animatedValue * 100);

  const getColor = (v: number) => {
    if (v >= 0.8) return { stroke: "oklch(0.696 0.17 162.48)", text: "text-emerald-400" };
    if (v >= 0.6) return { stroke: "oklch(0.727 0.194 142.5)", text: "text-green-400" };
    if (v >= 0.4) return { stroke: "oklch(0.768 0.152 73.7)", text: "text-amber-400" };
    return { stroke: "oklch(0.637 0.237 25.33)", text: "text-red-400" };
  };

  const colors = getColor(value);

  return (
    <div ref={ref} className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg viewBox={`0 0 ${size} ${size}`} className="w-full h-full -rotate-90">
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="oklch(1 0 0 / 8%)" strokeWidth="6" />
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={colors.stroke} strokeWidth="6" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={strokeDashoffset} style={{ transition: "stroke-dashoffset 0.1s ease-out" }} />
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={colors.stroke} strokeWidth="6" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={strokeDashoffset} opacity="0.3" filter="blur(3px)" style={{ transition: "stroke-dashoffset 0.1s ease-out" }} />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-xl font-bold ${colors.text}`}>{percentage}%</span>
        </div>
      </div>
      <span className="text-[10px] text-muted-foreground font-mono uppercase tracking-wider text-center">{label}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Stat Card                                                          */
/* ------------------------------------------------------------------ */

function StatCard({ icon, label, value, suffix, sub, delay, gradient }: {
  icon: React.ReactNode;
  label: string;
  value: number;
  suffix?: string;
  sub?: string;
  delay: number;
  gradient: string;
}) {
  const { count, ref } = useAnimatedCounter(value, 1200);

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="relative p-5 rounded-xl bg-card/50 border border-border/30 card-hover-lift group overflow-hidden"
    >
      <div className={`absolute inset-0 bg-gradient-to-br ${gradient} opacity-30 group-hover:opacity-50 transition-opacity duration-300`} />
      <div className="relative z-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-lg bg-emerald-600/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            {icon}
          </div>
          <div className="text-xs text-muted-foreground font-mono uppercase tracking-wider">{label}</div>
        </div>
        <div className="flex items-baseline gap-1">
          <span className="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
            {typeof value === "number" && value < 100 ? count.toFixed(2) : Math.round(count)}
          </span>
          {suffix && <span className="text-lg font-semibold text-emerald-400">{suffix}</span>}
        </div>
        {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
      </div>
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/*  Category Score Bar                                                 */
/* ------------------------------------------------------------------ */

const categoryColorMap: Record<string, { bg: string; border: string; text: string; bar: string }> = {
  memory: { bg: "bg-emerald-500/10", border: "border-emerald-500/20", text: "text-emerald-400", bar: "bg-emerald-500" },
  planning: { bg: "bg-teal-500/10", border: "border-teal-500/20", text: "text-teal-400", bar: "bg-teal-500" },
  reasoning: { bg: "bg-green-500/10", border: "border-green-500/20", text: "text-green-400", bar: "bg-green-500" },
  learning: { bg: "bg-amber-500/10", border: "border-amber-500/20", text: "text-amber-400", bar: "bg-amber-500" },
  prediction: { bg: "bg-cyan-500/10", border: "border-cyan-500/20", text: "text-cyan-400", bar: "bg-cyan-500" },
};

function getCategoryColors(category: string) {
  return categoryColorMap[category] || { bg: "bg-slate-500/10", border: "border-slate-500/20", text: "text-slate-400", bar: "bg-slate-500" };
}

/* ------------------------------------------------------------------ */
/*  Tab: Tournament Rankings                                           */
/* ------------------------------------------------------------------ */

function TournamentTab({ data }: { data: ValidationData }) {
  const { tournament_result, summary } = data;
  const rankings = tournament_result?.rankings || summary?.rankings || [];

  const maxScore = rankings.length > 0 ? Math.max(...rankings.map(([, s]) => s)) : 1;

  return (
    <div className="space-y-8">
      {/* Winner Banner */}
      {tournament_result && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="relative p-6 rounded-2xl bg-gradient-to-br from-emerald-500/10 via-teal-500/5 to-emerald-500/10 border border-emerald-500/20 card-hover-lift overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full -translate-y-1/2 translate-x-1/2 blur-2xl" />
          <div className="relative z-10 flex items-center gap-4">
            <div className="w-14 h-14 rounded-xl bg-emerald-600/15 border border-emerald-500/25 flex items-center justify-center">
              <Trophy className="w-7 h-7 text-emerald-400" />
            </div>
            <div>
              <div className="text-xs text-muted-foreground font-mono uppercase tracking-wider mb-1">Tournament Winner</div>
              <div className="text-2xl font-bold bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
                {tournament_result.best_system}
              </div>
            </div>
            <div className="ml-auto text-right">
              <div className="text-xs text-muted-foreground font-mono">Worst System</div>
              <div className="text-sm text-muted-foreground">{tournament_result.worst_system}</div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Rankings */}
      <div>
        <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-emerald-400" />
          System Rankings
        </h3>
        <div className="space-y-3">
          {rankings.map(([system, score], i) => {
            const isWinner = i === 0;
            const barWidth = (score / maxScore) * 100;
            return (
              <motion.div
                key={system}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.4, delay: i * 0.1 }}
                className={`p-4 rounded-xl ${isWinner ? "bg-emerald-500/5 border border-emerald-500/20" : "bg-card/50 border border-border/30"} card-hover-lift`}
              >
                <div className="flex items-center gap-3 mb-2">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm ${isWinner ? "bg-emerald-600/15 text-emerald-400 border border-emerald-500/25" : "bg-muted/30 text-muted-foreground"}`}>
                    #{i + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`text-sm font-semibold ${isWinner ? "text-emerald-400" : "text-foreground"}`}>{system}</span>
                      {isWinner && (
                        <Badge className="text-[9px] font-mono bg-emerald-500/15 text-emerald-400 border-emerald-500/25">
                          <Trophy className="w-2.5 h-2.5 mr-0.5" /> WINNER
                        </Badge>
                      )}
                    </div>
                  </div>
                  <span className={`text-lg font-bold font-mono ${isWinner ? "text-emerald-400" : "text-foreground"}`}>
                    {(score * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="ml-11">
                  <ConfidenceBar value={score} colorClass={isWinner ? "bg-emerald-500" : "bg-teal-500/60"} />
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* A/B Comparisons */}
      {data.comparison_results && data.comparison_results.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
            <GitCompare className="w-4 h-4 text-teal-400" />
            A/B Comparisons
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.comparison_results.map((comp, i) => {
              const isAcosWin = comp.winner === comp.system_a_name;
              const isTie = comp.winner === "tie";
              return (
                <motion.div
                  key={comp.id}
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: 0.3 + i * 0.1 }}
                  className="p-4 rounded-xl bg-card/50 border border-border/30 card-hover-lift"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2 text-sm">
                      <span className={`font-semibold ${isAcosWin ? "text-emerald-400" : "text-foreground"}`}>
                        {comp.system_a_name}
                      </span>
                      <span className="text-muted-foreground text-xs">vs</span>
                      <span className="font-semibold text-foreground">{comp.system_b_name}</span>
                    </div>
                    <Badge className={`text-[10px] font-mono ${
                      isTie ? "bg-slate-500/15 text-slate-400 border-slate-500/25" :
                      isAcosWin ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/25" :
                      "bg-red-500/15 text-red-400 border-red-500/25"
                    }`}>
                      {isTie ? <Minus className="w-2.5 h-2.5 mr-0.5" /> :
                       isAcosWin ? <CheckCircle className="w-2.5 h-2.5 mr-0.5" /> :
                       <XCircle className="w-2.5 h-2.5 mr-0.5" />}
                      {isTie ? "TIE" : isAcosWin ? "WIN" : "LOSS"}
                    </Badge>
                  </div>

                  {/* Score comparison */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-muted-foreground font-mono w-12">{comp.system_a_name.split(" ")[0]}</span>
                      <div className="flex-1">
                        <ConfidenceBar value={comp.system_a_trace?.mean_score || 0} colorClass={isAcosWin ? "bg-emerald-500" : "bg-teal-500/60"} />
                      </div>
                      <span className="text-[10px] font-mono font-bold text-foreground w-14 text-right">
                        {((comp.system_a_trace?.mean_score || 0) * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-muted-foreground font-mono w-12">{comp.system_b_name.split(" ")[0]}</span>
                      <div className="flex-1">
                        <ConfidenceBar value={comp.system_b_trace?.mean_score || 0} colorClass={!isAcosWin && !isTie ? "bg-emerald-500" : "bg-teal-500/60"} />
                      </div>
                      <span className="text-[10px] font-mono font-bold text-foreground w-14 text-right">
                        {((comp.system_b_trace?.mean_score || 0) * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  {/* Significance */}
                  {comp.significance && (
                    <div className="mt-3 pt-3 border-t border-border/20 flex items-center gap-2 flex-wrap">
                      <Badge className={`text-[9px] font-mono ${
                        comp.significance.significance_level === "highly_significant" ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/25" :
                        comp.significance.significance_level === "significant" ? "bg-green-500/15 text-green-400 border-green-500/25" :
                        comp.significance.significance_level === "marginal" ? "bg-amber-500/15 text-amber-400 border-amber-500/25" :
                        "bg-slate-500/15 text-slate-400 border-slate-500/25"
                      }`}>
                        {comp.significance.significance_level.replace(/_/g, " ")}
                      </Badge>
                      <span className="text-[10px] text-muted-foreground font-mono">
                        p={comp.significance.p_value.toFixed(3)} d={comp.significance.effect_size_cohens_d.toFixed(2)}
                      </span>
                      <span className="text-[10px] text-muted-foreground font-mono ml-auto">
                        margin: {(comp.margin * 100).toFixed(1)}%
                      </span>
                    </div>
                  )}
                </motion.div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Tab: Category Scores                                               */
/* ------------------------------------------------------------------ */

function CategoryScoresTab({ data }: { data: ValidationData }) {
  const categoryScores = data.summary?.acos_category_scores || {};
  const categories = Object.entries(categoryScores);

  // Build per-category benchmark details from benchmark_results
  const benchmarksByCategory: Record<string, BenchmarkResult[]> = {};
  data.benchmark_results.forEach((br) => {
    if (br.system_name.toUpperCase().includes("ACOS")) {
      if (!benchmarksByCategory[br.category]) benchmarksByCategory[br.category] = [];
      benchmarksByCategory[br.category].push(br);
    }
  });

  return (
    <div className="space-y-8">
      {/* Category Score Gauges */}
      {categories.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
            <Gauge className="w-4 h-4 text-emerald-400" />
            ACOS Category Performance
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {categories.map(([category, score], i) => {
              const colors = getCategoryColors(category);
              return (
                <motion.div
                  key={category}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.4, delay: i * 0.08 }}
                  className={`p-4 rounded-xl ${colors.bg} border ${colors.border} card-hover-lift flex flex-col items-center`}
                >
                  <CircularGauge value={score} size={90} label={category} />
                </motion.div>
              );
            })}
          </div>
        </div>
      )}

      {/* Category Horizontal Bars */}
      {categories.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-teal-400" />
            Score Comparison by Category
          </h3>
          <div className="p-4 rounded-xl bg-card/50 border border-border/30">
            <div className="space-y-4">
              {categories.map(([category, score]) => {
                const colors = getCategoryColors(category);
                return (
                  <div key={category}>
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-xs font-semibold capitalize ${colors.text}`}>{category}</span>
                      <span className="text-xs font-mono font-bold text-foreground">{(score * 100).toFixed(1)}%</span>
                    </div>
                    <div className="w-full h-3 rounded-full bg-muted/20 overflow-hidden">
                      <motion.div
                        className={`h-full rounded-full ${colors.bar}`}
                        initial={{ width: 0 }}
                        animate={{ width: `${score * 100}%` }}
                        transition={{ duration: 0.8, ease: "easeOut" }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Benchmark Details by Category */}
      {Object.keys(benchmarksByCategory).length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
            <Target className="w-4 h-4 text-emerald-400" />
            Benchmark Details by Category
          </h3>
          <div className="space-y-4">
            {Object.entries(benchmarksByCategory).map(([category, benchmarks]) => {
              const colors = getCategoryColors(category);
              return (
                <Card key={category} className="border-border/30 card-hover-lift">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Badge className={`text-[9px] font-mono ${colors.bg} ${colors.text} ${colors.border}`}>
                        {category.toUpperCase()}
                      </Badge>
                      <span className="text-muted-foreground font-normal">{benchmarks.length} benchmarks</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                      {benchmarks.map((b) => (
                        <div key={b.id} className="flex items-center gap-3 text-xs">
                          <span className="text-muted-foreground font-mono w-40 truncate">{b.benchmark_name.replace(/_/g, " ")}</span>
                          <div className="flex-1">
                            <ConfidenceBar value={b.overall_score} colorClass={colors.bar} />
                          </div>
                          <span className={`font-mono font-bold ${colors.text} w-14 text-right`}>
                            {(b.overall_score * 100).toFixed(1)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Tab: Failure Analysis                                              */
/* ------------------------------------------------------------------ */

function FailureAnalysisTab({ data }: { data: ValidationData }) {
  const { failure_analysis } = data;
  const [expandedFailure, setExpandedFailure] = useState<string | null>(null);

  if (!failure_analysis) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        <AlertCircle className="w-5 h-5 mr-2" /> No failure analysis data available
      </div>
    );
  }

  const detectedFailures = failure_analysis.failure_reports.filter((f) => f.detected);
  const noIssueFailures = failure_analysis.failure_reports.filter((f) => !f.detected);

  return (
    <div className="space-y-8">
      {/* Health Overview */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="grid grid-cols-1 md:grid-cols-3 gap-4"
      >
        <div className="p-5 rounded-xl bg-card/50 border border-border/30 card-hover-lift flex flex-col items-center">
          <CircularGauge value={failure_analysis.overall_health} size={110} label="Health Score" />
        </div>
        <div className="p-5 rounded-xl bg-card/50 border border-border/30 card-hover-lift flex flex-col items-center justify-center">
          <div className="text-4xl font-bold text-amber-400">{failure_analysis.total_failures_detected}</div>
          <div className="text-xs text-muted-foreground font-mono uppercase mt-2">Failures Detected</div>
          {failure_analysis.most_severe_failure && (
            <Badge className="mt-2 text-[9px] font-mono bg-red-500/15 text-red-400 border-red-500/25">
              <AlertTriangle className="w-2.5 h-2.5 mr-0.5" />
              {failure_analysis.most_severe_failure.replace(/_/g, " ")}
            </Badge>
          )}
        </div>
        <div className="p-5 rounded-xl bg-card/50 border border-border/30 card-hover-lift flex flex-col items-center justify-center">
          <div className="text-4xl font-bold text-emerald-400">{noIssueFailures.length}</div>
          <div className="text-xs text-muted-foreground font-mono uppercase mt-2">Clean Areas</div>
          <Badge className="mt-2 text-[9px] font-mono bg-emerald-500/15 text-emerald-400 border-emerald-500/25">
            <CheckCircle className="w-2.5 h-2.5 mr-0.5" /> ALL CLEAR
          </Badge>
        </div>
      </motion.div>

      {/* Detected Failures */}
      {detectedFailures.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            Detected Failures
            <Badge className="text-[10px] font-mono bg-red-500/15 text-red-400 border-red-500/25">
              {detectedFailures.length}
            </Badge>
          </h3>
          <div className="space-y-3">
            {detectedFailures.map((failure, i) => (
              <motion.div
                key={failure.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: i * 0.1 }}
              >
                <Card className="border-red-500/20 card-hover-lift">
                  <CardContent className="p-4">
                    <div
                      className="flex items-start justify-between gap-3 cursor-pointer"
                      onClick={() => setExpandedFailure(expandedFailure === failure.id ? null : failure.id)}
                    >
                      <div className="flex items-start gap-3">
                        <div className="w-8 h-8 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center justify-center mt-0.5">
                          <AlertTriangle className="w-4 h-4 text-red-400" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-semibold text-foreground capitalize">
                              {failure.failure_type.replace(/_/g, " ")}
                            </span>
                            <SeverityBadge severity={failure.severity} />
                          </div>
                          <p className="text-xs text-muted-foreground">{failure.description}</p>
                        </div>
                      </div>
                      {expandedFailure === failure.id ? (
                        <ChevronUp className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                      )}
                    </div>
                    <AnimatePresence>
                      {expandedFailure === failure.id && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="overflow-hidden"
                        >
                          <div className="pt-3 mt-3 border-t border-border/20 space-y-2">
                            {failure.affected_components.length > 0 && (
                              <div>
                                <span className="text-[10px] text-muted-foreground font-mono uppercase">Affected Components</span>
                                <div className="flex flex-wrap gap-1.5 mt-1">
                                  {failure.affected_components.map((c) => (
                                    <Badge key={c} className="text-[9px] font-mono bg-red-500/10 text-red-400 border-red-500/20">
                                      {c}
                                    </Badge>
                                  ))}
                                </div>
                              </div>
                            )}
                            {failure.recommended_actions.length > 0 && (
                              <div>
                                <span className="text-[10px] text-muted-foreground font-mono uppercase">Recommended Actions</span>
                                <ul className="mt-1 space-y-1">
                                  {failure.recommended_actions.map((action, j) => (
                                    <li key={j} className="flex items-start gap-2 text-xs text-muted-foreground">
                                      <ArrowRight className="w-3 h-3 text-teal-400 flex-shrink-0 mt-0.5" />
                                      {action}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Clean Areas */}
      {noIssueFailures.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-400" />
            Clean Areas
            <Badge className="text-[10px] font-mono bg-emerald-500/15 text-emerald-400 border-emerald-500/25">
              {noIssueFailures.length}
            </Badge>
          </h3>
          <div className="flex flex-wrap gap-2">
            {noIssueFailures.map((failure) => (
              <Tooltip key={failure.id}>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 cursor-default hover:bg-emerald-500/15 transition-colors">
                    <CheckCircle className="w-3 h-3 text-emerald-400" />
                    <span className="text-xs text-emerald-400 capitalize">{failure.failure_type.replace(/_/g, " ")}</span>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{failure.description}</p>
                </TooltipContent>
              </Tooltip>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Tab: Emergent Behaviors                                            */
/* ------------------------------------------------------------------ */

function EmergenceTab({ data }: { data: ValidationData }) {
  const { emergence_analysis } = data;

  if (!emergence_analysis) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        <AlertCircle className="w-5 h-5 mr-2" /> No emergence analysis data available
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Overall Emergence Score */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="grid grid-cols-1 md:grid-cols-3 gap-4"
      >
        <div className="p-5 rounded-xl bg-card/50 border border-border/30 card-hover-lift flex flex-col items-center">
          <CircularGauge value={emergence_analysis.overall_emergence_score} size={110} label="Emergence Score" />
        </div>
        <div className="p-5 rounded-xl bg-emerald-500/5 border border-emerald-500/20 card-hover-lift flex flex-col items-center justify-center">
          <div className="text-4xl font-bold text-emerald-400">{emergence_analysis.emergent_capabilities.length}</div>
          <div className="text-xs text-muted-foreground font-mono uppercase mt-2">Emergent Capabilities</div>
          <div className="flex flex-wrap gap-1.5 mt-2 justify-center">
            {emergence_analysis.emergent_capabilities.map((cap) => (
              <Badge key={cap} className="text-[9px] font-mono bg-emerald-500/15 text-emerald-400 border-emerald-500/25">
                <Sparkles className="w-2.5 h-2.5 mr-0.5" />{cap}
              </Badge>
            ))}
          </div>
        </div>
        <div className="p-5 rounded-xl bg-card/50 border border-border/30 card-hover-lift flex flex-col items-center justify-center">
          <div className="text-4xl font-bold text-muted-foreground">{emergence_analysis.non_emergent_capabilities.length}</div>
          <div className="text-xs text-muted-foreground font-mono uppercase mt-2">Not Yet Emergent</div>
          <div className="flex flex-wrap gap-1.5 mt-2 justify-center">
            {emergence_analysis.non_emergent_capabilities.map((cap) => (
              <Badge key={cap} className="text-[9px] font-mono bg-slate-500/15 text-slate-400 border-slate-500/25">
                {cap}
              </Badge>
            ))}
          </div>
        </div>
      </motion.div>

      {/* Emergence Reports */}
      <div>
        <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-emerald-400" />
          Emergence Analysis by Type
        </h3>
        <div className="space-y-4">
          {emergence_analysis.reports.map((report, i) => {
            const isEmergent = report.emergence_score > 0;
            return (
              <motion.div
                key={report.id}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
              >
                <Card className={`border-border/30 card-hover-lift ${isEmergent ? "border-emerald-500/20" : ""}`}>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      {isEmergent ? (
                        <Sparkles className="w-4 h-4 text-emerald-400" />
                      ) : (
                        <Circle className="w-4 h-4 text-muted-foreground" />
                      )}
                      <span className="capitalize">{report.emergence_type.replace(/_/g, " ")}</span>
                      <Badge className={`text-[9px] font-mono ${isEmergent ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/25" : "bg-slate-500/15 text-slate-400 border-slate-500/25"}`}>
                        Score: {(report.emergence_score * 100).toFixed(0)}%
                      </Badge>
                      {isEmergent && (
                        <Badge className="text-[9px] font-mono bg-emerald-500/15 text-emerald-400 border-emerald-500/25">
                          EMERGENT
                        </Badge>
                      )}
                    </CardTitle>
                    <CardDescription className="text-xs">{report.analysis_summary}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {report.indicators.map((ind) => (
                        <div key={ind.name} className="space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-foreground">{ind.name}</span>
                            <div className="flex items-center gap-2">
                              {ind.is_emergent && (
                                <Badge className="text-[8px] font-mono bg-emerald-500/15 text-emerald-400 border-emerald-500/25">
                                  <Sparkles className="w-2 h-2 mr-0.5" />{(ind.improvement_factor).toFixed(1)}x
                                </Badge>
                              )}
                              <span className="text-[10px] font-mono text-muted-foreground">
                                ACOS: {(ind.acos_value * 100).toFixed(0)}% vs Baseline: {(ind.best_baseline_value * 100).toFixed(0)}%
                              </span>
                            </div>
                          </div>
                          <div className="flex gap-1 items-center">
                            <div className="flex-1 h-1.5 rounded-full bg-muted/20 overflow-hidden">
                              <motion.div
                                className="h-full rounded-full bg-emerald-500"
                                initial={{ width: 0 }}
                                animate={{ width: `${ind.acos_value * 100}%` }}
                                transition={{ duration: 0.6, ease: "easeOut" }}
                              />
                            </div>
                            <div className="flex-1 h-1.5 rounded-full bg-muted/20 overflow-hidden">
                              <motion.div
                                className="h-full rounded-full bg-slate-500/50"
                                initial={{ width: 0 }}
                                animate={{ width: `${ind.best_baseline_value * 100}%` }}
                                transition={{ duration: 0.6, ease: "easeOut", delay: 0.1 }}
                              />
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                    {report.strongest_emergence && (
                      <div className="mt-3 pt-3 border-t border-border/20">
                        <span className="text-[10px] text-muted-foreground font-mono">Strongest indicator: </span>
                        <span className="text-[10px] text-emerald-400 font-mono">{report.strongest_emergence}</span>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Tab: Cognitive Metrics                                             */
/* ------------------------------------------------------------------ */

function CognitiveMetricsTab({ data }: { data: ValidationData }) {
  const { cognitive_metrics } = data;

  if (!cognitive_metrics) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        <AlertCircle className="w-5 h-5 mr-2" /> No cognitive metrics data available
      </div>
    );
  }

  const metricIcons: Record<string, React.ReactNode> = {
    belief_accuracy: <Shield className="w-4 h-4" />,
    goal_completion_rate: <Target className="w-4 h-4" />,
    memory_utilization: <Brain className="w-4 h-4" />,
    prediction_accuracy: <TrendingUp className="w-4 h-4" />,
    uncertainty_calibration: <Gauge className="w-4 h-4" />,
    reflection_quality: <Eye className="w-4 h-4" />,
    causal_accuracy: <GitCompare className="w-4 h-4" />,
    counterfactual_accuracy: <Activity className="w-4 h-4" />,
  };

  return (
    <div className="space-y-8">
      {/* Overall Score */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="flex flex-col md:flex-row gap-4 items-center"
      >
        <div className="p-6 rounded-xl bg-card/50 border border-emerald-500/15 card-hover-lift flex flex-col items-center">
          <CircularGauge value={cognitive_metrics.overall_cognitive_score} size={130} label="Overall Cognitive Score" />
        </div>
        <div className="flex-1 grid grid-cols-2 gap-3 w-full">
          <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20 card-hover-lift text-center">
            <div className="text-2xl font-bold text-emerald-400">{cognitive_metrics.strengths.length}</div>
            <div className="text-[10px] text-muted-foreground font-mono uppercase mt-1">Strengths</div>
          </div>
          <div className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/20 card-hover-lift text-center">
            <div className="text-2xl font-bold text-amber-400">{cognitive_metrics.weaknesses.length}</div>
            <div className="text-[10px] text-muted-foreground font-mono uppercase mt-1">Weaknesses</div>
          </div>
        </div>
      </motion.div>

      {/* Individual Metrics */}
      <div>
        <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
          <Cpu className="w-4 h-4 text-emerald-400" />
          8 Cognitive Metrics
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {cognitive_metrics.metrics.map((metric, i) => {
            const isAbove = metric.is_above_baseline;
            const color = metric.value >= 0.8 ? "emerald" : metric.value >= 0.5 ? "amber" : "red";
            const colorClasses = {
              emerald: { bg: "bg-emerald-500/5", border: "border-emerald-500/20", bar: "bg-emerald-500", text: "text-emerald-400" },
              amber: { bg: "bg-amber-500/5", border: "border-amber-500/20", bar: "bg-amber-500", text: "text-amber-400" },
              red: { bg: "bg-red-500/5", border: "border-red-500/20", bar: "bg-red-500", text: "text-red-400" },
            }[color];

            return (
              <motion.div
                key={metric.metric_name}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: i * 0.06 }}
                className={`p-4 rounded-xl ${colorClasses.bg} border ${colorClasses.border} card-hover-lift`}
              >
                <div className="flex items-center gap-2 mb-3">
                  <div className={`w-7 h-7 rounded-lg ${colorClasses.bg} border ${colorClasses.border} flex items-center justify-center ${colorClasses.text}`}>
                    {metricIcons[metric.metric_name] || <Gauge className="w-4 h-4" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[10px] text-muted-foreground font-mono uppercase tracking-wider truncate">
                      {metric.metric_name.replace(/_/g, " ")}
                    </div>
                  </div>
                  {isAbove && (
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                  )}
                </div>
                <div className="flex items-baseline gap-1 mb-2">
                  <span className={`text-2xl font-bold ${colorClasses.text}`}>
                    {(metric.value * 100).toFixed(0)}%
                  </span>
                  <span className="text-[10px] text-muted-foreground font-mono">
                    {metric.interpretation}
                  </span>
                </div>
                <ConfidenceBar value={metric.value} colorClass={colorClasses.bar} />
                <div className="mt-2 flex items-center justify-between">
                  <span className="text-[9px] text-muted-foreground font-mono">
                    Percentile: {(metric.percentile_vs_baseline * 100).toFixed(0)}%
                  </span>
                  <Badge className={`text-[8px] font-mono ${isAbove ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/25" : "bg-amber-500/15 text-amber-400 border-amber-500/25"}`}>
                    {isAbove ? "Above Baseline" : "Below Baseline"}
                  </Badge>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* Strengths & Weaknesses */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {cognitive_metrics.strengths.length > 0 && (
          <Card className="border-emerald-500/20 card-hover-lift">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-400" />
                Strengths
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                {cognitive_metrics.strengths.map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                    <CheckCircle className="w-3 h-3 text-emerald-400 flex-shrink-0 mt-0.5" />
                    {s}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}
        {cognitive_metrics.weaknesses.length > 0 && (
          <Card className="border-amber-500/20 card-hover-lift">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Weaknesses
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                {cognitive_metrics.weaknesses.map((w, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                    <AlertTriangle className="w-3 h-3 text-amber-400 flex-shrink-0 mt-0.5" />
                    {w}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Tab: Report                                                        */
/* ------------------------------------------------------------------ */

function ReportTab({ data }: { data: ValidationData }) {
  const [expandedSection, setExpandedSection] = useState<string | null>("conclusion");

  const sections = [
    { id: "experiment", label: "Experiment Design", icon: <FlaskConical className="w-4 h-4" />, content: data.experiment_design },
    { id: "conclusion", label: "Conclusion", icon: <FileText className="w-4 h-4" />, content: data.conclusion },
    { id: "strengths", label: "Strengths", icon: <CheckCircle className="w-4 h-4" />, content: data.strengths },
    { id: "weaknesses", label: "Weaknesses", icon: <AlertTriangle className="w-4 h-4" />, content: data.weaknesses },
    { id: "recommendations", label: "Recommendations", icon: <Lightbulb className="w-4 h-4" />, content: data.recommended_changes },
  ];

  return (
    <div className="space-y-6">
      {/* Report Header */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="p-5 rounded-xl bg-gradient-to-br from-emerald-500/5 via-teal-500/5 to-emerald-500/5 border border-emerald-500/15"
      >
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-600/15 border border-emerald-500/25 flex items-center justify-center">
            <FileText className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-foreground">{data.title}</h2>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Badge className="text-[9px] font-mono bg-emerald-500/15 text-emerald-400 border-emerald-500/25">
                v{data.version}
              </Badge>
              <span className="font-mono">
                <Clock className="w-3 h-3 inline mr-1" />
                {data.total_execution_time_ms.toFixed(0)}ms
              </span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Collapsible Sections */}
      <div className="space-y-2">
        {sections.map((section, i) => {
          const isExpanded = expandedSection === section.id;
          const hasContent = Array.isArray(section.content)
            ? section.content.length > 0
            : !!section.content;

          return (
            <motion.div
              key={section.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: i * 0.05 }}
            >
              <Card className="border-border/30 card-hover-lift">
                <div
                  className="p-4 cursor-pointer flex items-center gap-3"
                  onClick={() => setExpandedSection(isExpanded ? null : section.id)}
                >
                  <span className="text-emerald-400">{section.icon}</span>
                  <span className="text-sm font-semibold text-foreground flex-1">{section.label}</span>
                  {Array.isArray(section.content) && (
                    <Badge className="text-[9px] font-mono bg-muted/30 text-muted-foreground border-border/20">
                      {section.content.length}
                    </Badge>
                  )}
                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-muted-foreground" />
                  )}
                </div>
                <AnimatePresence>
                  {isExpanded && hasContent && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="px-4 pb-4 pt-0 border-t border-border/20 mt-0 pt-3">
                        {section.id === "experiment" && data.experiment_design && (
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                            <div className="p-2 rounded-lg bg-muted/20">
                              <span className="text-muted-foreground font-mono">Systems</span>
                              <div className="font-bold text-foreground">{data.experiment_design.n_systems}</div>
                            </div>
                            <div className="p-2 rounded-lg bg-muted/20">
                              <span className="text-muted-foreground font-mono">Benchmarks</span>
                              <div className="font-bold text-foreground">{data.experiment_design.n_benchmarks}</div>
                            </div>
                            <div className="p-2 rounded-lg bg-muted/20">
                              <span className="text-muted-foreground font-mono">Test Cases</span>
                              <div className="font-bold text-foreground">{data.experiment_design.n_test_cases}</div>
                            </div>
                            <div className="p-2 rounded-lg bg-muted/20 col-span-2 md:col-span-1">
                              <span className="text-muted-foreground font-mono">Methodology</span>
                              <div className="font-bold text-foreground text-[10px]">{data.experiment_design.methodology.slice(0, 80)}...</div>
                            </div>
                            <div className="col-span-2 md:col-span-4">
                              <div className="flex flex-wrap gap-1.5 mt-1">
                                {data.experiment_design.systems_tested.map((s) => (
                                  <Badge key={s} className="text-[9px] font-mono bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                                    {s}
                                  </Badge>
                                ))}
                              </div>
                            </div>
                          </div>
                        )}
                        {section.id === "conclusion" && typeof section.content === "string" && (
                          <p className="text-sm text-muted-foreground leading-relaxed">{section.content}</p>
                        )}
                        {Array.isArray(section.content) && (
                          <ul className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
                            {(section.content as string[]).map((item, j) => (
                              <li key={j} className="flex items-start gap-2 text-xs text-muted-foreground">
                                {section.id === "strengths" && <CheckCircle className="w-3 h-3 text-emerald-400 flex-shrink-0 mt-0.5" />}
                                {section.id === "weaknesses" && <AlertTriangle className="w-3 h-3 text-amber-400 flex-shrink-0 mt-0.5" />}
                                {section.id === "recommendations" && <Lightbulb className="w-3 h-3 text-teal-400 flex-shrink-0 mt-0.5" />}
                                {item}
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </Card>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Loading Skeleton                                                   */
/* ------------------------------------------------------------------ */

function ValidationSkeleton() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Skeleton className="w-12 h-12 rounded-xl" />
        <div className="space-y-2">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-3 w-32" />
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>

      {/* Content */}
      <Skeleton className="h-64 rounded-xl" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Skeleton className="h-48 rounded-xl" />
        <Skeleton className="h-48 rounded-xl" />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Error Display                                                      */
/* ------------------------------------------------------------------ */

function ErrorDisplay({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center py-16 gap-4"
    >
      <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
        <AlertTriangle className="w-8 h-8 text-red-400" />
      </div>
      <div className="text-center">
        <h3 className="text-lg font-semibold text-foreground mb-1">Validation Failed</h3>
        <p className="text-sm text-muted-foreground max-w-md">{message}</p>
      </div>
      <Button onClick={onRetry} variant="outline" className="gap-2">
        <RotateCw className="w-4 h-4" /> Retry
      </Button>
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export function ValidationLab() {
  const [data, setData] = useState<ValidationData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runningValidation, setRunningValidation] = useState(false);
  const [activeTab, setActiveTab] = useState("tournament");

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/validation?quick=true&seed=42");
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP ${res.status}`);
      }
      const json = await res.json();
      setData(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch validation data");
    } finally {
      setLoading(false);
    }
  }, []);

  const runFullValidation = useCallback(async () => {
    setRunningValidation(true);
    setError(null);
    try {
      const res = await fetch("/api/validation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ quick: true, seed: Math.floor(Math.random() * 1000) }),
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP ${res.status}`);
      }
      const json = await res.json();
      setData(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run validation");
    } finally {
      setRunningValidation(false);
    }
  }, []);

  // Fetch on mount
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
      >
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500/15 to-teal-500/15 border border-emerald-500/20 flex items-center justify-center">
            <FlaskConical className="w-6 h-6 text-emerald-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
              Validation Lab
            </h1>
            <p className="text-xs text-muted-foreground font-mono">
              ACOS Benchmark & Cognitive Metrics Dashboard
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={fetchData}
            disabled={loading}
            variant="outline"
            size="sm"
            className="gap-2"
          >
            <RotateCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button
            onClick={runFullValidation}
            disabled={runningValidation}
            size="sm"
            className="gap-2 bg-emerald-600 hover:bg-emerald-500 text-white"
          >
            {runningValidation ? (
              <>
                <RotateCw className="w-4 h-4 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Run Full Validation
              </>
            )}
          </Button>
        </div>
      </motion.div>

      {/* Loading State */}
      {(loading || runningValidation) && !data && <ValidationSkeleton />}

      {/* Error State */}
      {error && !loading && !runningValidation && (
        <ErrorDisplay message={error} onRetry={fetchData} />
      )}

      {/* Data Loaded */}
      {data && !error && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
        >
          {/* Summary Stat Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <StatCard
              icon={<Trophy className="w-5 h-5" />}
              label="Tournament Winner"
              value={data.summary?.tournament_winner === "ACOS Runtime" ? 1 : 0}
              suffix=""
              sub={data.summary?.tournament_winner || "N/A"}
              delay={0}
              gradient="from-emerald-500/10 to-emerald-600/5"
            />
            <StatCard
              icon={<Sparkles className="w-5 h-5" />}
              label="Emergence Score"
              value={data.summary?.emergence_score || 0}
              suffix=""
              sub={`${data.summary?.emergent_capabilities?.length || 0} emergent capabilities`}
              delay={0.1}
              gradient="from-teal-500/10 to-teal-600/5"
            />
            <StatCard
              icon={<Shield className="w-5 h-5" />}
              label="Health Score"
              value={data.summary?.health_score || 0}
              suffix=""
              sub={`${data.summary?.failures_detected || 0} failures detected`}
              delay={0.2}
              gradient="from-green-500/10 to-green-600/5"
            />
            <StatCard
              icon={<Zap className="w-5 h-5" />}
              label="Cognitive Score"
              value={data.cognitive_metrics?.overall_cognitive_score || 0}
              suffix=""
              sub={data.cognitive_metrics ? `${data.cognitive_metrics.strengths.length} strengths, ${data.cognitive_metrics.weaknesses.length} weaknesses` : "N/A"}
              delay={0.3}
              gradient="from-emerald-500/10 to-teal-600/5"
            />
          </div>

          {/* Tabbed Content */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="w-full grid grid-cols-3 sm:grid-cols-6 h-auto p-1 bg-card/50 border border-border/30">
              <TabsTrigger value="tournament" className="text-xs gap-1.5 py-2">
                <Trophy className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Tournament</span>
                <span className="sm:hidden">Rank</span>
              </TabsTrigger>
              <TabsTrigger value="categories" className="text-xs gap-1.5 py-2">
                <BarChart3 className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Categories</span>
                <span className="sm:hidden">Cats</span>
              </TabsTrigger>
              <TabsTrigger value="failures" className="text-xs gap-1.5 py-2">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Failures</span>
                <span className="sm:hidden">Fail</span>
              </TabsTrigger>
              <TabsTrigger value="emergence" className="text-xs gap-1.5 py-2">
                <Sparkles className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Emergence</span>
                <span className="sm:hidden">Emrg</span>
              </TabsTrigger>
              <TabsTrigger value="cognitive" className="text-xs gap-1.5 py-2">
                <Cpu className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Cognitive</span>
                <span className="sm:hidden">Cog</span>
              </TabsTrigger>
              <TabsTrigger value="report" className="text-xs gap-1.5 py-2">
                <FileText className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Report</span>
                <span className="sm:hidden">Rpt</span>
              </TabsTrigger>
            </TabsList>

            <TabsContent value="tournament" className="mt-6">
              <TournamentTab data={data} />
            </TabsContent>
            <TabsContent value="categories" className="mt-6">
              <CategoryScoresTab data={data} />
            </TabsContent>
            <TabsContent value="failures" className="mt-6">
              <FailureAnalysisTab data={data} />
            </TabsContent>
            <TabsContent value="emergence" className="mt-6">
              <EmergenceTab data={data} />
            </TabsContent>
            <TabsContent value="cognitive" className="mt-6">
              <CognitiveMetricsTab data={data} />
            </TabsContent>
            <TabsContent value="report" className="mt-6">
              <ReportTab data={data} />
            </TabsContent>
          </Tabs>
        </motion.div>
      )}

      {/* Running validation overlay */}
      <AnimatePresence>
        {runningValidation && data && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="fixed bottom-20 right-6 z-50 p-4 rounded-xl bg-card border border-emerald-500/30 shadow-lg shadow-emerald-500/10 flex items-center gap-3"
          >
            <RotateCw className="w-5 h-5 text-emerald-400 animate-spin" />
            <div>
              <div className="text-sm font-semibold text-foreground">Running Validation</div>
              <div className="text-[10px] text-muted-foreground font-mono">This may take a moment...</div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
