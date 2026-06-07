"use client";

import { useEffect, useState, useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Brain, ShieldCheck, Lightbulb, Zap, AlertCircle, Cpu, Network, RefreshCw, GitBranch, Activity, Database, Users, Layers } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { InteractiveArchitecture } from "@/components/acos/interactive-architecture";

/* ------------------------------------------------------------------ */
/*  Animated Counter Hook                                              */
/* ------------------------------------------------------------------ */

function useAnimatedCounter(target: number, duration: number = 2000, startOnView: boolean = true) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true });
  const hasStarted = useRef(false);

  useEffect(() => {
    if (startOnView && !isInView) return;
    if (hasStarted.current) return;
    hasStarted.current = true;

    const startTime = Date.now();
    const step = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.round(eased * target));
      if (progress < 1) {
        requestAnimationFrame(step);
      }
    };
    requestAnimationFrame(step);
  }, [isInView, startOnView, target, duration]);

  return { count, ref };
}

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

const keyInnovations = [
  {
    icon: <Zap className="w-5 h-5" />,
    title: "O(N log N) Attention",
    description: "Hierarchical Binary Tree Attention achieves logarithmic scaling through gated-sum broadcast. Crossover point: N > d*logN ~ 4,608 for d=512",
    color: "emerald",
  },
  {
    icon: <Network className="w-5 h-5" />,
    title: "Orthogonal Thread Memory",
    description: "Stiefel Manifold St(d,K) parameterization ensures S^T*S = I_k, giving mathematically proven zero inter-thread interference: <S_i, S_j> = 0 for all i != j",
    color: "teal",
  },
  {
    icon: <Brain className="w-5 h-5" />,
    title: "Three-Tier Memory",
    description: "Working Memory (Stiefel matrix S_t), Episodic Memory (HNSW vector store), Semantic Memory (Knowledge Graph). Retrieval in O(d*logM).",
    color: "green",
  },
  {
    icon: <Cpu className="w-5 h-5" />,
    title: "Neuro-Symbolic Kernel",
    description: "Pingala routing, Panini constraints (differentiable product logic AND/OR/NOT), Nyaya verification (MLP energy function with smooth rejection sampling).",
    color: "cyan",
  },
];

const v2Corrections = [
  { num: 1, correction: "Leaf concatenation -> gated-sum broadcast" },
  { num: 2, correction: "Complexity domination statement corrected" },
  { num: 3, correction: "Minimum sequence length N* made explicit" },
  { num: 4, correction: "Theorem 4.6 approximation error downgraded to Plausible" },
  { num: 5, correction: "Controller Lyapunov stability narrowed to local" },
  { num: 6, correction: "Engineering prescription for fp16 Riemannian drift added" },
  { num: 7, correction: "epsilon term identified as structural, not noise-based" },
];

const innovationColorMap: Record<string, { bg: string; border: string; icon: string; hoverBg: string }> = {
  emerald: { bg: "bg-emerald-500/10", border: "border-emerald-500/20", icon: "text-emerald-400", hoverBg: "hover:border-emerald-500/40" },
  teal: { bg: "bg-teal-500/10", border: "border-teal-500/20", icon: "text-teal-400", hoverBg: "hover:border-teal-500/40" },
  green: { bg: "bg-green-500/10", border: "border-green-500/20", icon: "text-green-400", hoverBg: "hover:border-green-500/40" },
  cyan: { bg: "bg-cyan-500/10", border: "border-cyan-500/20", icon: "text-cyan-400", hoverBg: "hover:border-cyan-500/40" },
};

