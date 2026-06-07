"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  BookOpen,
  FileText,
  Globe,
  Building2,
  ShieldCheck,
  RotateCcw,
  AlertTriangle,
  Brain,
  Moon,
  RefreshCw,
  ArrowRight,
} from "lucide-react";
import { SectionHeader } from "./section-header";
import { FlowChart } from "./flow-chart";

const learningModes = [
  { id: "user", label: "User Learning", icon: <BookOpen className="w-4 h-4" />, desc: "Adapts to individual user preferences and patterns", color: "bg-emerald-900/50 border-emerald-500/30" },
  { id: "document", label: "Document Learning", icon: <FileText className="w-4 h-4" />, desc: "Ingests and learns from uploaded documents and files", color: "bg-teal-900/50 border-teal-500/30" },
  { id: "web", label: "Web Learning", icon: <Globe className="w-4 h-4" />, desc: "Continuously learns from web sources and real-time data", color: "bg-cyan-900/50 border-cyan-500/30" },
  { id: "enterprise", label: "Enterprise Learning", icon: <Building2 className="w-4 h-4" />, desc: "Learns organizational knowledge and processes", color: "bg-green-900/50 border-green-500/30" },
];

const preventionMechanisms = [
  {
    problem: "Catastrophic Forgetting",
    solution: "Orthogonal gradient projection",
    description: "Stiefel Manifold ensures new learning doesn't overwrite prior knowledge by projecting gradients onto orthogonal subspace",
    status: "Proven" as const,
    risk: "low",
  },
  {
    problem: "Hallucination Amplification",
    solution: "Nyaya Verifier scoring",
    description: "Every generated output passes through Nyaya verification to catch and prevent hallucination propagation",
    status: "Plausible" as const,
    risk: "medium",
  },
  {
    problem: "Memory Corruption",
    solution: "QR re-orthogonalization",
    description: "Periodic QR decomposition ensures thread memory matrices maintain orthogonality despite numerical drift",
    status: "Proven (Theory)" as const,
    risk: "medium",
  },
  {
    problem: "Knowledge Drift",
    solution: "Entropy regularizer",
    description: "Entropy-based regularization prevents knowledge from drifting too far from verified facts over time",
    status: "Plausible" as const,
    risk: "low",
  },
];

const learningFlowSteps = [
  { id: "input", label: "New Knowledge", description: "User/Document/Web", color: "bg-slate-800 border-slate-600" },
  { id: "encode", label: "Encode", description: "Feature extraction", color: "bg-emerald-900/50 border-emerald-500/30" },
  { id: "project", label: "Orthogonal Project", description: "Stiefel gradient", color: "bg-teal-900/50 border-teal-500/30" },
  { id: "verify", label: "Nyaya Verify", description: "Consistency check", color: "bg-amber-900/30 border-amber-500/30" },
  { id: "consolidate", label: "Consolidate", description: "Sleep phase", color: "bg-green-900/50 border-green-500/30" },
];

const riskColors: Record<string, string> = {
  low: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  medium: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  high: "bg-red-500/20 text-red-400 border-red-500/30",
};

const sleepCycleSteps = [
  { step: "Sample", desc: "Sample from Episodic Memory M_E", icon: <BookOpen className="w-4 h-4" /> },
  { step: "Rehearse", desc: "Rehearse on past experiences", icon: <RefreshCw className="w-4 h-4" /> },
  { step: "Consolidate", desc: "Consolidate short-term → long-term", icon: <ArrowRight className="w-4 h-4" /> },
  { step: "Re-orthogonalize", desc: "QR re-orthogonalization of S_t", icon: <ShieldCheck className="w-4 h-4" /> },
  { step: "Idle", desc: "Run during idle time", icon: <Moon className="w-4 h-4" /> },
];

