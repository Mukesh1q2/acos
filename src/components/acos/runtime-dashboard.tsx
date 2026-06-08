"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { motion, AnimatePresence, useInView } from "framer-motion";
import {
  Brain,
  Activity,
  Target,
  Network,
  TrendingUp,
  Shield,
  AlertTriangle,
  CheckCircle,
  Database,
  ArrowRight,
  Clock,
  Hash,
  Zap,
  Eye,
  Circle,
  Pause,
  ChevronDown,
  RefreshCw,
  GitBranch,
  Layers,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";

/* ------------------------------------------------------------------ */
/*  TypeScript Types                                                   */
/* ------------------------------------------------------------------ */

interface Concept {
  id: string;
  name: string;
  concept_type: string;
  description: string;
  confidence: number;
  properties: string;
  access_count: number;
}

interface Entity {
  id: string;
  name: string;
  entity_type: string;
  description: string;
  confidence: number;
  concept_id: string;
}

interface Relationship {
  id: string;
  source_name: string;
  target_name: string;
  relationship_type: string;
  confidence: number;
  description: string;
}

interface EvidenceItem {
  id: string;
  content: string;
  evidence_type: string;
  source_id: string | null;
  confidence: number;
  created_at: string;
}

interface Belief {
  id: string;
  statement: string;
  confidence: number;
  status: string;
  supporting_evidence: EvidenceItem[];
  contradicting_evidence: EvidenceItem[];
  supporting_evidence_count: number;
  contradicting_evidence_count: number;
  related_concept_ids: string[];
  parent_belief_id: string | null;
  version: number;
  category: string;
  created_at: string;
  updated_at: string;
}

interface Goal {
  id: string;
  description: string;
  status: string;
  priority: string;
  progress: number;
  parent_goal_id: string | null;
  subgoal_ids: string[];
  dependency_ids: string[];
  related_concept_ids: string[];
  related_belief_ids: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

interface CognitiveState {
  id: string;
  session_count: number;
  overall_confidence: number;
  uncertainty_estimates: string;
  knowledge_graph_concept_ids: string[];
  last_query: string;
  last_synthesis: string;
}

interface RuntimeStats {
  totalConcepts: number;
  totalEntities: number;
  totalRelationships: number;
  activeBeliefs: number;
  weakenedBeliefs: number;
  totalBeliefs: number;
  activeGoals: number;
  completedGoals: number;
  pausedGoals: number;
  totalGoals: number;
  avgBeliefConfidence: number;
  avgGoalProgress: number;
  overallConfidence: number;
  sessionCount: number;
  relationshipTypes: Record<string, number>;
  conceptTypes: Record<string, number>;
}

interface RuntimeData {
  concepts: Concept[];
  entities: Entity[];
  relationships: Relationship[];
  beliefs: Belief[];
  goals: Goal[];
  cognitiveState: CognitiveState | null;
  stats: RuntimeStats;
  version: string;
  timestamp: string;
}

/* ------------------------------------------------------------------ */
/*  Animated Counter Hook                                              */
/* ------------------------------------------------------------------ */

function useAnimatedCounter(target: number, duration: number = 1500) {
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
      setCount(Math.round(eased * target));
      if (progress < 1) {
        requestAnimationFrame(step);
      }
    };
    requestAnimationFrame(step);
  }, [isInView, target, duration]);

  return { count, ref };
}

/* ------------------------------------------------------------------ */
/*  Confidence Gauge (Circular SVG)                                    */
/* ------------------------------------------------------------------ */

