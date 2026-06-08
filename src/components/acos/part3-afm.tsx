"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { StatusBadge } from "./status-badge";
import { Badge } from "@/components/ui/badge";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Zap, CheckCircle2, Layers, ArrowRight, Brain, Cpu, Network } from "lucide-react";
import { SectionHeader } from "./section-header";

const componentEvals = [
  { component: "HBTA", decision: "Keep but Modify", rationale: "Hybrid Attention: FlashAttention < 4096 tokens, HBTA > 4096 tokens" },
  { component: "OTM", decision: "Core Feature", rationale: "Replaces KV Cache, dynamic and trainable during inference" },
  { component: "NSK (Panini)", decision: "Implement as Adapters", rationale: "LoRA-style for Panini constraints per task" },
];

const archComparison = [
  { name: "Transformer", time: "O(N^2*d)", memory: "O(N^2)", isolation: "None", persistent: "None", convergence: "Empirical", timeVal: 20, memVal: 20, isoVal: 0, persVal: 0, convVal: 30 },
  { name: "RWKV", time: "O(Nd)", memory: "O(rd)", isolation: "None", persistent: "Partial", convergence: "None", timeVal: 70, memVal: 70, isoVal: 0, persVal: 40, convVal: 0 },
  { name: "Mamba", time: "O(Nd)", memory: "O(rd)", isolation: "None", persistent: "Partial", convergence: "None", timeVal: 75, memVal: 75, isoVal: 0, persVal: 40, convVal: 0 },
  { name: "AHC v2", time: "O(Nd^2*logN)", memory: "O(Nd)", isolation: "Full [proven]", persistent: "Yes", convergence: "Local [proven]", timeVal: 50, memVal: 60, isoVal: 100, persVal: 100, convVal: 70 },
];

const additionalArchComparison = [
  { name: "RetNet", time: "O(Nd)", memory: "O(Nd)", isolation: "None", keyFeature: "Parallel training, sequential inference" },
  { name: "Titans", time: "O(Nd)", memory: "O(Nd)", isolation: "None", keyFeature: "Adaptive memory" },
  { name: "Liquid NNs", time: "O(Nd)", memory: "O(rd)", isolation: "None", keyFeature: "Dynamic weights per input" },
];

const radarData = [
  { metric: "Time Efficiency", Transformer: 20, RWKV: 70, Mamba: 75, "AHC v2": 50 },
  { metric: "Memory Efficiency", Transformer: 20, RWKV: 70, Mamba: 75, "AHC v2": 60 },
  { metric: "Thread Isolation", Transformer: 0, RWKV: 0, Mamba: 0, "AHC v2": 100 },
  { metric: "Persistent Memory", Transformer: 0, RWKV: 40, Mamba: 40, "AHC v2": 100 },
  { metric: "Convergence", Transformer: 30, RWKV: 0, Mamba: 0, "AHC v2": 70 },
];