const valuePropositions = [
  {
    icon: <RefreshCw className="w-6 h-6" />,
    title: "Continuous Learning",
    desc: "The system that never forgets — orthogonal gradient projection preserves all prior knowledge",
    gradient: "from-emerald-500/20 to-emerald-600/5",
    border: "border-emerald-500/20",
    hoverBorder: "hover:border-emerald-500/40",
  },
  {
    icon: <GitBranch className="w-6 h-6" />,
    title: "Orthogonal Threads",
    desc: "Zero interference reasoning — mathematically proven thread isolation via Stiefel Manifold",
    gradient: "from-teal-500/20 to-teal-600/5",
    border: "border-teal-500/20",
    hoverBorder: "hover:border-teal-500/40",
  },
  {
    icon: <Brain className="w-6 h-6" />,
    title: "Neuro-Symbolic",
    desc: "Logic meets learning — Panini constraints and Nyaya verification integrated with neural reasoning",
    gradient: "from-green-500/20 to-green-600/5",
    border: "border-green-500/20",
    hoverBorder: "hover:border-green-500/40",
  },
];

/* Stats with animated counters */
const metricStats = [
  { value: 77, suffix: "x", label: "Attention Speedup", sub: "at N=32K tokens", icon: <Activity className="w-5 h-5" /> },
  { value: 250, suffix: "x", label: "Memory Reduction", sub: "vs KV Cache", icon: <Database className="w-5 h-5" /> },
  { value: 86, suffix: "%", label: "Knowledge Retention", sub: "after 10 tasks", icon: <Users className="w-5 h-5" /> },
  { value: 0, suffix: "", label: "Thread Interference", sub: "proven by construction", icon: <Layers className="w-5 h-5" /> },
];

/* ------------------------------------------------------------------ */
/*  Counter Stat Card                                                  */
/* ------------------------------------------------------------------ */