export function Part5Learning() {
  return (
    <div className="space-y-8">
      <SectionHeader
        sectionNumber={5}
        title="Continuous Learning"
        subtitle="Orthogonal gradient projection for interference-free learning"
        badge="ZERO FORGETTING"
        icon={<RotateCcw className="w-5 h-5" />}
        id="continuous-learning"
      />

      {/* Learning Modes — Gradient Header Card */}
      <Card className="card-hover-lift border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
              <Brain className="w-5 h-5" />
            </div>
            <div>
              <CardTitle className="text-lg">Learning Modes</CardTitle>
              <CardDescription>Four distinct modes of continuous knowledge acquisition</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {learningModes.map((mode, i) => (
              <motion.div
                key={mode.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className="p-4 rounded-lg bg-card/50 border border-border/20"
              >
                <div className="flex items-start gap-3">
                  <div className={`w-10 h-10 rounded-lg ${mode.color} border flex items-center justify-center text-emerald-400 flex-shrink-0`}>
                    {mode.icon}
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-foreground">
                      {mode.label}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {mode.desc}
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Learning Flow Diagram */}
      <Card className="card-hover-lift border-border/30">
        <CardHeader>
          <CardTitle className="text-lg">Learning Pipeline</CardTitle>
          <CardDescription>End-to-end knowledge processing and consolidation workflow</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto pb-2">
            <FlowChart steps={learningFlowSteps} direction="horizontal" />
          </div>
          <div className="mt-4 p-3 rounded-lg bg-muted/20 border border-border/20">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
                <RotateCcw className="w-4 h-4" />
              </div>
              <span className="text-sm font-semibold">Memory Consolidation (Sleep Phase)</span>
            </div>
            <p className="text-xs text-muted-foreground">
              During idle periods, ACOS samples from episodic memory, rehearses
              important patterns, and consolidates short-term memories into
              long-term semantic knowledge. This is analogous to human sleep
              consolidation.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Prevention Mechanisms */}
      <Card className="card-hover-lift border-border/30">
        <CardHeader>
          <CardTitle className="text-lg">Prevention Mechanisms</CardTitle>
          <CardDescription>Built-in safeguards against common continuous learning failure modes</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {preventionMechanisms.map((mech, i) => (
              <motion.div
                key={mech.problem}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className="flex flex-col md:flex-row md:items-center gap-3 p-4 rounded-lg bg-muted/20 border border-border/20"
              >
                <div className="flex items-center gap-2 min-w-[180px]">
                  <AlertTriangle className={`w-4 h-4 flex-shrink-0 ${
                    mech.risk === "low" ? "text-emerald-400" : "text-amber-400"
                  }`} />
                  <span className="text-sm font-semibold">{mech.problem}</span>
                </div>
                <div className="flex items-center gap-2 min-w-[160px]">
                  <ShieldCheck className="w-3.5 h-3.5 text-teal-400 flex-shrink-0" />
                  <span className="text-xs font-mono text-teal-400">
                    {mech.solution}
                  </span>
                </div>
                <div className="text-xs text-muted-foreground flex-1">
                  {mech.description}
                </div>
                <Badge
                  variant="outline"
                  className={`text-[10px] ${riskColors[mech.risk]}`}
                >
                  {mech.risk} risk
                </Badge>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Key Insight */}
      <Card className="card-hover-lift border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardContent className="p-6">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
              <Brain className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-semibold text-foreground mb-1">
                Key Innovation: Orthogonal Gradient Projection
              </div>
              <p className="text-xs text-muted-foreground">
                Unlike conventional fine-tuning which overwrites prior knowledge,
                ACOS natively supports continuous learning through the Stiefel
                Manifold. New gradients are projected onto the orthogonal
                complement of prior knowledge, ensuring zero interference. This
                is mathematically guaranteed, not empirically observed.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Orthogonal Gradient Projection — Detailed */}
      <Card className="card-hover-lift border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
              <Brain className="w-5 h-5" />
            </div>
            <div>
              <CardTitle className="text-lg text-emerald-400">Orthogonal Gradient Projection — Detailed</CardTitle>
              <CardDescription className="text-emerald-400/70">Mathematical foundations of zero-forgetting learning</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="p-4 rounded-lg bg-card/50 border border-emerald-500/15"
            >
              <div className="text-sm font-semibold text-emerald-400 mb-2">The Problem</div>
              <p className="text-xs text-muted-foreground">
                When learning task A, standard gradient descent updates all parameters. This can degrade performance on previously learned task B — catastrophic forgetting.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="p-4 rounded-lg bg-card/50 border border-emerald-500/15"
            >
              <div className="text-sm font-semibold text-emerald-400 mb-2">The Solution</div>
              <p className="text-xs text-muted-foreground mb-2">
                When learning task A, compute gradients grad_L_A. Project onto orthogonal complement of important directions for task B:
              </p>
              <code className="text-xs font-mono text-foreground block bg-card/50 p-3 rounded-md border border-border/10">
                grad_tilde_L_A = grad_L_A - S_B * (S_B^T * grad_L_A)
              </code>
              <p className="text-xs text-muted-foreground mt-2">
                Where S_B contains the important parameter directions for task B stored in the Stiefel matrix. Result: model learns A without degrading B. Natively supported by Stiefel Manifold geometry.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="p-4 rounded-lg bg-card/50 border border-emerald-500/15"
            >
              <div className="text-sm font-semibold text-emerald-400 mb-2">Why It Works</div>
              <p className="text-xs text-muted-foreground">
                The Stiefel Manifold St(d,K) has columns that are mutually orthonormal by construction (S^T S = I_K). The Riemannian gradient automatically projects updates onto the tangent space of the manifold, preventing interference between threads. This is not an approximation — it is a mathematical guarantee from differential geometry.
              </p>
            </motion.div>
          </div>
        </CardContent>
      </Card>

      {/* Sleep Cycle Architecture */}
      <Card className="card-hover-lift border-teal-500/20 bg-gradient-to-r from-teal-900/10 to-green-900/10">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400 flex-shrink-0">
              <Moon className="w-5 h-5" />
            </div>
            <div>
              <CardTitle className="text-lg text-teal-400">Sleep Cycle Architecture</CardTitle>
              <CardDescription className="text-teal-400/70">Idle-time consolidation inspired by human sleep</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {sleepCycleSteps.map((step, i) => (
              <motion.div
                key={step.step}
                initial={{ opacity: 0, x: -15 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className="flex items-center gap-3 p-3 rounded-lg bg-card/50 border border-teal-500/15"
              >
                <div className="w-10 h-10 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400 flex-shrink-0">
                  {step.icon}
                </div>
                <div className="flex-1">
                  <div className="text-sm font-semibold text-teal-400">{step.step}</div>
                  <div className="text-xs text-muted-foreground">{step.desc}</div>
                </div>
                <div className="text-[10px] text-muted-foreground font-mono">
                  Step {i + 1}/{sleepCycleSteps.length}
                </div>
              </motion.div>
            ))}
          </div>

          <div className="mt-4 p-3 rounded-lg bg-muted/20 border border-border/20">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-10 h-10 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400 flex-shrink-0">
                <Moon className="w-4 h-4" />
              </div>
              <span className="text-sm font-semibold">Analogous to Human Sleep</span>
            </div>
            <p className="text-xs text-muted-foreground">
              The sleep cycle runs during idle time (analogous to human sleep), sampling from episodic memory to rehearse past experiences, consolidating short-term knowledge into long-term semantic memory, and performing QR re-orthogonalization to maintain the mathematical integrity of the Stiefel matrix.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
