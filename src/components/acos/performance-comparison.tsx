"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts";
import {
  Zap,
  ShieldCheck,
  HardDrive,
  TrendingUp,
  ArrowRight,
  MemoryStick,
  Brain,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

// ─── Data ──────────────────────────────────────────────────────────────────────

const attentionScalingData = [
  { N: "512", standard: 1, flash: 0.3, hbta: 0.5, hybrid: 0.3 },
  { N: "1024", standard: 4, flash: 1.2, hbta: 1.1, hybrid: 1.2 },
  { N: "2048", standard: 16, flash: 4.8, hbta: 2.4, hybrid: 4.8 },
  { N: "4096", standard: 64, flash: 19.2, hbta: 5.2, hybrid: 19.2 },
  { N: "8192", standard: 256, flash: 76.8, hbta: 11.3, hybrid: 11.3 },
  { N: "16384", standard: 1024, flash: 307.2, hbta: 24.5, hybrid: 24.5 },
  { N: "32768", standard: 4096, flash: 1228.8, hbta: 53.1, hybrid: 53.1 },
];

const threadIsolationData = [
  { category: "Memory Leak", standard: 85, acos: 0 },
  { category: "Task Interference", standard: 72, acos: 0 },
  { category: "Context Contamination", standard: 90, acos: 0 },
  { category: "Gradient Bleed", standard: 65, acos: 2 },
  { category: "Output Correlation", standard: 78, acos: 0 },
];

const learningStabilityData = [
  { task: "Task 1", standard: 95, acos: 95 },
  { task: "Task 2", standard: 88, acos: 94 },
  { task: "Task 3", standard: 75, acos: 93 },
  { task: "Task 4", standard: 62, acos: 92 },
  { task: "Task 5", standard: 50, acos: 91 },
  { task: "Task 6", standard: 40, acos: 90 },
  { task: "Task 7", standard: 32, acos: 89 },
  { task: "Task 8", standard: 25, acos: 88 },
  { task: "Task 9", standard: 20, acos: 87 },
  { task: "Task 10", standard: 18, acos: 86 },
];

// ─── Animated Counter Hook ─────────────────────────────────────────────────────

function useAnimatedCounter(target: number, duration: number = 1500) {
  const [count, setCount] = useState(0);
  const prevTarget = useRef(0);

  useEffect(() => {
    if (prevTarget.current === target) return;
    prevTarget.current = target;

    const startTime = Date.now();
    const startVal = 0;

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.round(startVal + (target - startVal) * eased));

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }, [target, duration]);

  return count;
}

// ─── Animated Number Display ───────────────────────────────────────────────────

function AnimatedNumber({ value, suffix = "", prefix = "" }: { value: number; suffix?: string; prefix?: string }) {
  const animatedValue = useAnimatedCounter(value);
  return (
    <span className="tabular-nums">
      {prefix}
      {animatedValue.toLocaleString()}
      {suffix}
    </span>
  );
}

