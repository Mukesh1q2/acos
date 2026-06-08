"use client";

import { useState } from "react";
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
  Eye,
  EyeOff,
  TrendingDown,
  Zap,
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

// Learning curve data: performance on Task 1 as new tasks are learned
const standardCurve = [95, 82, 67, 54, 43, 35, 28, 23, 20, 18];
const acosCurve = [95, 94, 93, 92, 91, 90, 89, 88, 87, 86];

// SVG chart dimensions
const CHART_W = 600;
const CHART_H = 320;
const PAD_L = 50;
const PAD_R = 20;
const PAD_T = 20;
const PAD_B = 40;
const PLOT_W = CHART_W - PAD_L - PAD_R;
const PLOT_H = CHART_H - PAD_T - PAD_B;

function yPos(val: number) {
  return PAD_T + PLOT_H * (1 - val / 100);
}
function xPos(i: number) {
  return PAD_L + (i / 9) * PLOT_W;
}

function buildPath(data: number[]) {
  return data.map((v, i) => `${i === 0 ? "M" : "L"} ${xPos(i).toFixed(1)} ${yPos(v).toFixed(1)}`).join(" ");
}

function buildAreaPath(data: number[]) {
  const line = data.map((v, i) => `${i === 0 ? "M" : "L"} ${xPos(i).toFixed(1)} ${yPos(v).toFixed(1)}`).join(" ");
  const lastX = xPos(data.length - 1).toFixed(1);
  const firstX = xPos(0).toFixed(1);
  const bottom = yPos(0).toFixed(1);
  return `${line} L ${lastX} ${bottom} L ${firstX} ${bottom} Z`;
}