function MambaOTMVisualization() {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-50px" });

  const layers = [
    { type: "mamba", label: "Mamba Block" },
    { type: "mamba", label: "Mamba Block" },
    { type: "mamba", label: "Mamba Block" },
    { type: "otm", label: "OTM Layer" },
    { type: "mamba", label: "Mamba Block" },
    { type: "mamba", label: "Mamba Block" },
    { type: "mamba", label: "Mamba Block" },
    { type: "otm", label: "OTM Layer" },
  ];

  return (
    <div ref={ref} className="flex flex-col items-center gap-0">
      <div className="flex items-stretch gap-3 w-full max-w-md">
        {/* Layer stack */}
        <div className="flex flex-col gap-1.5 flex-1">
          {layers.map((layer, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -30 }}
              animate={isInView ? { opacity: 1, x: 0 } : { opacity: 0, x: -30 }}
              transition={{ delay: i * 0.1, duration: 0.4, ease: "easeOut" }}
              className={`relative flex items-center justify-center py-2.5 px-4 rounded-md border text-xs font-semibold tracking-wide ${
                layer.type === "mamba"
                  ? "bg-teal-500/15 border-teal-500/30 text-teal-400"
                  : "bg-emerald-500/20 border-emerald-500/40 text-emerald-300"
              }`}
            >
              {layer.type === "otm" && (
                <motion.div
                  className="absolute inset-0 rounded-md border-2 border-emerald-400/40"
                  initial={{ opacity: 0 }}
                  animate={isInView ? { opacity: [0.3, 0.7, 0.3] } : { opacity: 0 }}
                  transition={{ delay: i * 0.1 + 0.5, duration: 2, repeat: Infinity, ease: "easeInOut" }}
                />
              )}
              <span className="relative z-10">{layer.label}</span>
              {layer.type === "mamba" && (
                <span className="ml-2 text-[9px] font-mono opacity-60">O(Nd)</span>
              )}
              {layer.type === "otm" && (
                <span className="ml-2 text-[9px] font-mono opacity-70">isolation</span>
              )}
            </motion.div>
          ))}
        </div>

        {/* Ratio indicator */}
        <div className="flex flex-col items-center justify-center gap-2">
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={isInView ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.8 }}
            transition={{ delay: 0.9, duration: 0.5, type: "spring", stiffness: 200 }}
            className="flex flex-col items-center gap-1 px-3 py-2 rounded-lg bg-muted/30 border border-border/30"
          >
            <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">Ratio</span>
            <div className="flex items-baseline gap-0.5">
              <span className="text-lg font-bold text-teal-400">3</span>
              <span className="text-sm text-muted-foreground">:</span>
              <span className="text-lg font-bold text-emerald-400">1</span>
            </div>
            <div className="flex gap-1">
              <div className="w-3 h-2 rounded-sm bg-teal-500/40" />
              <div className="w-3 h-2 rounded-sm bg-emerald-500/40" />
            </div>
          </motion.div>

          {/* Data flow arrow */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : { opacity: 0 }}
            transition={{ delay: 1.2, duration: 0.5 }}
            className="flex flex-col items-center gap-1"
          >
            <svg width="16" height="60" viewBox="0 0 16 60" className="text-emerald-500/40">
              <motion.line
                x1="8" y1="0" x2="8" y2="60"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeDasharray="4 3"
                initial={{ pathLength: 0 }}
                animate={isInView ? { pathLength: 1 } : { pathLength: 0 }}
                transition={{ delay: 1.3, duration: 1, ease: "easeInOut" }}
              />
            </svg>
            <span className="text-[8px] font-mono text-muted-foreground uppercase tracking-widest" style={{ writingMode: "vertical-rl" }}>data flow</span>
          </motion.div>
        </div>
      </div>

      {/* Legend */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 10 }}
        transition={{ delay: 1.4, duration: 0.4 }}
        className="flex items-center gap-4 mt-3 text-[10px] text-muted-foreground"
      >
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-2.5 rounded-sm bg-teal-500/30 border border-teal-500/40" />
          <span>Mamba Block (3x)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-2.5 rounded-sm bg-emerald-500/30 border border-emerald-500/50" />
          <span>OTM Layer (1x)</span>
        </div>
      </motion.div>
    </div>
  );
}