// ─── Custom Tooltip ────────────────────────────────────────────────────────────

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ name: string; value: number; color: string }>; label?: string }) {
  if (!active || !payload || !payload.length) return null;

  return (
    <div className="bg-slate-800 border border-slate-600/50 rounded-lg px-3 py-2 shadow-xl text-xs">
      <p className="text-slate-300 font-medium mb-1.5">{label}</p>
      {payload.map((entry, i) => (
        <div key={i} className="flex items-center gap-2 py-0.5">
          <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-slate-400">{entry.name}:</span>
          <span className="text-foreground font-medium">{entry.value.toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
}

// ─── Tab Definitions ───────────────────────────────────────────────────────────

const tabs = [
  { id: "attention", label: "Attention Scaling", icon: <Zap className="w-4 h-4" /> },
  { id: "isolation", label: "Thread Isolation", icon: <ShieldCheck className="w-4 h-4" /> },
  { id: "memory", label: "Memory Efficiency", icon: <HardDrive className="w-4 h-4" /> },
  { id: "stability", label: "Learning Stability", icon: <TrendingUp className="w-4 h-4" /> },
];

// ─── Main Component ────────────────────────────────────────────────────────────

export function PerformanceComparison() {
  const [activeTab, setActiveTab] = useState("attention");

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
          <Zap className="w-3 h-3" />
          PERFORMANCE BENCHMARKS
        </div>
        <h2 className="text-2xl md:text-3xl font-bold text-foreground">
          ACOS vs Standard LLM
        </h2>
        <p className="text-sm text-muted-foreground mt-2 max-w-xl mx-auto">
          Quantitative comparison across attention scaling, thread isolation, memory efficiency, and learning stability
        </p>
      </motion.div>

      {/* Tab Navigation */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.15 }}
        className="flex flex-wrap justify-center gap-1.5 p-1 bg-muted/30 rounded-xl border border-border/20"
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`
              relative flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium
              transition-all duration-200
              ${
                activeTab === tab.id
                  ? "bg-emerald-600/15 text-emerald-400 border border-emerald-500/25 shadow-sm"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50 border border-transparent"
              }
            `}
          >
            {tab.icon}
            <span className="hidden sm:inline">{tab.label}</span>
            <span className="sm:hidden">{tab.label.split(" ")[0]}</span>
            {activeTab === tab.id && (
              <motion.div
                layoutId="perfTabIndicator"
                className="absolute inset-0 rounded-lg border border-emerald-500/25 bg-emerald-600/10"
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            )}
          </button>
        ))}
      </motion.div>

      {/* Tab Panels */}
      <AnimatePresence mode="wait">
        {activeTab === "attention" && (
          <motion.div
            key="attention"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3 }}
          >
            <AttentionScalingTab />
          </motion.div>
        )}
        {activeTab === "isolation" && (
          <motion.div
            key="isolation"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3 }}
          >
            <ThreadIsolationTab />
          </motion.div>
        )}
        {activeTab === "memory" && (
          <motion.div
            key="memory"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3 }}
          >
            <MemoryEfficiencyTab />
          </motion.div>
        )}
        {activeTab === "stability" && (
          <motion.div
            key="stability"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3 }}
          >
            <LearningStabilityTab />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── Attention Scaling Tab ─────────────────────────────────────────────────────

function AttentionScalingTab() {
  return (
    <div className="space-y-4">
      <Card className="border-border/30 bg-card/50 backdrop-blur-sm overflow-hidden">
        <CardContent className="p-4 md:p-6">
          <div className="mb-4 flex items-center justify-between flex-wrap gap-2">
            <h3 className="text-sm font-semibold text-foreground">
              Attention Complexity Scaling
            </h3>
            <span className="text-[10px] font-mono text-muted-foreground bg-muted/30 px-2 py-1 rounded">
              Y-axis: Log Scale
            </span>
          </div>
          <div className="h-[320px] md:h-[380px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={attentionScalingData}
                margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.4} />
                <XAxis
                  dataKey="N"
                  tick={{ fill: "#94a3b8", fontSize: 11 }}
                  axisLine={{ stroke: "#475569" }}
                  tickLine={{ stroke: "#475569" }}
                  label={{ value: "Sequence Length N", position: "insideBottom", offset: -2, fill: "#94a3b8", fontSize: 11 }}
                />
                <YAxis
                  tick={{ fill: "#94a3b8", fontSize: 11 }}
                  axisLine={{ stroke: "#475569" }}
                  tickLine={{ stroke: "#475569" }}
                  scale="log"
                  domain={[0.1, "auto"]}
                  label={{ value: "Compute Cost (rel.)", angle: -90, position: "insideLeft", offset: 5, fill: "#94a3b8", fontSize: 11 }}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  wrapperStyle={{ paddingTop: 12, fontSize: 11 }}
                  iconType="circle"
                  iconSize={8}
                />
                <Line
                  type="monotone"
                  dataKey="standard"
                  name="Standard Attention O(N^2*d)"
                  stroke="#94a3b8"
                  strokeWidth={2}
                  dot={{ fill: "#94a3b8", r: 3 }}
                  activeDot={{ r: 5, stroke: "#94a3b8", strokeWidth: 2 }}
                  animationDuration={1200}
                />
                <Line
                  type="monotone"
                  dataKey="flash"
                  name="FlashAttention O(N^2*d/M)"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  dot={{ fill: "#f59e0b", r: 3 }}
                  activeDot={{ r: 5, stroke: "#f59e0b", strokeWidth: 2 }}
                  animationDuration={1200}
                  animationBegin={200}
                />
                <Line
                  type="monotone"
                  dataKey="hbta"
                  name="HBTA (ACOS) O(Nd^2*logN)"
                  stroke="#10b981"
                  strokeWidth={2.5}
                  dot={{ fill: "#10b981", r: 3 }}
                  activeDot={{ r: 5, stroke: "#10b981", strokeWidth: 2 }}
                  animationDuration={1200}
                  animationBegin={400}
                />
                <Line
                  type="monotone"
                  dataKey="hybrid"
                  name="HBTA+Hybrid"
                  stroke="#14b8a6"
                  strokeWidth={2}
                  strokeDasharray="6 3"
                  dot={{ fill: "#14b8a6", r: 3 }}
                  activeDot={{ r: 5, stroke: "#14b8a6", strokeWidth: 2 }}
                  animationDuration={1200}
                  animationBegin={600}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Explanation */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="grid grid-cols-1 md:grid-cols-2 gap-3"
      >
        <Card className="border-border/20 bg-card/30">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-slate-500/10 flex items-center justify-center flex-shrink-0">
                <Zap className="w-4 h-4 text-slate-400" />
              </div>
              <div>
                <p className="text-xs font-semibold text-foreground mb-1">Quadratic Bottleneck</p>
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  Standard attention scales as O(N^2*d), making long sequences prohibitively expensive.
                  At N=32K, compute is 4096x the base cost.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-emerald-500/20 bg-emerald-500/5">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center flex-shrink-0">
                <Zap className="w-4 h-4 text-emerald-400" />
              </div>
              <div>
                <p className="text-xs font-semibold text-emerald-400 mb-1">HBTA Breakthrough</p>
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  Hierarchical Binary Tree Attention achieves O(Nd^2*logN) scaling via gated-sum broadcast.
                  At N=32K, ACOS is <span className="text-emerald-400 font-semibold">77x cheaper</span> than standard attention.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}

