"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Cpu,
  Layers,
  Database,
  GitBranch,
  Users,
  Clock,
  Zap,
  Brain,
  Code,
  FlaskConical,
  HardDrive,
  ShieldCheck,
  MapPin,
  Sparkles,
  MessageSquare,
  ArrowRight,
  Monitor,
  Smartphone,
} from "lucide-react";

const coreComponents = [
  {
    title: "Cognitive Kernel",
    icon: <Cpu className="w-5 h-5" />,
    color: "emerald",
    description: "The core OS layer managing processes, memory, and scheduling",
    items: [
      { name: "Process Manager", desc: "Thread lifecycle management" },
      { name: "Memory Manager", desc: "Hierarchical memory allocation" },
      { name: "Scheduler", desc: "Lyapunov-Guided Scheduling for stability" },
    ],
  },
  {
    title: "Multi-Thread Reasoning Engine",
    icon: <Layers className="w-5 h-5" />,
    color: "teal",
    description: "8 specialized thread types with proven isolation guarantees",
    items: [
      { name: "Analytical", icon: <Brain className="w-3 h-3" /> },
      { name: "Mathematical", icon: <Zap className="w-3 h-3" /> },
      { name: "Coding", icon: <Code className="w-3 h-3" /> },
      { name: "Scientific", icon: <FlaskConical className="w-3 h-3" /> },
      { name: "Memory Retrieval", icon: <HardDrive className="w-3 h-3" /> },
      { name: "Verification", icon: <ShieldCheck className="w-3 h-3" /> },
      { name: "Planning", icon: <MapPin className="w-3 h-3" /> },
      { name: "Creative", icon: <Sparkles className="w-3 h-3" /> },
    ],
    isThreadGrid: true,
  },
  {
    title: "Hierarchical Memory Architecture",
    icon: <Database className="w-5 h-5" />,
    color: "green",
    description: "5-tier memory system inspired by human cognition",
    items: [
      { name: "Working Memory", desc: "8K tokens - Instant", speed: 100 },
      { name: "Episodic Memory", desc: "100K tokens - Fast", speed: 80 },
      { name: "Semantic Memory", desc: "1M+ vectors - Medium", speed: 50 },
      { name: "Long-Term Memory", desc: "10M+ vectors - Slow", speed: 25 },
      { name: "Procedural Memory", desc: "Unlimited - Compiled", speed: 90 },
    ],
    isMemory: true,
  },
  {
    title: "Knowledge Fabric",
    icon: <GitBranch className="w-5 h-5" />,
    color: "cyan",
    description: "Unified knowledge representation across multiple paradigms",
    items: [
      { name: "Knowledge Graph", desc: "Entity-relationship structured knowledge" },
      { name: "Vector DB", desc: "Semantic similarity search" },
      { name: "Symbolic Layer", desc: "Panini constraint integration" },
      { name: "Citation Tracking", desc: "Provenance and source verification" },
    ],
  },
  {
    title: "Cognitive Agent Framework",
    icon: <Users className="w-5 h-5" />,
    color: "lime",
    description: "7 specialized agent types with cooperation model",
    items: [
      { name: "Reasoning Agent", desc: "Logical deduction and inference" },
      { name: "Coding Agent", desc: "Code generation and debugging" },
      { name: "Research Agent", desc: "Information retrieval and synthesis" },
      { name: "Verification Agent", desc: "Output validation and fact-checking" },
      { name: "Planning Agent", desc: "Task decomposition and scheduling" },
      { name: "Creative Agent", desc: "Generative and divergent thinking" },
      { name: "Memory Agent", desc: "Knowledge consolidation and retrieval" },
    ],
  },
];

const colorMap: Record<string, { bg: string; border: string; icon: string; badge: string }> = {
  emerald: {
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/20",
    icon: "text-emerald-400",
    badge: "bg-emerald-500/20 text-emerald-400",
  },
  teal: {
    bg: "bg-teal-500/10",
    border: "border-teal-500/20",
    icon: "text-teal-400",
    badge: "bg-teal-500/20 text-teal-400",
  },
  green: {
    bg: "bg-green-500/10",
    border: "border-green-500/20",
    icon: "text-green-400",
    badge: "bg-green-500/20 text-green-400",
  },
  cyan: {
    bg: "bg-cyan-500/10",
    border: "border-cyan-500/20",
    icon: "text-cyan-400",
    badge: "bg-cyan-500/20 text-cyan-400",
  },
  lime: {
    bg: "bg-lime-500/10",
    border: "border-lime-500/20",
    icon: "text-lime-400",
    badge: "bg-lime-500/20 text-lime-400",
  },
};