export function Part3AFM() {
  return (
    <div className="space-y-10">
      <SectionHeader
        sectionNumber={3}
        title="AFM Architecture"
        subtitle="The Avadhan Foundation Model backbone design"
        badge="HYBRID SSM"
        icon={<Cpu className="w-5 h-5" />}
        id="afm-architecture"
      />

      {/* Component Evaluation — Gradient Header Card */}
      <Card className="glass-card-premium card-hover-lift border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <CardTitle className="text-lg" id="component-evaluation">Component Evaluation & Decision</CardTitle>
              <CardDescription className="mb-2">Core architectural components and their implementation verdicts</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="gradient-accent-bar" />
          <div className="space-y-4">
            {componentEvals.map((eval_item, i) => (
              <motion.div
                key={eval_item.component}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.15 }}
                className="flex flex-col md:flex-row md:items-center gap-3 p-4 rounded-lg bg-muted/20 border border-border/20"
              >
                <div className="w-32 font-mono font-semibold text-sm text-foreground">
                  {eval_item.component}
                </div>
                <div>
                  <Badge
                    variant="outline"
                    className={`font-mono text-xs mr-2 ${
                      eval_item.decision === "Core Feature"
                        ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                        : eval_item.decision === "Keep but Modify"
                          ? "bg-amber-500/20 text-amber-400 border-amber-500/30"
                          : "bg-teal-500/20 text-teal-400 border-teal-500/30"
                    }`}
                  >
                    {eval_item.decision}
                  </Badge>
                </div>
                <div className="text-sm text-muted-foreground flex-1">
                  {eval_item.rationale}
                </div>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Architecture Comparison Table */}
      <Card className="card-hover-lift border-border/30">
        <CardHeader>
          <CardTitle className="text-lg" id="architecture-comparison">Architecture Comparison</CardTitle>
          <CardDescription className="mb-2">Side-by-side comparison of leading architectures across key metrics</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Architecture</TableHead>
                  <TableHead>Time</TableHead>
                  <TableHead>Memory</TableHead>
                  <TableHead>Thread Isolation</TableHead>
                  <TableHead>Persistent Memory</TableHead>
                  <TableHead>Convergence</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {archComparison.map((row) => (
                  <TableRow key={row.name} className={row.name === "AHC v2" ? "bg-emerald-500/5" : ""}>
                    <TableCell className="font-semibold">{row.name}</TableCell>
                    <TableCell className="font-mono text-xs">{row.time}</TableCell>
                    <TableCell className="font-mono text-xs">{row.memory}</TableCell>
                    <TableCell>
                      {row.isolation === "Full [proven]" ? (
                        <StatusBadge status="Proven" />
                      ) : (
                        <Badge variant="outline" className="bg-red-500/10 text-red-400 border-red-500/20 text-xs">
                          {row.isolation}
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={`text-xs ${
                          row.persistent === "Yes"
                            ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                            : row.persistent === "Partial"
                              ? "bg-amber-500/20 text-amber-400 border-amber-500/30"
                              : "bg-red-500/10 text-red-400 border-red-500/20"
                        }`}
                      >
                        {row.persistent}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={`text-xs ${
                          row.convergence.includes("proven")
                            ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                            : row.convergence === "Empirical"
                              ? "bg-amber-500/20 text-amber-400 border-amber-500/30"
                              : "bg-red-500/10 text-red-400 border-red-500/20"
                        }`}
                      >
                        {row.convergence}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Radar Chart */}
      <Card className="card-hover-lift border-border/30">
        <CardHeader>
          <CardTitle className="text-lg" id="radar-comparison">Architecture Comparison Radar</CardTitle>
          <CardDescription className="mb-2">Visual comparison of architecture capabilities across five dimensions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="70%">
                <PolarGrid stroke="oklch(1 0 0 / 8%)" />
                <PolarAngleAxis
                  dataKey="metric"
                  tick={{ fontSize: 11, fill: "oklch(0.7 0 0)" }}
                />
                <PolarRadiusAxis
                  angle={30}
                  domain={[0, 100]}
                  tick={{ fontSize: 9, fill: "oklch(0.5 0 0)" }}
                />
                <Radar
                  name="Transformer"
                  dataKey="Transformer"
                  stroke="#ef4444"
                  fill="#ef4444"
                  fillOpacity={0.1}
                />
                <Radar
                  name="RWKV"
                  dataKey="RWKV"
                  stroke="#f59e0b"
                  fill="#f59e0b"
                  fillOpacity={0.1}
                />
                <Radar
                  name="Mamba"
                  dataKey="Mamba"
                  stroke="#06b6d4"
                  fill="#06b6d4"
                  fillOpacity={0.1}
                />
                <Radar
                  name="AHC v2"
                  dataKey="AHC v2"
                  stroke="#10b981"
                  fill="#10b981"
                  fillOpacity={0.2}
                  strokeWidth={2}
                />
                <Legend
                  wrapperStyle={{ fontSize: "11px" }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Proposed Hybrid */}
      <Card className="card-hover-lift border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
              <Network className="w-5 h-5" />
            </div>
            <div>
              <CardTitle className="text-lg" id="mamba-otm-hybrid">Proposed Hybrid: Mamba-OTM</CardTitle>
              <CardDescription className="mb-2">Combining Mamba speed with OTM thread isolation</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Mamba-OTM Layer Visualization */}
          <MambaOTMVisualization />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
            <div className="p-4 rounded-lg bg-card/50 border border-border/20">
              <div className="text-sm font-semibold text-teal-400 mb-1">Backbone: Mamba</div>
              <div className="text-xs text-muted-foreground">
                Speed and linear scaling for general token processing. State-space
                model provides O(Nd) complexity with efficient hardware utilization.
              </div>
            </div>
            <div className="p-4 rounded-lg bg-card/50 border border-emerald-500/20">
              <div className="text-sm font-semibold text-emerald-400 mb-1">Reasoning Layer: OTM</div>
              <div className="text-xs text-muted-foreground">
                Every 4th layer replaced with OTM for thread isolation during complex
                reasoning. Mathematically proven zero interference between threads.
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Detailed Component Decisions */}
      <Card className="card-hover-lift border-border/30">
        <CardHeader>
          <CardTitle className="text-lg">Detailed Component Decisions</CardTitle>
          <CardDescription className="mb-2">In-depth rationale for each component implementation strategy</CardDescription>
        </CardHeader>
        <CardContent>
          <Accordion type="multiple" className="w-full">
            <AccordionItem value="hbta">
              <AccordionTrigger>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="bg-amber-500/20 text-amber-400 border-amber-500/30 text-xs">
                    Keep but Modify
                  </Badge>
                  <span className="text-sm font-semibold">HBTA → Hybrid Attention</span>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-2 p-3 rounded-lg bg-muted/20 border border-border/20">
                  <p className="text-xs text-muted-foreground">
                    <span className="text-amber-400 font-semibold">Strategy:</span> FlashAttention for first 4096 tokens, switch to HBTA for tokens &gt; 4096. Best of both worlds.
                  </p>
                  <div className="flex items-center gap-2 mt-2">
                    <code className="text-[10px] font-mono bg-card/50 px-2 py-1 rounded border border-border/10">
                      N &lt; 4096 -&gt; FlashAttention (O(N^2*d) but optimized)
                    </code>
                    <ArrowRight className="w-3 h-3 text-muted-foreground" />
                    <code className="text-[10px] font-mono bg-card/50 px-2 py-1 rounded border border-border/10">
                      N &gt; 4096 -&gt; HBTA (O(Nd^2*logN))
                    </code>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="otm">
              <AccordionTrigger>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30 text-xs">
                    Core Feature
                  </Badge>
                  <span className="text-sm font-semibold">OTM → Replaces KV Cache</span>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="p-3 rounded-lg bg-muted/20 border border-border/20">
                  <p className="text-xs text-muted-foreground">
                    <span className="text-emerald-400 font-semibold">Key Advantage:</span> OTM is dynamic and trainable during inference, unlike static KV Cache. The Stiefel Manifold parameterization ensures thread isolation while allowing the model to update its memory representation based on new context.
                  </p>
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="nsk">
              <AccordionTrigger>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="bg-teal-500/20 text-teal-400 border-teal-500/30 text-xs">
                    As Adapters
                  </Badge>
                  <span className="text-sm font-semibold">NSK → LoRA-style Adapters</span>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="p-3 rounded-lg bg-muted/20 border border-border/20">
                  <p className="text-xs text-muted-foreground">
                    <span className="text-teal-400 font-semibold">Strategy:</span> Train base LLM (AFM-Base), then train lightweight LoRA adapters for Panini constraints per task. For example, a &quot;Coding Adapter&quot; enforcing syntax rules, a &quot;Math Adapter&quot; enforcing logical consistency. This keeps the base model general while adding domain-specific symbolic constraints.
                  </p>
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </CardContent>
      </Card>

      {/* Additional Architecture Comparison */}
      <Card className="card-hover-lift border-border/30">
        <CardHeader>
          <CardTitle className="text-lg">Extended Architecture Comparison</CardTitle>
          <CardDescription className="mb-2">Broader landscape of alternative architecture approaches</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Architecture</TableHead>
                  <TableHead>Time</TableHead>
                  <TableHead>Memory</TableHead>
                  <TableHead>Thread Isolation</TableHead>
                  <TableHead>Key Feature</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {additionalArchComparison.map((row) => (
                  <TableRow key={row.name}>
                    <TableCell className="font-semibold">{row.name}</TableCell>
                    <TableCell className="font-mono text-xs">{row.time}</TableCell>
                    <TableCell className="font-mono text-xs">{row.memory}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="bg-red-500/10 text-red-400 border-red-500/20 text-xs">
                        {row.isolation}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">{row.keyFeature}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Hybrid Verdict */}
      <Card className="card-hover-lift border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardHeader>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <CardTitle className="text-lg text-emerald-400" id="hybrid-verdict">Hybrid Verdict: Why Hybrid Outperforms Pure Avadhan</CardTitle>
            <CardDescription className="text-emerald-400/70 mb-2">The case for combining architectures</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            Pure Avadhan architecture would sacrifice the speed of Mamba/RWKV for long-range reasoning. The Mamba-OTM hybrid achieves:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {[
              {
                num: "1",
                title: "O(Nd) from Mamba",
                desc: "Linear scaling backbone for general token processing",
                icon: <Zap className="w-4 h-4" />,
                color: "teal",
              },
              {
                num: "2",
                title: "Proven Thread Isolation",
                desc: "OTM every 4th layer ensures zero interference",
                icon: <Layers className="w-4 h-4" />,
                color: "emerald",
              },
              {
                num: "3",
                title: "Neuro-Symbolic Verification",
                desc: "NSK adapters add Panini constraints per domain",
                icon: <CheckCircle2 className="w-4 h-4" />,
                color: "green",
              },
            ].map((item, i) => (
              <motion.div
                key={item.num}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.15 }}
                className={`p-4 rounded-lg bg-card/50 border ${
                  item.color === "emerald" ? "border-emerald-500/20" :
                  item.color === "teal" ? "border-teal-500/20" :
                  "border-green-500/20"
                }`}
              >
                <div className={`flex items-center gap-2 mb-2 ${
                  item.color === "emerald" ? "text-emerald-400" :
                  item.color === "teal" ? "text-teal-400" :
                  "text-green-400"
                }`}>
                  <div className={`w-10 h-10 rounded-lg ${
                    item.color === "emerald" ? "bg-emerald-500/10 border border-emerald-500/20" :
                    item.color === "teal" ? "bg-teal-500/10 border border-teal-500/20" :
                    "bg-green-500/10 border border-green-500/20"
                  } flex items-center justify-center`}>
                    {item.icon}
                  </div>
                  <span className="text-sm font-semibold">{item.title}</span>
                </div>
                <p className="text-xs text-muted-foreground">{item.desc}</p>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Key Innovation Insight Card */}
      <Card className="card-hover-lift border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardContent className="p-6">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
              <Brain className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-semibold text-foreground mb-1">
                Key Innovation: Mamba-OTM Hybrid Architecture
              </div>
              <p className="text-xs text-muted-foreground">
                The Mamba-OTM hybrid is the only architecture that simultaneously achieves linear-time
                processing (from Mamba&apos;s state-space model) and mathematically proven thread isolation
                (from OTM&apos;s Stiefel Manifold parameterization). Every 4th layer is replaced with OTM,
                creating a cognitive backbone that scales efficiently while preserving zero-interference
                guarantees. This hybrid approach reduces compute requirements by 250x compared to pure
                transformer architectures while enabling multi-threaded reasoning impossible in any
                existing alternative.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