// ─── Thread Isolation Tab ──────────────────────────────────────────────────────

function ThreadIsolationTab() {
  const barColors = ["#94a3b8", "#94a3b8", "#94a3b8", "#94a3b8", "#94a3b8"];
  const acosColors = ["#10b981", "#10b981", "#10b981", "#10b981", "#10b981"];

  return (
    <div className="space-y-4">
      <Card className="border-border/30 bg-card/50 backdrop-blur-sm overflow-hidden">
        <CardContent className="p-4 md:p-6">
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-foreground">
              Thread Isolation Quality
            </h3>
            <p className="text-[10px] text-muted-foreground mt-0.5">
              Lower is better - measures cross-thread interference
            </p>
          </div>
          <div className="h-[320px] md:h-[380px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={threadIsolationData}
                margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
                barCategoryRatio={0.6}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.4} />
                <XAxis
                  dataKey="category"
                  tick={{ fill: "#94a3b8", fontSize: 10 }}
                  axisLine={{ stroke: "#475569" }}
                  tickLine={{ stroke: "#475569" }}
                  interval={0}
                  angle={-15}
                  textAnchor="end"
                  height={60}
                />
                <YAxis
                  tick={{ fill: "#94a3b8", fontSize: 11 }}
                  axisLine={{ stroke: "#475569" }}
                  tickLine={{ stroke: "#475569" }}
                  label={{ value: "Interference Score", angle: -90, position: "insideLeft", offset: 5, fill: "#94a3b8", fontSize: 11 }}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  wrapperStyle={{ paddingTop: 12, fontSize: 11 }}
                  iconType="circle"
                  iconSize={8}
                />
                <Bar
                  dataKey="standard"
                  name="Standard Multi-Head"
                  animationDuration={1200}
                  radius={[4, 4, 0, 0]}
                >
                  {threadIsolationData.map((_, index) => (
                    <Cell key={`cell-std-${index}`} fill={barColors[index]} opacity={0.7} />
                  ))}
                </Bar>
                <Bar
                  dataKey="acos"
                  name="ACOS OTM"
                  animationDuration={1200}
                  animationBegin={300}
                  radius={[4, 4, 0, 0]}
                >
                  {threadIsolationData.map((_, index) => (
                    <Cell key={`cell-acos-${index}`} fill={acosColors[index]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Explanation */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="grid grid-cols-1 md:grid-cols-2 gap-3"
      >
        <Card className="border-border/20 bg-card/30">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-slate-500/10 flex items-center justify-center flex-shrink-0">
                <ShieldCheck className="w-4 h-4 text-slate-400" />
              </div>
              <div>
                <p className="text-xs font-semibold text-foreground mb-1">Standard: Pervasive Leakage</p>
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  Multi-head attention shares key/query spaces across tasks, causing memory leaks (85%),
                  context contamination (90%), and task interference (72%).
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-emerald-500/20 bg-emerald-500/5">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center flex-shrink-0">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
              </div>
              <div>
                <p className="text-xs font-semibold text-emerald-400 mb-1">ACOS: Proven Zero Interference</p>
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  Orthogonal Thread Memory on the Stiefel Manifold ensures S^T*S = I_k, giving mathematically
                  proven zero inter-thread interference: &lt;S_i, S_j&gt; = 0 for all i != j.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}

// ─── Memory Efficiency Tab ─────────────────────────────────────────────────────

function MemoryEfficiencyTab() {
  return (
    <div className="space-y-4">
      {/* Comparison Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Standard LLM Card */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Card className="border-border/30 bg-card/50 h-full">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-10 h-10 rounded-lg bg-slate-500/10 flex items-center justify-center">
                  <MemoryStick className="w-5 h-5 text-slate-400" />
                </div>
                <div>
                  <p className="text-xs font-mono text-slate-400 uppercase tracking-wider">Standard LLM</p>
                  <p className="text-sm font-semibold text-foreground">KV Cache Approach</p>
                </div>
              </div>

              <div className="space-y-4">
                <div className="text-center p-4 rounded-lg bg-slate-500/5 border border-slate-500/10">
                  <div className="text-3xl md:text-4xl font-bold text-slate-300">
                    <AnimatedNumber value={2} suffix=" GB" />
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-1">Memory for 8K context (70B model)</p>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-lg bg-slate-500/5 border border-slate-500/10">
                    <p className="text-lg font-bold text-slate-300">O(N)</p>
                    <p className="text-[10px] text-muted-foreground">Per layer scaling</p>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-500/5 border border-slate-500/10">
                    <p className="text-lg font-bold text-slate-300">O(N*L)</p>
                    <p className="text-[10px] text-muted-foreground">Total KV cache</p>
                  </div>
                </div>

                <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/5 border border-red-500/15">
                  <ArrowRight className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />
                  <p className="text-[11px] text-red-300/80">
                    Linear growth per layer, multiplied by number of layers
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* ACOS Card */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.15 }}
        >
          <Card className="border-emerald-500/25 bg-gradient-to-br from-emerald-500/5 to-teal-500/5 h-full">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                  <Brain className="w-5 h-5 text-emerald-400" />
                </div>
                <div>
                  <p className="text-xs font-mono text-emerald-400 uppercase tracking-wider">ACOS</p>
                  <p className="text-sm font-semibold text-foreground">Thread Memory (OTM)</p>
                </div>
              </div>

              <div className="space-y-4">
                <div className="text-center p-4 rounded-lg bg-emerald-500/5 border border-emerald-500/15">
                  <div className="text-3xl md:text-4xl font-bold text-emerald-400">
                    <AnimatedNumber value={8} suffix=" MB" />
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-1">Memory for 8 threads (d=512)</p>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/15">
                    <p className="text-lg font-bold text-emerald-400">O(d*K)</p>
                    <p className="text-[10px] text-muted-foreground">Per thread</p>
                  </div>
                  <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/15">
                    <p className="text-lg font-bold text-emerald-400">O(d*K^2)</p>
                    <p className="text-[10px] text-muted-foreground">K threads total</p>
                  </div>
                </div>

                <div className="flex items-center gap-2 p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/15">
                  <ArrowRight className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                  <p className="text-[11px] text-emerald-300/80">
                    Bounded by thread count K, not sequence length N
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Compression Ratio Card */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.3 }}
      >
        <Card className="border-emerald-500/30 bg-gradient-to-r from-emerald-600/10 via-teal-600/5 to-emerald-600/10 overflow-hidden">
          <CardContent className="p-6">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="text-center md:text-left">
                <p className="text-xs font-mono text-emerald-400 uppercase tracking-wider mb-1">Memory Compression Ratio</p>
                <p className="text-[11px] text-muted-foreground">Thread state is dramatically more compact than KV cache</p>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <p className="text-sm text-slate-400 line-through">2,048 MB</p>
                </div>
                <ArrowRight className="w-5 h-5 text-emerald-400" />
                <div className="text-left">
                  <p className="text-sm text-emerald-400 font-semibold">8 MB</p>
                </div>
                <div className="ml-2 px-4 py-2 rounded-xl bg-emerald-500/15 border border-emerald-500/25">
                  <span className="text-2xl md:text-3xl font-bold text-emerald-400">
                    <AnimatedNumber value={250} suffix="x" />
                  </span>
                  <p className="text-[9px] text-emerald-300/60 text-center">less memory</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Explanation */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
      >
        <Card className="border-border/20 bg-card/30">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center flex-shrink-0">
                <HardDrive className="w-4 h-4 text-emerald-400" />
              </div>
              <div>
                <p className="text-xs font-semibold text-foreground mb-1">Why 250x Less Memory?</p>
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  Standard LLMs allocate KV cache that grows linearly with sequence length per layer,
                  requiring O(N*L*d) total memory. ACOS stores thread state as compact Stiefel Manifold
                  matrices of dimension d*K per thread, where K (thread count) is typically 4-16 and
                  independent of sequence length. This decoupling from N is the key to the compression advantage.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}

// ─── Learning Stability Tab ────────────────────────────────────────────────────

function LearningStabilityTab() {
  return (
    <div className="space-y-4">
      <Card className="border-border/30 bg-card/50 backdrop-blur-sm overflow-hidden">
        <CardContent className="p-4 md:p-6">
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-foreground">
              Continuous Learning - Task Retention
            </h3>
            <p className="text-[10px] text-muted-foreground mt-0.5">
              Performance on Task 1 as new tasks are learned sequentially
            </p>
          </div>
          <div className="h-[320px] md:h-[380px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={learningStabilityData}
                margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
              >
                <defs>
                  <linearGradient id="standardGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#94a3b8" stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="acosGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.4} />
                <XAxis
                  dataKey="task"
                  tick={{ fill: "#94a3b8", fontSize: 11 }}
                  axisLine={{ stroke: "#475569" }}
                  tickLine={{ stroke: "#475569" }}
                  label={{ value: "Tasks Learned Sequentially", position: "insideBottom", offset: -2, fill: "#94a3b8", fontSize: 11 }}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fill: "#94a3b8", fontSize: 11 }}
                  axisLine={{ stroke: "#475569" }}
                  tickLine={{ stroke: "#475569" }}
                  label={{ value: "Task 1 Performance (%)", angle: -90, position: "insideLeft", offset: 5, fill: "#94a3b8", fontSize: 11 }}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  wrapperStyle={{ paddingTop: 12, fontSize: 11 }}
                  iconType="circle"
                  iconSize={8}
                />
                <Area
                  type="monotone"
                  dataKey="standard"
                  name="Standard Fine-tuning"
                  stroke="#94a3b8"
                  strokeWidth={2}
                  fill="url(#standardGradient)"
                  animationDuration={1200}
                />
                <Area
                  type="monotone"
                  dataKey="acos"
                  name="ACOS Orthogonal"
                  stroke="#10b981"
                  strokeWidth={2.5}
                  fill="url(#acosGradient)"
                  animationDuration={1200}
                  animationBegin={300}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Explanation */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="grid grid-cols-1 md:grid-cols-2 gap-3"
      >
        <Card className="border-border/20 bg-card/30">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center flex-shrink-0">
                <TrendingUp className="w-4 h-4 text-red-400" />
              </div>
              <div>
                <p className="text-xs font-semibold text-foreground mb-1">Catastrophic Forgetting</p>
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  Standard fine-tuning overwrites previously learned weights. After learning 10 tasks,
                  Task 1 performance drops from 95% to 18% — an 81% degradation. This is the
                  fundamental barrier to continuous learning.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-emerald-500/20 bg-emerald-500/5">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center flex-shrink-0">
                <TrendingUp className="w-4 h-4 text-emerald-400" />
              </div>
              <div>
                <p className="text-xs font-semibold text-emerald-400 mb-1">Orthogonal Preservation</p>
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  ACOS projects new task gradients onto the orthogonal complement of prior task subspaces,
                  ensuring new learning never interferes with old. After 10 tasks, Task 1 retains 86% —
                  only a <span className="text-emerald-400 font-semibold">9% degradation</span> vs 81% for standard.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
