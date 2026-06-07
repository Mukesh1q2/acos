"use client";

import { motion } from "framer-motion";
import { Brain, ShieldCheck, Lightbulb, Zap, AlertCircle, Cpu, Network, RefreshCw, GitBranch } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

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

const innovationColorMap: Record<string, { bg: string; border: string; icon: string }> = {
  emerald: { bg: "bg-emerald-500/10", border: "border-emerald-500/20", icon: "text-emerald-400" },
  teal: { bg: "bg-teal-500/10", border: "border-teal-500/20", icon: "text-teal-400" },
  green: { bg: "bg-green-500/10", border: "border-green-500/20", icon: "text-green-400" },
  cyan: { bg: "bg-cyan-500/10", border: "border-cyan-500/20", icon: "text-cyan-400" },
};

const stackLayers = [
  { name: "Cognitive Agent Framework", color: "bg-emerald-700", textColor: "text-white" },
  { name: "Knowledge Fabric", color: "bg-emerald-600", textColor: "text-white" },
  { name: "Hierarchical Memory", color: "bg-teal-600", textColor: "text-white" },
  { name: "Multi-Thread Reasoning Engine", color: "bg-teal-700", textColor: "text-white" },
  { name: "AFM (Avadhan Foundation Model)", color: "bg-slate-700", textColor: "text-white" },
  { name: "Cognitive Kernel (OS Layer)", color: "bg-slate-800 border border-slate-600", textColor: "text-slate-200" },
];

const valuePropositions = [
  {
    icon: <RefreshCw className="w-6 h-6" />,
    title: "Continuous Learning",
    desc: "The system that never forgets — orthogonal gradient projection preserves all prior knowledge",
    gradient: "from-emerald-500/20 to-emerald-600/5",
    border: "border-emerald-500/20",
  },
  {
    icon: <GitBranch className="w-6 h-6" />,
    title: "Orthogonal Threads",
    desc: "Zero interference reasoning — mathematically proven thread isolation via Stiefel Manifold",
    gradient: "from-teal-500/20 to-teal-600/5",
    border: "border-teal-500/20",
  },
  {
    icon: <Brain className="w-6 h-6" />,
    title: "Neuro-Symbolic",
    desc: "Logic meets learning — Panini constraints and Nyaya verification integrated with neural reasoning",
    gradient: "from-green-500/20 to-green-600/5",
    border: "border-green-500/20",
  },
];

export function OverviewSection() {
  return (
    <div className="relative overflow-hidden">
      {/* Animated gradient background */}
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-900/30 via-slate-950 to-teal-900/20 animate-gradient" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_oklch(0.696_0.17_162.48/0.1),_transparent_50%)]" />

      <div className="relative z-10 px-6 py-16 md:py-24 max-w-5xl mx-auto">
        {/* Title */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7 }}
          className="text-center mb-12"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-600/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono mb-6">
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
          <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto">
            The Operating System for Cognitive Intelligence
          </p>
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
              className={`relative p-6 rounded-xl bg-gradient-to-br ${item.gradient} border ${item.border} backdrop-blur-sm group hover:scale-[1.02] hover:shadow-lg hover:shadow-emerald-500/5 transition-all duration-300`}
            >
              <div className="text-emerald-400 mb-3 group-hover:text-emerald-300 transition-colors duration-300">{item.icon}</div>
              <h3 className="text-lg font-semibold text-foreground mb-2">
                {item.title}
              </h3>
              <p className="text-sm text-muted-foreground">{item.desc}</p>
            </motion.div>
          ))}
        </motion.div>

        {/* Key stats */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.7 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-16"
        >
          {[
            { label: "O(N log N) Scaling", sub: "Hierarchical Binary Tree Attention", icon: <Zap className="w-5 h-5" /> },
            { label: "Proven Thread Isolation", sub: "Stiefel Manifold guarantee", icon: <ShieldCheck className="w-5 h-5" /> },
            { label: "3-Tier Memory", sub: "Working - Episodic - Semantic", icon: <Lightbulb className="w-5 h-5" /> },
          ].map((stat) => (
            <div
              key={stat.label}
              className="flex items-center gap-4 p-4 rounded-lg bg-card/50 border border-border/30"
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

        {/* Architecture Stack Diagram */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.9 }}
        >
          <h2 className="text-lg font-semibold text-foreground mb-6 text-center">
            The ACOS Stack
          </h2>
          <div className="max-w-lg mx-auto space-y-2">
            {stackLayers.map((layer, i) => (
              <motion.div
                key={layer.name}
                initial={{ opacity: 0, scaleX: 0.5 }}
                animate={{ opacity: 1, scaleX: 1 }}
                transition={{ duration: 0.4, delay: 1 + i * 0.1 }}
                className={`${layer.color} ${layer.textColor} text-center py-3 px-4 rounded-lg text-sm font-medium cursor-default hover:scale-[1.03] hover:shadow-lg hover:shadow-emerald-500/10 transition-all duration-200`}
              >
                {layer.name}
              </motion.div>
            ))}
          </div>

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
                    ? "bg-emerald-600/10 border-emerald-500/30 hover:bg-emerald-600/15"
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
          transition={{ duration: 0.6, delay: 1.3 }}
          className="mt-16"
        >
          <h2 className="text-lg font-semibold text-foreground mb-6 text-center">
            Key Technical Innovations
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {keyInnovations.map((inn, i) => {
              const colors = innovationColorMap[inn.color];
              return (
                <motion.div
                  key={inn.title}
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: 1.4 + i * 0.1 }}
                >
                  <Card className={`border-border/30 h-full hover:${colors.border} hover:shadow-md hover:shadow-emerald-500/5 transition-all duration-300`}>
                    <CardContent className="p-4">
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
          transition={{ duration: 0.6, delay: 1.8 }}
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
                    transition={{ delay: 2 + corr.num * 0.05 }}
                    className="flex items-start gap-2 p-2 rounded-md bg-amber-500/5 border border-amber-500/10"
                  >
                    <Badge
                      variant="outline"
                      className="text-[9px] bg-amber-500/15 text-amber-400 border-amber-500/25 flex-shrink-0 mt-0.5"
                    >
                      #{corr.num}
                    </Badge>
                    <span className="text-xs text-foreground">{corr.correction}</span>
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