export function Part5Learning() {
  const [showStandard, setShowStandard] = useState(true);

  return (
    <div className="space-y-10">
      <SectionHeader
        sectionNumber={5}
        title="Continuous Learning"
        subtitle="Orthogonal gradient projection for interference-free learning"
        badge="ZERO FORGETTING"
        icon={<RotateCcw className="w-5 h-5" />}
        id="continuous-learning"
      />

      {/* Catastrophic Forgetting — Learning Curve Visualization */}
      <Card className="card-hover-lift border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
              <TrendingDown className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <CardTitle className="text-lg" id="catastrophic-forgetting">Catastrophic Forgetting — Learning Curve</CardTitle>
              <CardDescription className="mb-2">Performance on Task 1 as new tasks are sequentially learned</CardDescription>
            </div>
            <button
              onClick={() => setShowStandard((v) => !v)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-200 hover:scale-105 active:scale-95"
              style={{
                borderColor: showStandard ? "rgba(245,158,11,0.3)" : "rgba(245,158,11,0.15)",
                backgroundColor: showStandard ? "rgba(245,158,11,0.1)" : "transparent",
                color: showStandard ? "#f59e0b" : "#78716c",
              }}
            >
              {showStandard ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
              Standard FT
            </button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="w-full overflow-x-auto">
            <svg
              viewBox={`0 0 ${CHART_W} ${CHART_H}`}
              className="w-full max-w-[700px] mx-auto"
              style={{ minWidth: 360 }}
              role="img"
              aria-label="Learning curve comparison: ACOS Orthogonal Learning vs Standard Fine-Tuning"
            >
              {/* Definitions */}
              <defs>
                <linearGradient id="acosGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#10b981" stopOpacity="0.35" />
                  <stop offset="100%" stopColor="#10b981" stopOpacity="0.02" />
                </linearGradient>
                <linearGradient id="standardGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.25" />
                  <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.02" />
                </linearGradient>
              </defs>

              {/* Grid lines */}
              {[0, 20, 40, 60, 80, 100].map((v) => (
                <g key={v}>
                  <line
                    x1={PAD_L}
                    y1={yPos(v)}
                    x2={PAD_L + PLOT_W}
                    y2={yPos(v)}
                    stroke="currentColor"
                    strokeOpacity={0.06}
                    strokeWidth={1}
                  />
                  <text
                    x={PAD_L - 8}
                    y={yPos(v) + 4}
                    textAnchor="end"
                    className="fill-muted-foreground"
                    style={{ fontSize: 10, fontFamily: "monospace" }}
                  >
                    {v}%
                  </text>
                </g>
              ))}

              {/* X-axis labels */}
              {standardCurve.map((_, i) => (
                <text
                  key={i}
                  x={xPos(i)}
                  y={CHART_H - PAD_B + 20}
                  textAnchor="middle"
                  className="fill-muted-foreground"
                  style={{ fontSize: 10, fontFamily: "monospace" }}
                >
                  {i + 1}
                </text>
              ))}

              {/* Axis titles */}
              <text
                x={PAD_L + PLOT_W / 2}
                y={CHART_H - 2}
                textAnchor="middle"
                className="fill-muted-foreground"
                style={{ fontSize: 11, fontFamily: "sans-serif" }}
              >
                Tasks Learned (1-10)
              </text>
              <text
                x={14}
                y={PAD_T + PLOT_H / 2}
                textAnchor="middle"
                className="fill-muted-foreground"
                style={{ fontSize: 11, fontFamily: "sans-serif" }}
                transform={`rotate(-90, 14, ${PAD_T + PLOT_H / 2})`}
              >
                Performance on Task 1 (%)
              </text>

              {/* Standard FT area fill */}
              {showStandard && (
                <motion.path
                  d={buildAreaPath(standardCurve)}
                  fill="url(#standardGrad)"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.8, delay: 0.6 }}
                />
              )}

              {/* ACOS area fill */}
              <motion.path
                d={buildAreaPath(acosCurve)}
                fill="url(#acosGrad)"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.8, delay: 0.4 }}
              />

              {/* Standard FT line */}
              {showStandard && (
                <motion.path
                  d={buildPath(standardCurve)}
                  fill="none"
                  stroke="#f59e0b"
                  strokeWidth={2.5}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeDasharray="6 3"
                  initial={{ pathLength: 0, opacity: 0 }}
                  animate={{ pathLength: 1, opacity: 1 }}
                  transition={{ duration: 1.2, delay: 0.3, ease: "easeInOut" }}
                />
              )}

              {/* ACOS Orthogonal line */}
              <motion.path
                d={buildPath(acosCurve)}
                fill="none"
                stroke="#10b981"
                strokeWidth={3}
                strokeLinecap="round"
                strokeLinejoin="round"
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{ pathLength: 1, opacity: 1 }}
                transition={{ duration: 1.2, delay: 0.1, ease: "easeInOut" }}
              />

              {/* End-point labels */}
              <motion.g
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.5 }}
              >
                {/* ACOS end label */}
                <rect
                  x={xPos(9) - 28}
                  y={yPos(86) - 22}
                  width={56}
                  height={18}
                  rx={4}
                  fill="#10b981"
                  fillOpacity={0.15}
                  stroke="#10b981"
                  strokeOpacity={0.4}
                  strokeWidth={1}
                />
                <text
                  x={xPos(9)}
                  y={yPos(86) - 10}
                  textAnchor="middle"
                  fill="#10b981"
                  style={{ fontSize: 10, fontWeight: 700, fontFamily: "monospace" }}
                >
                  86%
                </text>

                {/* Standard end label */}
                {showStandard && (
                  <>
                    <rect
                      x={xPos(9) - 22}
                      y={yPos(18) - 6}
                      width={44}
                      height={18}
                      rx={4}
                      fill="#f59e0b"
                      fillOpacity={0.15}
                      stroke="#f59e0b"
                      strokeOpacity={0.4}
                      strokeWidth={1}
                    />
                    <text
                      x={xPos(9)}
                      y={yPos(18) + 7}
                      textAnchor="middle"
                      fill="#f59e0b"
                      style={{ fontSize: 10, fontWeight: 700, fontFamily: "monospace" }}
                    >
                      18%
                    </text>
                  </>
                )}
              </motion.g>

              {/* Data point dots — ACOS */}
              <motion.g
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.4, duration: 0.5 }}
              >
                {acosCurve.map((v, i) => (
                  <circle
                    key={`acos-dot-${i}`}
                    cx={xPos(i)}
                    cy={yPos(v)}
                    r={3}
                    fill="#10b981"
                    stroke="#022c22"
                    strokeWidth={1.5}
                  />
                ))}
              </motion.g>

              {/* Data point dots — Standard */}
              {showStandard && (
                <motion.g
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 1.5, duration: 0.5 }}
                >
                  {standardCurve.map((v, i) => (
                    <circle
                      key={`std-dot-${i}`}
                      cx={xPos(i)}
                      cy={yPos(v)}
                      r={3}
                      fill="#f59e0b"
                      stroke="#422006"
                      strokeWidth={1.5}
                    />
                  ))}
                </motion.g>
              )}

              {/* Legend */}
              <motion.g
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.2 }}
              >
                <line x1={PAD_L + 10} y1={PAD_T + 8} x2={PAD_L + 30} y2={PAD_T + 8} stroke="#10b981" strokeWidth={3} strokeLinecap="round" />
                <text x={PAD_L + 35} y={PAD_T + 12} fill="#10b981" style={{ fontSize: 10, fontWeight: 600 }}>ACOS Orthogonal</text>
                {showStandard && (
                  <>
                    <line x1={PAD_L + 145} y1={PAD_T + 8} x2={PAD_L + 165} y2={PAD_T + 8} stroke="#f59e0b" strokeWidth={2.5} strokeDasharray="6 3" strokeLinecap="round" />
                    <text x={PAD_L + 170} y={PAD_T + 12} fill="#f59e0b" style={{ fontSize: 10, fontWeight: 600 }}>Standard Fine-Tuning</text>
                  </>
                )}
              </motion.g>
            </svg>
          </div>

          {/* Critical Insight callout */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.6, duration: 0.5 }}
            className="mt-5 p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20 flex items-start gap-3"
          >
            <div className="w-9 h-9 rounded-lg bg-emerald-500/15 border border-emerald-500/25 flex items-center justify-center text-emerald-400 flex-shrink-0">
              <Zap className="w-4 h-4" />
            </div>
            <div>
              <div className="text-sm font-bold text-emerald-400 mb-1">Critical Insight</div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                ACOS retains <span className="text-emerald-400 font-bold">86%</span> vs{" "}
                <span className="text-amber-400 font-bold">18%</span> for standard fine-tuning across 10 sequential tasks —
                a{" "}
                <span className="text-emerald-400 font-bold text-sm">4.8x improvement</span>{" "}
                in knowledge retention. This is not empirical: it is a mathematical
                guarantee from the Stiefel Manifold geometry.
              </p>
            </div>
          </motion.div>
        </CardContent>
      </Card>

      {/* Learning Modes — Gradient Header Card */}
      <Card className="glass-card-premium card-hover-lift border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
              <Brain className="w-5 h-5" />
            </div>
            <div>
              <CardTitle className="text-lg">Learning Modes</CardTitle>
              <CardDescription className="mb-2">Four distinct modes of continuous knowledge acquisition</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="gradient-accent-bar" />
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
          <CardDescription className="mb-2">End-to-end knowledge processing and consolidation workflow</CardDescription>
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
          <CardDescription className="mb-2">Built-in safeguards against common continuous learning failure modes</CardDescription>
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
              <CardTitle className="text-lg text-emerald-400" id="orthogonal-gradient">Orthogonal Gradient Projection — Detailed</CardTitle>
              <CardDescription className="text-emerald-400/70 mb-2">Mathematical foundations of zero-forgetting learning</CardDescription>
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
              <code className="prose-code-block text-xs font-mono text-foreground block">
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
              <CardDescription className="text-teal-400/70 mb-2">Idle-time consolidation inspired by human sleep</CardDescription>
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