const osAnalogyItems = [
  { os: "Windows", desc: "OS for Computers", IconComponent: Monitor },
  { os: "Android", desc: "OS for Mobile", IconComponent: Smartphone },
  { os: "ACOS", desc: "OS for Cognitive Intelligence", IconComponent: Brain, highlight: true },
];

export function Part2ACOS() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-2">
          Part 2 — ACOS Design
        </h2>
        <p className="text-muted-foreground">
          The Avadhan Cognitive Operating System — 5 core components forming the
          complete OS for cognitive intelligence.
        </p>
      </div>

      {/* OS Analogy */}
      <Card className="border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardContent className="p-6">
          <div className="flex flex-col md:flex-row items-center justify-center gap-8 text-center">
            {osAnalogyItems.map((item, i) => {
              const IconComp = item.IconComponent;
              return (
                <motion.div
                  key={item.os}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.2 }}
                  className={`p-4 rounded-xl border ${
                    item.highlight
                      ? "border-emerald-500/30 bg-emerald-600/10 scale-110"
                      : "border-border/20 bg-card/30"
                  }`}
                >
                  <div className="flex justify-center mb-2">
                    <IconComp className={`w-7 h-7 ${item.highlight ? "text-emerald-400" : "text-muted-foreground"}`} />
                  </div>
                  <div className={`text-lg font-bold ${item.highlight ? "text-emerald-400" : "text-foreground"}`}>
                    {item.os}
                  </div>
                  <div className="text-xs text-muted-foreground">{item.desc}</div>
                </motion.div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Core Components */}
      <div className="space-y-6">
        {coreComponents.map((comp, i) => {
          const colors = colorMap[comp.color];
          return (
            <motion.div
              key={comp.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: i * 0.1 }}
            >
              <Card className={`border-border/30 hover:${colors.border} transition-colors duration-300`}>
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg ${colors.bg} ${colors.border} border flex items-center justify-center ${colors.icon}`}>
                      {comp.icon}
                    </div>
                    <div>
                      <CardTitle className="text-lg">{comp.title}</CardTitle>
                      <CardDescription className="text-xs">
                        {comp.description}
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  {comp.isThreadGrid ? (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                      {comp.items.map((item) => (
                        <div
                          key={item.name}
                          className="flex items-center gap-2 p-2 rounded-md bg-muted/30 border border-border/20"
                        >
                          <span className={colors.icon}>{item.icon}</span>
                          <span className="text-xs font-medium">{item.name}</span>
                        </div>
                      ))}
                    </div>
                  ) : comp.isMemory ? (
                    <div className="space-y-2">
                      {comp.items.map((item) => {
                        const memItem = item as { name: string; desc: string; speed: number };
                        return (
                          <div
                            key={memItem.name}
                            className="flex items-center gap-3 p-2 rounded-md bg-muted/20"
                          >
                            <div className="flex-1">
                              <div className="text-sm font-medium">{memItem.name}</div>
                              <div className="text-xs text-muted-foreground">{memItem.desc}</div>
                            </div>
                            <div className="w-24 h-2 rounded-full bg-muted overflow-hidden">
                              <motion.div
                                className={`h-full rounded-full ${
                                  memItem.speed > 75
                                    ? "bg-emerald-500"
                                    : memItem.speed > 40
                                      ? "bg-teal-500"
                                      : "bg-amber-500"
                                }`}
                                initial={{ width: 0 }}
                                animate={{ width: `${memItem.speed}%` }}
                                transition={{ duration: 0.8, delay: 0.2 }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {comp.items.map((item) => (
                        <div
                          key={item.name}
                          className="p-3 rounded-md bg-muted/20 border border-border/10"
                        >
                          <div className="text-sm font-medium">{item.name}</div>
                          <div className="text-xs text-muted-foreground mt-0.5">
                            {item.desc}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </div>

      {/* Cognitive Kernel — Enhanced Technical Details */}
      <Card className="border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-emerald-400" />
            <CardTitle className="text-lg text-emerald-400">Cognitive Kernel — Technical Details</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="p-4 rounded-lg bg-card/50 border border-emerald-500/15"
            >
              <div className="text-sm font-semibold text-emerald-400 mb-2">Lyapunov-Guided Scheduling</div>
              <code className="text-xs font-mono text-foreground block bg-card/50 p-3 rounded-md border border-border/10 mb-2">
                V(h,a) = -R(S,a) + u/2*||a||^2 + v/2*||h||^2
              </code>
              <p className="text-xs text-muted-foreground">
                The Lyapunov function V decreases monotonically during scheduling, guaranteeing stability. a controls thread allocation, h is hidden state.
              </p>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="p-4 rounded-lg bg-card/50 border border-emerald-500/15"
            >
              <div className="text-sm font-semibold text-emerald-400 mb-2">Thread Allocation</div>
              <p className="text-xs text-muted-foreground mb-2">
                Resources are allocated to the thread with the highest gradient of value:
              </p>
              <code className="text-xs font-mono text-foreground block bg-card/50 p-3 rounded-md border border-border/10">
                k* = argmax_k ||grad_(&#123;S_k&#125;) V(h,a)||
              </code>
              <p className="text-xs text-muted-foreground mt-2">
                This ensures compute is directed to the thread that would benefit most from additional processing.
              </p>
            </motion.div>
          </div>
        </CardContent>
      </Card>

      {/* Multi-Thread Reasoning — Inter-Thread Communication */}
      <Card className="border-teal-500/20 bg-gradient-to-r from-teal-900/10 to-emerald-900/10">
        <CardHeader>
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-teal-400" />
            <CardTitle className="text-lg text-teal-400">Inter-Thread Communication</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-start gap-3 p-3 rounded-lg bg-card/50 border border-teal-500/15">
              <ArrowRight className="w-4 h-4 text-teal-400 flex-shrink-0 mt-0.5" />
              <div>
                <div className="text-sm font-semibold">Global Context Vector</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Threads communicate via Global Context Vector from HBTA top-down broadcast. Each thread receives context from the hierarchical tree without direct message passing.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 rounded-lg bg-card/50 border border-teal-500/15">
              <ShieldCheck className="w-4 h-4 text-teal-400 flex-shrink-0 mt-0.5" />
              <div>
                <div className="text-sm font-semibold">Thread Isolation Guarantee</div>
                <code className="text-xs font-mono text-foreground block bg-card/50 p-2 rounded-md border border-border/10 mt-1">
                  S_i^T . S_j = 0 (proven) -&gt; Contamination-free by construction
                </code>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Hierarchical Memory — Consolidation */}
      <Card className="border-green-500/20 bg-gradient-to-r from-green-900/10 to-teal-900/10">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-green-400" />
            <CardTitle className="text-lg text-green-400">Memory Consolidation</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-lg bg-card/50 border border-green-500/15">
              <div className="text-sm font-semibold text-green-400 mb-2">Sphota Bottleneck</div>
              <p className="text-xs text-muted-foreground">
                Autoencoder compresses Working Memory M_W to Episodic Memory M_E during sleep phase. The Sphota bottleneck learns a compressed representation that preserves essential information while discarding noise.
              </p>
            </div>
            <div className="p-4 rounded-lg bg-card/50 border border-green-500/15">
              <div className="text-sm font-semibold text-green-400 mb-2">Memory Decay</div>
              <p className="text-xs text-muted-foreground">
                Vectors are pruned if retrieval probability drops below threshold. This prevents memory bloat while ensuring frequently accessed knowledge is retained. Decay rate is configurable per memory tier.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Knowledge Fabric — Data Sources */}
      <Card className="border-cyan-500/20 bg-gradient-to-r from-cyan-900/10 to-teal-900/10">
        <CardHeader>
          <div className="flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-cyan-400" />
            <CardTitle className="text-lg text-cyan-400">Knowledge Fabric — Data Sources</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {[
              "Wikipedia", "Research Papers", "Books", "PDFs",
              "Databases", "APIs", "User Documents", "Websites",
              "Enterprise Data", "Code Repos", "News Feeds", "Scientific Data",
            ].map((source, i) => (
              <motion.div
                key={source}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.03 }}
                className="flex items-center justify-center p-2 rounded-md bg-muted/20 border border-border/20 text-xs font-medium text-center"
              >
                {source}
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