function CounterStat({ stat, delay }: { stat: typeof metricStats[0]; delay: number }) {
  const { count, ref } = useAnimatedCounter(stat.value, 1800);

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="relative p-5 rounded-xl bg-card/50 border border-border/30 card-hover-lift group overflow-hidden"
    >
      {/* Shimmer on hover */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 animate-shimmer transition-opacity duration-500" />

      <div className="relative z-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-lg bg-emerald-600/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            {stat.icon}
          </div>
          <div className="text-xs text-muted-foreground font-mono uppercase tracking-wider">{stat.label}</div>
        </div>
        <div className="flex items-baseline gap-1">
          <span className="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
            {stat.value === 0 ? "0" : count}
          </span>
          {stat.suffix && (
            <span className="text-lg font-semibold text-emerald-400">{stat.suffix}</span>
          )}
        </div>
        <div className="text-xs text-muted-foreground mt-1">{stat.sub}</div>
      </div>
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export function OverviewSection() {
  return (
    <div className="relative overflow-hidden">
      {/* Animated gradient background */}
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-900/30 via-slate-950 to-teal-900/20 animate-gradient" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_oklch(0.696_0.17_162.48/0.1),_transparent_50%)]" />
      {/* Dot grid pattern */}
      <div className="absolute inset-0 bg-dot-grid" />

      {/* Decorative rotating circle */}
      <div className="absolute top-20 right-10 w-64 h-64 opacity-[0.03] animate-spin-slow pointer-events-none">
        <svg viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="100" cy="100" r="90" stroke="currentColor" strokeWidth="0.5" className="text-emerald-400" />
          <circle cx="100" cy="100" r="70" stroke="currentColor" strokeWidth="0.5" className="text-emerald-400" />
          <circle cx="100" cy="100" r="50" stroke="currentColor" strokeWidth="0.5" className="text-emerald-400" />
          <line x1="10" y1="100" x2="190" y2="100" stroke="currentColor" strokeWidth="0.3" className="text-emerald-400" />
          <line x1="100" y1="10" x2="100" y2="190" stroke="currentColor" strokeWidth="0.3" className="text-emerald-400" />
        </svg>
      </div>

      {/* Second decorative element */}
      <div className="absolute bottom-40 left-5 w-48 h-48 opacity-[0.02] animate-spin-slow pointer-events-none" style={{ animationDirection: "reverse" }}>
        <svg viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="20" y="20" width="160" height="160" stroke="currentColor" strokeWidth="0.5" className="text-teal-400" rx="20" />
          <rect x="40" y="40" width="120" height="120" stroke="currentColor" strokeWidth="0.5" className="text-teal-400" rx="15" />
          <rect x="60" y="60" width="80" height="80" stroke="currentColor" strokeWidth="0.5" className="text-teal-400" rx="10" />
        </svg>
      </div>

      <div className="relative z-10 px-6 py-16 md:py-24 max-w-5xl mx-auto">
        {/* Title */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7 }}
          className="text-center mb-12"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-600/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono mb-6">
            <Zap className="w-3 h-3" />
            BRAHM AI RESEARCH INITIATIVE
          </div>
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight mb-4">
            <span className="relative inline-block">
              <span className="bg-gradient-to-r from-emerald-400 via-teal-400 to-emerald-300 bg-clip-text text-transparent animate-pulse-glow">
                AVADHAN
              </span>
              <span className="absolute inset-0 bg-gradient-to-r from-emerald-400/20 via-teal-400/20 to-emerald-300/20 blur-xl animate-pulse-glow" aria-hidden="true" />
            </span>
            <br />
            <span className="text-foreground">COGNITIVE OPERATING SYSTEM</span>
          </h1>
          <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            The Operating System for Cognitive Intelligence
          </p>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="text-sm text-muted-foreground/60 max-w-xl mx-auto mt-3"
          >
            Not another chatbot. A complete cognitive infrastructure for reasoning, memory, and continuous learning.
          </motion.p>
          {/* Hero architecture image */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.6 }}
            className="mt-8 relative max-w-3xl mx-auto rounded-xl overflow-hidden border border-emerald-500/20 shadow-2xl shadow-emerald-500/10"
          >
            <img
              src="/acos-hero.png"
              alt="ACOS Architecture - Cognitive Operating System Stack Visualization"
              className="w-full h-auto object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-slate-950/80 via-transparent to-transparent" />
            <div className="absolute bottom-3 left-4 text-[10px] text-emerald-400/60 font-mono">
              ACOS Cognitive Stack Architecture
            </div>
          </motion.div>
        </motion.div>

        {/* Three value propositions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16"
        >
          {valuePropositions.map((item, i) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.4 + i * 0.15 }}
              className={`relative p-6 rounded-xl bg-gradient-to-br ${item.gradient} border ${item.border} ${item.hoverBorder} backdrop-blur-sm group hover:scale-[1.02] hover:shadow-lg hover:shadow-emerald-500/5 transition-all duration-300 card-hover-lift`}
            >
              {/* Corner accent */}
              <div className="absolute top-0 right-0 w-16 h-16 overflow-hidden rounded-tr-xl">
                <div className="absolute -top-8 -right-8 w-16 h-16 bg-gradient-to-bl from-emerald-500/10 to-transparent rotate-45" />
              </div>

              <div className="text-emerald-400 mb-3 group-hover:text-emerald-300 transition-colors duration-300">{item.icon}</div>
              <h3 className="text-lg font-semibold text-foreground mb-2">
                {item.title}
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{item.desc}</p>
            </motion.div>
          ))}
        </motion.div>

        {/* Animated Counter Stats */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.6 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-16"
        >
          {metricStats.map((stat, i) => (
            <CounterStat key={stat.label} stat={stat} delay={0.7 + i * 0.12} />
          ))}
        </motion.div>

        {/* Key stats row (original, kept for context) */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.9 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-16"
        >
          {[
            { label: "O(N log N) Scaling", sub: "Hierarchical Binary Tree Attention", icon: <Zap className="w-5 h-5" /> },
            { label: "Proven Thread Isolation", sub: "Stiefel Manifold guarantee", icon: <ShieldCheck className="w-5 h-5" /> },
            { label: "3-Tier Memory", sub: "Working - Episodic - Semantic", icon: <Lightbulb className="w-5 h-5" /> },
          ].map((stat) => (
            <div
              key={stat.label}
              className="flex items-center gap-4 p-4 rounded-lg bg-card/50 border border-border/30 card-hover-lift"
            >
              <div className="w-10 h-10 rounded-lg bg-emerald-600/10 flex items-center justify-center text-emerald-400 flex-shrink-0">
                {stat.icon}
              </div>
              <div>
                <div className="text-sm font-bold text-foreground">{stat.label}</div>
                <div className="text-xs text-muted-foreground">{stat.sub}</div>
              </div>
            </div>
          ))}
        </motion.div>

        {/* Interactive Architecture Stack Diagram */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 1.1 }}
        >
          <h2 className="text-lg font-semibold text-foreground mb-6 text-center">
            The ACOS Stack
          </h2>
          <InteractiveArchitecture />

          {/* OS Analogy */}
          <div className="mt-8 grid grid-cols-3 gap-4 text-center max-w-lg mx-auto">
            {[
              { os: "Windows", desc: "OS for Computers" },
              { os: "Android", desc: "OS for Mobile" },
              { os: "ACOS", desc: "OS for Cognitive Intelligence", highlight: true },
            ].map((item) => (
              <div
                key={item.os}
                className={`p-3 rounded-lg border transition-all duration-200 hover:scale-[1.03] ${
                  item.highlight
                    ? "bg-emerald-600/10 border-emerald-500/30 hover:bg-emerald-600/15 hover:shadow-md hover:shadow-emerald-500/10"
                    : "bg-card/30 border-border/20 hover:bg-card/50"
                }`}
              >
                <div
                  className={`text-sm font-bold ${item.highlight ? "text-emerald-400" : "text-muted-foreground"}`}
                >
                  {item.os}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  {item.desc}
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Key Technical Innovations */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 1.5 }}
          className="mt-16"
        >
          <h2 className="text-lg font-semibold text-foreground mb-6 text-center">
            Key Technical Innovations
          </h2>
          {/* Brain network visualization */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, delay: 1.55 }}
            className="mb-8 relative max-w-md mx-auto rounded-xl overflow-hidden border border-emerald-500/15 shadow-xl shadow-emerald-500/5"
          >
            <img
              src="/acos-brain.png"
              alt="Neural network visualization representing ACOS cognitive architecture"
              className="w-full h-auto object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-slate-950/60 via-transparent to-transparent" />
          </motion.div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {keyInnovations.map((inn, i) => {
              const colors = innovationColorMap[inn.color];
              return (
                <motion.div
                  key={inn.title}
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: 1.6 + i * 0.1 }}
                  className="card-hover-lift"
                >
                  <Card className={`border-border/30 h-full ${colors.hoverBg} hover:shadow-md hover:shadow-emerald-500/5 transition-all duration-300`}>
                    <CardContent className="p-5">
                      <div className="flex items-start gap-3">
                        <div className={`w-10 h-10 rounded-lg ${colors.bg} ${colors.border} border flex items-center justify-center ${colors.icon} flex-shrink-0`}>
                          {inn.icon}
                        </div>
                        <div>
                          <div className="text-sm font-semibold text-foreground mb-1">
                            {inn.title}
                          </div>
                          <p className="text-xs text-muted-foreground leading-relaxed">
                            {inn.description}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </div>
        </motion.div>

        {/* v2 Corrections Summary */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 2 }}
          className="mt-8"
        >
          <Card className="border-amber-500/20 bg-gradient-to-r from-amber-900/10 to-amber-950/5">
            <CardHeader>
              <div className="flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-amber-400" />
                <CardTitle className="text-lg text-amber-400">AHC v2 Corrections Summary</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground mb-4">
                Key corrections from the Avadhan Hierarchical Cognition v2 paper that refine the theoretical foundations:
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {v2Corrections.map((corr) => (
                  <motion.div
                    key={corr.num}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 2.2 + corr.num * 0.05 }}
                    className="flex items-start gap-2 p-2.5 rounded-md bg-amber-500/5 border border-amber-500/10 hover:bg-amber-500/8 transition-colors duration-200"
                  >
                    <Badge
                      variant="outline"
                      className="text-[9px] bg-amber-500/15 text-amber-400 border-amber-500/25 flex-shrink-0 mt-0.5"
                    >
                      #{corr.num}
                    </Badge>
                    <span className="text-xs text-foreground leading-relaxed">{corr.correction}</span>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