function ConfidenceGauge({ value, size = 180 }: { value: number; size?: number }) {
  const [animatedValue, setAnimatedValue] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true });

  useEffect(() => {
    if (!isInView) return;
    const startTime = Date.now();
    const duration = 1800;
    const step = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setAnimatedValue(eased * value);
      if (progress < 1) {
        requestAnimationFrame(step);
      }
    };
    requestAnimationFrame(step);
  }, [isInView, value]);

  const radius = (size - 20) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (animatedValue / 1) * circumference;
  const percentage = Math.round(animatedValue * 100);

  // Color scale: red -> amber -> emerald based on confidence
  const getColor = (v: number) => {
    if (v >= 0.8) return { stroke: "oklch(0.696 0.17 162.48)", text: "text-emerald-400" };
    if (v >= 0.6) return { stroke: "oklch(0.727 0.194 142.5)", text: "text-green-400" };
    if (v >= 0.4) return { stroke: "oklch(0.768 0.152 73.7)", text: "text-amber-400" };
    return { stroke: "oklch(0.637 0.237 25.33)", text: "text-red-400" };
  };

  const colors = getColor(value);

  return (
    <div ref={ref} className="flex flex-col items-center gap-3">
      <div className="relative" style={{ width: size, height: size }}>
        <svg viewBox={`0 0 ${size} ${size}`} className="w-full h-full -rotate-90">
          {/* Background ring */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="oklch(1 0 0 / 8%)"
            strokeWidth="10"
          />
          {/* Progress ring */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={colors.stroke}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            style={{ transition: "stroke-dashoffset 0.1s ease-out" }}
          />
          {/* Glow effect */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={colors.stroke}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            opacity="0.3"
            filter="blur(4px)"
            style={{ transition: "stroke-dashoffset 0.1s ease-out" }}
          />
        </svg>
        {/* Center label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-4xl font-bold ${colors.text}`}>
            {percentage}%
          </span>
          <span className="text-xs text-muted-foreground font-mono mt-1">
            CONFIDENCE
          </span>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Stat Card                                                          */
/* ------------------------------------------------------------------ */

function StatCard({
  icon,
  label,
  value,
  suffix,
  sub,
  delay,
  gradient,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  suffix?: string;
  sub?: string;
  delay: number;
  gradient: string;
}) {
  const { count, ref } = useAnimatedCounter(value, 1500);

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="relative p-5 rounded-xl bg-card/50 border border-border/30 card-hover-lift group overflow-hidden"
    >
      {/* Subtle gradient bg */}
      <div className={`absolute inset-0 bg-gradient-to-br ${gradient} opacity-30 group-hover:opacity-50 transition-opacity duration-300`} />
      {/* Shimmer on hover */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 animate-shimmer transition-opacity duration-500" />

      <div className="relative z-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-lg bg-emerald-600/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            {icon}
          </div>
          <div className="text-xs text-muted-foreground font-mono uppercase tracking-wider">{label}</div>
        </div>
        <div className="flex items-baseline gap-1">
          <span className="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
            {count}
          </span>
          {suffix && (
            <span className="text-lg font-semibold text-emerald-400">{suffix}</span>
          )}
        </div>
        {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
      </div>
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/*  Confidence Bar                                                     */
/* ------------------------------------------------------------------ */

function ConfidenceBar({ value, colorClass = "bg-emerald-500" }: { value: number; colorClass?: string }) {
  const percentage = Math.round(value * 100);
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
/*  Relationship Color Map                                             */
/* ------------------------------------------------------------------ */

const relationshipColorMap: Record<string, { bg: string; border: string; text: string; bar: string }> = {
  depends_on: { bg: "bg-amber-500/10", border: "border-amber-500/20", text: "text-amber-400", bar: "bg-amber-500" },
  part_of: { bg: "bg-emerald-500/10", border: "border-emerald-500/20", text: "text-emerald-400", bar: "bg-emerald-500" },
  relates_to: { bg: "bg-slate-500/10", border: "border-slate-500/20", text: "text-slate-400", bar: "bg-slate-500" },
  enables: { bg: "bg-teal-500/10", border: "border-teal-500/20", text: "text-teal-400", bar: "bg-teal-500" },
  contradicts: { bg: "bg-red-500/10", border: "border-red-500/20", text: "text-red-400", bar: "bg-red-500" },
  supports: { bg: "bg-green-500/10", border: "border-green-500/20", text: "text-green-400", bar: "bg-green-500" },
};

function getRelationshipColor(type: string) {
  return relationshipColorMap[type] || { bg: "bg-slate-500/10", border: "border-slate-500/20", text: "text-slate-400", bar: "bg-slate-500" };
}

/* ------------------------------------------------------------------ */
/*  Priority Color Map                                                 */
/* ------------------------------------------------------------------ */

const priorityColorMap: Record<string, { bg: string; text: string }> = {
  CRITICAL: { bg: "bg-red-500/15", text: "text-red-400" },
  HIGH: { bg: "bg-amber-500/15", text: "text-amber-400" },
  NORMAL: { bg: "bg-slate-500/15", text: "text-slate-400" },
  LOW: { bg: "bg-emerald-500/15", text: "text-emerald-400" },
};

/* ------------------------------------------------------------------ */
/*  Goal Status Icon                                                   */
/* ------------------------------------------------------------------ */

function GoalStatusIcon({ status }: { status: string }) {
  const s = typeof status === "string" ? status : String(status);
  switch (s.toUpperCase()) {
    case "ACTIVE":
      return <Activity className="w-3.5 h-3.5 text-emerald-400" />;
    case "COMPLETED":
      return <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />;
    case "PAUSED":
      return <Pause className="w-3.5 h-3.5 text-amber-400" />;
    default:
      return <Circle className="w-3.5 h-3.5 text-muted-foreground" />;
  }
}

/* ------------------------------------------------------------------ */
/*  Belief Status Badge                                                */
/* ------------------------------------------------------------------ */

function BeliefStatusBadge({ status }: { status: string }) {
  const s = typeof status === "string" ? status : String(status);
  const isActive = s.toUpperCase() === "ACTIVE";
  return (
    <Badge
      className={`text-[10px] font-mono ${
        isActive
          ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/25 hover:bg-emerald-500/20"
          : "bg-amber-500/15 text-amber-400 border-amber-500/25 hover:bg-amber-500/20"
      }`}
    >
      {s.toUpperCase()}
    </Badge>
  );
}

/* ------------------------------------------------------------------ */
/*  Goal Status Badge                                                  */
/* ------------------------------------------------------------------ */

function GoalStatusBadge({ status }: { status: string }) {
  const s = (typeof status === "string" ? status : String(status)).toUpperCase();
  const colorMap: Record<string, string> = {
    ACTIVE: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
    COMPLETED: "bg-green-500/15 text-green-400 border-green-500/25",
    PAUSED: "bg-amber-500/15 text-amber-400 border-amber-500/25",
  };
  return (
    <Badge className={`text-[10px] font-mono ${colorMap[s] || "bg-slate-500/15 text-slate-400 border-slate-500/25"}`}>
      {s}
    </Badge>
  );
}

/* ------------------------------------------------------------------ */
/*  Priority Badge                                                     */
/* ------------------------------------------------------------------ */

function PriorityBadge({ priority }: { priority: string | number }) {
  const label = typeof priority === "number"
    ? (priority >= 20 ? "CRITICAL" : priority >= 15 ? "HIGH" : priority >= 10 ? "NORMAL" : "LOW")
    : String(priority).toUpperCase();
  const colors = priorityColorMap[label] || priorityColorMap.NORMAL;
  return (
    <Badge className={`text-[10px] font-mono ${colors.bg} ${colors.text} border-transparent`}>
      {label}
    </Badge>
  );
}

/* ------------------------------------------------------------------ */
/*  Tab: Overview                                                      */
/* ------------------------------------------------------------------ */

function OverviewTab({ data }: { data: RuntimeData }) {
  const { stats, cognitiveState } = data;

  const statCards = [
    { icon: <Network className="w-5 h-5" />, label: "Concepts", value: stats.totalConcepts, sub: `${Object.keys(stats.conceptTypes).length} types`, gradient: "from-emerald-500/10 to-emerald-600/5" },
    { icon: <GitBranch className="w-5 h-5" />, label: "Relationships", value: stats.totalRelationships, sub: `${Object.keys(stats.relationshipTypes).length} types`, gradient: "from-teal-500/10 to-teal-600/5" },
    { icon: <Shield className="w-5 h-5" />, label: "Active Beliefs", value: stats.activeBeliefs, sub: `${stats.weakenedBeliefs} weakened`, gradient: "from-green-500/10 to-green-600/5" },
    { icon: <Target className="w-5 h-5" />, label: "Active Goals", value: stats.activeGoals, sub: `${stats.completedGoals} completed`, gradient: "from-emerald-500/10 to-teal-600/5" },
    { icon: <Eye className="w-5 h-5" />, label: "Sessions", value: stats.sessionCount, sub: "interaction cycles", gradient: "from-teal-500/10 to-green-600/5" },
    { icon: <TrendingUp className="w-5 h-5" />, label: "Avg Confidence", value: Math.round(stats.avgBeliefConfidence * 100), suffix: "%", sub: "belief system", gradient: "from-emerald-500/10 to-emerald-600/5" },
  ];

  return (
    <div className="space-y-8">
      {/* Confidence Gauge + Session Info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Large Confidence Gauge */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6 }}
          className="flex flex-col items-center justify-center p-8 rounded-2xl bg-card/50 border border-emerald-500/15 card-hover-lift"
        >
          <ConfidenceGauge value={stats.overallConfidence} size={200} />
          <div className="mt-4 flex items-center gap-2">
            <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/25 text-xs font-mono">
              <Zap className="w-3 h-3 mr-1" />
              v{data.version} Runtime
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-2 text-center">
            Overall Cognitive Confidence
          </p>
        </motion.div>

        {/* Session & State Info */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="space-y-4"
        >
          <Card className="border-border/30 card-hover-lift">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Brain className="w-4 h-4 text-emerald-400" />
                Cognitive State
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Session Count</span>
                <div className="flex items-center gap-1.5">
                  <span className="font-mono font-bold text-foreground">{stats.sessionCount}</span>
                  <TrendingUp className="w-3 h-3 text-emerald-400" />
                </div>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Active Beliefs</span>
                <span className="font-mono font-bold text-emerald-400">{stats.activeBeliefs}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Weakened Beliefs</span>
                <span className="font-mono font-bold text-amber-400">{stats.weakenedBeliefs}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Goal Progress</span>
                <span className="font-mono font-bold text-emerald-400">{Math.round(stats.avgGoalProgress * 100)}%</span>
              </div>
              <div className="mt-2">
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-muted-foreground">Avg Goal Progress</span>
                  <span className="font-mono text-emerald-400">{Math.round(stats.avgGoalProgress * 100)}%</span>
                </div>
                <Progress value={stats.avgGoalProgress * 100} className="h-2" />
              </div>
            </CardContent>
          </Card>

          {cognitiveState && (
            <Card className="border-border/30 card-hover-lift">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Clock className="w-4 h-4 text-teal-400" />
                  Last Activity
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {cognitiveState.last_query && (
                  <div className="text-xs">
                    <span className="text-muted-foreground">Last Query: </span>
                    <span className="text-foreground font-mono truncate block max-w-full">{cognitiveState.last_query}</span>
                  </div>
                )}
                {cognitiveState.last_synthesis && (
                  <div className="text-xs">
                    <span className="text-muted-foreground">Last Synthesis: </span>
                    <span className="text-foreground font-mono text-[10px]">{cognitiveState.last_synthesis}</span>
                  </div>
                )}
                {cognitiveState.knowledge_graph_concept_ids && (
                  <div className="text-xs">
                    <span className="text-muted-foreground">Knowledge Graph: </span>
                    <span className="text-emerald-400 font-mono">{cognitiveState.knowledge_graph_concept_ids.length} concepts</span>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </motion.div>
      </div>

      {/* Stat Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {statCards.map((stat, i) => (
          <StatCard
            key={stat.label}
            icon={stat.icon}
            label={stat.label}
            value={stat.value}
            suffix={stat.suffix}
            sub={stat.sub}
            delay={0.3 + i * 0.1}
            gradient={stat.gradient}
          />
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Tab: Knowledge Graph                                               */
/* ------------------------------------------------------------------ */

function KnowledgeGraphTab({ data }: { data: RuntimeData }) {
  const { concepts, relationships, stats } = data;
  const [expandedConcept, setExpandedConcept] = useState<string | null>(null);

  return (
    <div className="space-y-8">
      {/* Concept Type Distribution */}
      <div>
        <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
          <Layers className="w-4 h-4 text-emerald-400" />
          Concept Type Distribution
        </h3>
        <div className="flex flex-wrap gap-2">
          {Object.entries(stats.conceptTypes).map(([type, count]) => (
            <Tooltip key={type}>
              <TooltipTrigger asChild>
                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.3 }}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 cursor-default hover:bg-emerald-500/15 transition-colors"
                >
                  <span className="text-xs text-emerald-400 font-mono font-bold">{count}</span>
                  <span className="text-xs text-muted-foreground">{type}</span>
                </motion.div>
              </TooltipTrigger>
              <TooltipContent>
                <p>{count} concepts of type &quot;{type}&quot;</p>
              </TooltipContent>
            </Tooltip>
          ))}
        </div>
      </div>

      {/* Relationship Type Distribution */}
      <div>
        <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-teal-400" />
          Relationship Type Distribution
        </h3>
        <div className="flex flex-wrap gap-2">
          {Object.entries(stats.relationshipTypes).map(([type, count]) => {
            const colors = getRelationshipColor(type);
            return (
              <Tooltip key={type}>
                <TooltipTrigger asChild>
                  <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.3 }}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full ${colors.bg} border ${colors.border} cursor-default hover:opacity-80 transition-opacity`}
                  >
                    <span className={`text-xs font-mono font-bold ${colors.text}`}>{count}</span>
                    <span className="text-xs text-muted-foreground">{type.replace(/_/g, " ")}</span>
                  </motion.div>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{count} relationships of type &quot;{type}&quot;</p>
                </TooltipContent>
              </Tooltip>
            );
          })}
        </div>
      </div>

      {/* Concepts List */}
      <div>
        <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
          <Network className="w-4 h-4 text-emerald-400" />
          Concepts
          <Badge className="text-[10px] font-mono bg-emerald-500/15 text-emerald-400 border-emerald-500/25">
            {concepts.length}
          </Badge>
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-96 overflow-y-auto pr-1">
          {concepts.map((concept, i) => (
            <motion.div
              key={concept.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: Math.min(i * 0.03, 0.5) }}
            >
              <Card
                className="border-border/30 card-hover-lift cursor-pointer"
                onClick={() => setExpandedConcept(expandedConcept === concept.id ? null : concept.id)}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-sm font-semibold text-foreground truncate">{concept.name}</span>
                    </div>
                    <Badge className="text-[9px] font-mono bg-emerald-500/10 text-emerald-400 border-emerald-500/20 flex-shrink-0">
                      {concept.concept_type}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-[10px] text-muted-foreground font-mono">Confidence</span>
                    <span className="text-[10px] text-emerald-400 font-mono font-bold">{Math.round(concept.confidence * 100)}%</span>
                  </div>
                  <ConfidenceBar value={concept.confidence} />
                  <AnimatePresence>
                    {expandedConcept === concept.id && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                      >
                        <div className="pt-2 mt-2 border-t border-border/20">
                          {concept.description && (
                            <p className="text-xs text-muted-foreground mb-1">{concept.description}</p>
                          )}
                          <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <Eye className="w-3 h-3" />
                              {concept.access_count} accesses
                            </span>
                            <span className="flex items-center gap-1">
                              <Hash className="w-3 h-3" />
                              {concept.id.slice(0, 8)}
                            </span>
                          </div>
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

      {/* Relationships List */}
      <div>
        <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-teal-400" />
          Relationships
          <Badge className="text-[10px] font-mono bg-teal-500/15 text-teal-400 border-teal-500/25">
            {relationships.length}
          </Badge>
        </h3>
        <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
          {relationships.map((rel, i) => {
            const colors = getRelationshipColor(rel.relationship_type);
            return (
              <motion.div
                key={rel.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: Math.min(i * 0.03, 0.5) }}
                className={`p-3 rounded-lg ${colors.bg} border ${colors.border} card-hover-lift`}
              >
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  <span className="text-xs font-semibold text-foreground">{rel.source_name}</span>
                  <ArrowRight className={`w-3 h-3 ${colors.text} flex-shrink-0`} />
                  <Badge className={`text-[9px] font-mono ${colors.bg} ${colors.text} border ${colors.border}`}>
                    {rel.relationship_type.replace(/_/g, " ")}
                  </Badge>
                  <ArrowRight className={`w-3 h-3 ${colors.text} flex-shrink-0`} />
                  <span className="text-xs font-semibold text-foreground">{rel.target_name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-muted-foreground font-mono">Confidence</span>
                  <div className="flex-1">
                    <ConfidenceBar value={rel.confidence} colorClass={colors.bar} />
                  </div>
                  <span className={`text-[10px] font-mono font-bold ${colors.text}`}>
                    {Math.round(rel.confidence * 100)}%
                  </span>
                </div>
                {rel.description && (
                  <p className="text-[10px] text-muted-foreground mt-1">{rel.description}</p>
                )}
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Belief Evidence Details (Expandable)                                */
/* ------------------------------------------------------------------ */

function BeliefEvidenceDetails({ belief }: { belief: Belief }) {
  const [expanded, setExpanded] = useState(false);
  // Safely count evidence - handle cases where arrays might contain non-object items
  const safeEvidence = (arr: unknown[]): EvidenceItem[] =>
    Array.isArray(arr) ? arr.filter((ev): ev is EvidenceItem => ev != null && typeof ev === "object" && "id" in ev) : [];
  const supportingSafe = safeEvidence(belief.supporting_evidence as unknown[] ?? []);
  const contradictingSafe = safeEvidence(belief.contradicting_evidence as unknown[] ?? []);
  const hasEvidence = supportingSafe.length > 0 || contradictingSafe.length > 0;

  if (!hasEvidence) return null;

  // Safely render content - convert objects to strings
  const safeContent = (content: unknown): string => {
    if (content == null) return "";
    if (typeof content === "string") return content;
    if (typeof content === "number" || typeof content === "boolean") return String(content);
    return JSON.stringify(content);
  };

  return (
    <div className="mt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
      >
        <ChevronDown className={`w-3 h-3 transition-transform ${expanded ? "rotate-180" : ""}`} />
        {expanded ? "Hide" : "Show"} evidence details
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="pt-2 mt-2 border-t border-border/20 space-y-2">
              {supportingSafe.map((ev) => (
                <div key={ev.id} className="flex items-start gap-2 text-[10px]">
                  <CheckCircle className="w-3 h-3 text-green-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="text-foreground">{safeContent(ev.content)}</span>
                    <span className="text-muted-foreground ml-2 font-mono">{Math.round((ev.confidence ?? 0) * 100)}%</span>
                  </div>
                </div>
              ))}
              {contradictingSafe.map((ev) => (
                <div key={ev.id} className="flex items-start gap-2 text-[10px]">
                  <AlertTriangle className="w-3 h-3 text-red-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="text-foreground">{safeContent(ev.content)}</span>
                    <span className="text-muted-foreground ml-2 font-mono">{Math.round((ev.confidence ?? 0) * 100)}%</span>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Tab: Beliefs                                                       */
/* ------------------------------------------------------------------ */

function BeliefsTab({ data }: { data: RuntimeData }) {
  const { beliefs, stats } = data;

  // Sort by confidence descending
  const sortedBeliefs = [...beliefs].sort((a, b) => b.confidence - a.confidence);

  // Confidence distribution buckets
  const confidenceBuckets = [
    { label: "0-20%", min: 0, max: 0.2, color: "bg-red-500" },
    { label: "20-40%", min: 0.2, max: 0.4, color: "bg-amber-500" },
    { label: "40-60%", min: 0.4, max: 0.6, color: "bg-yellow-500" },
    { label: "60-80%", min: 0.6, max: 0.8, color: "bg-green-500" },
    { label: "80-100%", min: 0.8, max: 1.0, color: "bg-emerald-500" },
  ];

  const bucketCounts = confidenceBuckets.map((bucket) => ({
    ...bucket,
    count: beliefs.filter((b) => b.confidence >= bucket.min && b.confidence < bucket.max).length +
      (bucket.max === 1.0 ? beliefs.filter((b) => b.confidence === 1.0).length : 0),
  }));

  const maxBucketCount = Math.max(...bucketCounts.map((b) => b.count), 1);

  return (
    <div className="space-y-8">
      {/* Belief Summary Stats */}
      <div className="grid grid-cols-3 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/15 text-center card-hover-lift"
        >
          <div className="text-2xl font-bold text-emerald-400">{stats.activeBeliefs}</div>
          <div className="text-[10px] text-muted-foreground font-mono uppercase mt-1">Active</div>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
          className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/15 text-center card-hover-lift"
        >
          <div className="text-2xl font-bold text-amber-400">{stats.weakenedBeliefs}</div>
          <div className="text-[10px] text-muted-foreground font-mono uppercase mt-1">Weakened</div>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
          className="p-4 rounded-xl bg-slate-500/5 border border-slate-500/15 text-center card-hover-lift"
        >
          <div className="text-2xl font-bold text-foreground">{stats.totalBeliefs}</div>
          <div className="text-[10px] text-muted-foreground font-mono uppercase mt-1">Total</div>
        </motion.div>
      </div>

      {/* Confidence Distribution */}
      <div>
        <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-emerald-400" />
          Confidence Distribution
        </h3>
        <div className="p-4 rounded-xl bg-card/50 border border-border/30">
          <div className="flex items-end gap-2 h-28">
            {bucketCounts.map((bucket) => (
              <div key={bucket.label} className="flex-1 flex flex-col items-center gap-1">
                <span className="text-[10px] font-mono text-muted-foreground">{bucket.count}</span>
                <motion.div
                  initial={{ height: 0 }}
                  animate={{ height: `${(bucket.count / maxBucketCount) * 80}px` }}
                  transition={{ duration: 0.6, ease: "easeOut" }}
                  className={`w-full rounded-t ${bucket.color} min-h-[2px]`}
                />
                <span className="text-[8px] text-muted-foreground font-mono text-center">{bucket.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Belief Cards */}
      <div>
        <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
          <Shield className="w-4 h-4 text-emerald-400" />
          All Beliefs
          <Badge className="text-[10px] font-mono bg-emerald-500/15 text-emerald-400 border-emerald-500/25">
            {sortedBeliefs.length}
          </Badge>
        </h3>
        <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
          {sortedBeliefs.map((belief, i) => {
            const isActive = belief.status.toUpperCase() === "ACTIVE";
            return (
              <motion.div
                key={belief.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: Math.min(i * 0.03, 0.5) }}
              >
                <Card className="border-border/30 card-hover-lift">
                  <CardContent className="p-4">
                    {/* Statement & Status */}
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <p className="text-sm text-foreground leading-relaxed flex-1">{belief.statement}</p>
                      <BeliefStatusBadge status={belief.status} />
                    </div>

                    {/* Confidence Bar */}
                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-[10px] text-muted-foreground font-mono w-16">Confidence</span>
                      <div className="flex-1">
                        <ConfidenceBar
                          value={belief.confidence}
                          colorClass={isActive ? "bg-emerald-500" : "bg-amber-500"}
                        />
                      </div>
                      <span className={`text-[10px] font-mono font-bold ${isActive ? "text-emerald-400" : "text-amber-400"}`}>
                        {Math.round(belief.confidence * 100)}%
                      </span>
                    </div>

                    {/* Evidence & Meta */}
                    <div className="flex items-center gap-4 text-[10px]">
                      <span className="flex items-center gap-1 text-green-400">
                        <CheckCircle className="w-3 h-3" />
                        {belief.supporting_evidence_count} supporting
                      </span>
                      {belief.contradicting_evidence_count > 0 && (
                        <span className="flex items-center gap-1 text-red-400">
                          <AlertTriangle className="w-3 h-3" />
                          {belief.contradicting_evidence_count} contradicting
                        </span>
                      )}
                      <span className="flex items-center gap-1 text-muted-foreground ml-auto">
                        <Hash className="w-3 h-3" />
                        v{belief.version}
                      </span>
                      {belief.category && (
                        <Badge className="text-[9px] font-mono bg-slate-500/10 text-slate-400 border-slate-500/20">
                          {belief.category}
                        </Badge>
                      )}
                    </div>

                    {/* Expandable Evidence Details */}
                    <BeliefEvidenceDetails belief={belief} />
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
/*  Tab: Goals                                                         */
/* ------------------------------------------------------------------ */

function GoalsTab({ data }: { data: RuntimeData }) {
  const { goals, stats } = data;
  const [sortBy, setSortBy] = useState<"priority" | "progress">("priority");

  const sortedGoals = useCallback(() => {
    const priorityOrder: Record<string, number> = { CRITICAL: 0, HIGH: 1, NORMAL: 2, LOW: 3 };
    const getPriorityKey = (p: string | number) => {
      const s = typeof p === "number"
        ? (p >= 20 ? "CRITICAL" : p >= 15 ? "HIGH" : p >= 10 ? "NORMAL" : "LOW")
        : String(p).toUpperCase();
      return s;
    };
    return [...goals].sort((a, b) => {
      if (sortBy === "priority") {
        return (priorityOrder[getPriorityKey(a.priority)] ?? 99) - (priorityOrder[getPriorityKey(b.priority)] ?? 99);
      }
      return b.progress - a.progress;
    });
  }, [goals, sortBy])();

  return (
    <div className="space-y-8">
      {/* Progress Overview */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="p-6 rounded-xl bg-card/50 border border-emerald-500/15 card-hover-lift"
      >
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <Target className="w-4 h-4 text-emerald-400" />
            Average Goal Progress
          </h3>
          <span className="text-sm font-bold text-emerald-400">{Math.round(stats.avgGoalProgress * 100)}%</span>
        </div>
        <Progress value={stats.avgGoalProgress * 100} className="h-3" />
        <div className="grid grid-cols-3 gap-4 mt-4">
          <div className="text-center">
            <div className="text-lg font-bold text-emerald-400">{stats.activeGoals}</div>
            <div className="text-[10px] text-muted-foreground font-mono">ACTIVE</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-green-400">{stats.completedGoals}</div>
            <div className="text-[10px] text-muted-foreground font-mono">COMPLETED</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-amber-400">{stats.pausedGoals}</div>
            <div className="text-[10px] text-muted-foreground font-mono">PAUSED</div>
          </div>
        </div>
      </motion.div>

      {/* Sort Controls */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Sort by:</span>
        <button
          onClick={() => setSortBy("priority")}
          className={`px-3 py-1 rounded-md text-xs font-mono transition-colors ${
            sortBy === "priority"
              ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25"
              : "bg-muted/30 text-muted-foreground border border-transparent hover:text-foreground"
          }`}
        >
          Priority
        </button>
        <button
          onClick={() => setSortBy("progress")}
          className={`px-3 py-1 rounded-md text-xs font-mono transition-colors ${
            sortBy === "progress"
              ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25"
              : "bg-muted/30 text-muted-foreground border border-transparent hover:text-foreground"
          }`}
        >
          Progress
        </button>
      </div>

      {/* Goal Cards */}
      <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
        {sortedGoals.map((goal, i) => (
          <motion.div
            key={goal.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: Math.min(i * 0.03, 0.5) }}
          >
            <Card className="border-border/30 card-hover-lift">
              <CardContent className="p-4">
                {/* Description, Priority & Status */}
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="flex items-start gap-2 min-w-0 flex-1">
                    <GoalStatusIcon status={goal.status} />
                    <p className="text-sm text-foreground leading-relaxed">{goal.description}</p>
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <PriorityBadge priority={goal.priority} />
                    <GoalStatusBadge status={goal.status} />
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-[10px] text-muted-foreground font-mono w-14">Progress</span>
                  <div className="flex-1">
                    <div className="w-full h-2.5 rounded-full bg-muted/30 overflow-hidden">
                      <motion.div
                        className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400"
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.round(goal.progress * 100)}%` }}
                        transition={{ duration: 0.8, ease: "easeOut" }}
                      />
                    </div>
                  </div>
                  <span className="text-[10px] font-mono font-bold text-emerald-400">
                    {Math.round(goal.progress * 100)}%
                  </span>
                </div>

                {/* Subgoals & Dependencies */}
                <div className="flex items-center gap-4 text-[10px] text-muted-foreground">
                  {goal.subgoal_ids && goal.subgoal_ids.length > 0 && (
                    <span className="flex items-center gap-1">
                      <Layers className="w-3 h-3" />
                      {goal.subgoal_ids.length} subgoal{goal.subgoal_ids.length !== 1 ? "s" : ""}
                    </span>
                  )}
                  {goal.dependency_ids && goal.dependency_ids.length > 0 && (
                    <span className="flex items-center gap-1">
                      <GitBranch className="w-3 h-3" />
                      {goal.dependency_ids.length} dependenc{goal.dependency_ids.length !== 1 ? "ies" : "y"}
                    </span>
                  )}
                  <span className="flex items-center gap-1 ml-auto">
                    <Hash className="w-3 h-3" />
                    {goal.id.slice(0, 8)}
                  </span>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main RuntimeDashboard Component                                    */
/* ------------------------------------------------------------------ */

export function RuntimeDashboard() {
  const [data, setData] = useState<RuntimeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch("/api/acos-runtime");
      if (!res.ok) throw new Error("Failed to fetch runtime data");
      const json = await res.json();
      setData(json);
      setLastRefresh(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading && !data) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 rounded-lg bg-emerald-600/10 flex items-center justify-center">
            <Activity className="w-5 h-5 text-emerald-400 animate-pulse" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-foreground">ACOS Runtime Dashboard</h2>
            <p className="text-xs text-muted-foreground font-mono">Loading cognitive state...</p>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-32 rounded-xl bg-card/50 border border-border/30 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 rounded-lg bg-emerald-600/10 flex items-center justify-center">
            <Activity className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-foreground">ACOS Runtime Dashboard</h2>
            <p className="text-xs text-muted-foreground font-mono">Error loading data</p>
          </div>
        </div>
        <Card className="border-red-500/20 bg-red-500/5">
          <CardContent className="p-6 text-center">
            <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-3" />
            <p className="text-sm text-red-400 mb-2">Failed to load ACOS Runtime data</p>
            <p className="text-xs text-muted-foreground mb-4">{error}</p>
            <button
              onClick={fetchData}
              className="px-4 py-2 rounded-lg bg-emerald-600/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono hover:bg-emerald-600/20 transition-colors"
            >
              <RefreshCw className="w-3 h-3 inline mr-1" />
              Retry
            </button>
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
          <div className="w-8 h-8 rounded-lg bg-emerald-600/10 flex items-center justify-center">
            <Activity className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-foreground">ACOS Runtime Dashboard</h2>
            <p className="text-xs text-muted-foreground font-mono">
              Live cognitive state &middot; v{data.version}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-muted-foreground font-mono">
            Updated {lastRefresh.toLocaleTimeString()}
          </span>
          <button
            onClick={fetchData}
            className="p-2 rounded-lg bg-emerald-600/10 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-600/20 transition-colors"
            aria-label="Refresh data"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Tabbed Content */}
      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="w-full sm:w-auto">
          <TabsTrigger value="overview" className="gap-1.5">
            <Brain className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Overview</span>
          </TabsTrigger>
          <TabsTrigger value="knowledge" className="gap-1.5">
            <Network className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Knowledge Graph</span>
          </TabsTrigger>
          <TabsTrigger value="beliefs" className="gap-1.5">
            <Shield className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Beliefs</span>
          </TabsTrigger>
          <TabsTrigger value="goals" className="gap-1.5">
            <Target className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Goals</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <OverviewTab data={data} />
        </TabsContent>
        <TabsContent value="knowledge">
          <KnowledgeGraphTab data={data} />
        </TabsContent>
        <TabsContent value="beliefs">
          <BeliefsTab data={data} />
        </TabsContent>
        <TabsContent value="goals">
          <GoalsTab data={data} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
