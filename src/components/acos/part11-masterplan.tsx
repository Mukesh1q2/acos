"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Map,
  Calendar,
  Server,
  Monitor,
  CheckCircle2,
  ArrowRight,
  Target,
  AlertTriangle,
  Shield,
  DollarSign,
  Cpu,
  Database,
  Cloud,
  HardDrive,
  Container,
} from "lucide-react";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from "recharts";

const verdict = {
  path: "Path C",
  description: "Build ACOS first, AFM later",
  rationale:
    "Start with the orchestrator layer that wraps existing models, then gradually build proprietary AFM components. This validates the architecture with real users before investing in full model training.",
};

const mvpMonths = [
  {
    month: 1,
    title: "HBTA/OTM Layer",
    description: "Build HBTA/OTM layer in PyTorch. Validate thread isolation on small scale. Benchmark against FlashAttention.",
    deliverable: "PyTorch module + benchmarks",
    color: "emerald",
  },
  {
    month: 2,
    title: "Cognitive Kernel",
    description: "Wrap Llama-3-8B with Cognitive Kernel. Implement process manager, memory manager, and Lyapunov scheduler.",
    deliverable: "Kernel-wrapped Llama-3-8B",
    color: "teal",
  },
  {
    month: 3,
    title: "Upload & Learn",
    description: "Build Upload & Learn pipeline (RAG + LoRA). Document ingestion, vector storage, and LoRA fine-tuning per user.",
    deliverable: "Document learning pipeline",
    color: "green",
  },
  {
    month: 4,
    title: "Chat Interface",
    description: "React-based chat interface with thread visualization. Real-time streaming, memory recall, and multi-thread display.",
    deliverable: "Full chat application",
    color: "cyan",
  },
  {
    month: 5,
    title: "CUDA Optimization",
    description: "CUDA kernel optimization for QR/Cayley transforms. Custom attention kernels for HBTA. Memory optimization for consumer GPUs.",
    deliverable: "Optimized CUDA kernels",
    color: "emerald",
  },
  {
    month: 6,
    title: 'Beta Launch',
    description: 'Beta Launch "ACOS for Laptops". Local deployment package, onboarding flow, and initial user testing.',
    deliverable: "Public beta release",
    color: "teal",
  },
];

const probabilityData = [
  { axis: "ACOS Orchestrator", value: 67 },
  { axis: "AFM Architecture", value: 17 },
  { axis: "Combined Path", value: 57 },
  { axis: "Technical Risk", value: 40 },
  { axis: "Market Timing", value: 55 },
  { axis: "Funding", value: 45 },
];

const commercialization = [
  {
    product: "Avadhan Server",
    type: "Enterprise",
    icon: <Server className="w-5 h-5" />,
    description: "On-premise deployment that learns company data. Private, secure, and continuously improving on internal knowledge.",
    features: ["On-premise deployment", "Enterprise data learning", "SOC 2 compliance", "Team collaboration"],
  },
  {
    product: "Avadhan Desktop",
    type: "Consumer",
    icon: <Monitor className="w-5 h-5" />,
    description: "Local AI assistant with memory. Remembers your preferences, learns your workflow, and never forgets.",
    features: ["Local-first deployment", "Personal memory", "Privacy guaranteed", "Cross-platform"],
  },
];

const colorStyles: Record<string, { bg: string; border: string; text: string }> = {
  emerald: { bg: "bg-emerald-500/10", border: "border-emerald-500/20", text: "text-emerald-400" },
  teal: { bg: "bg-teal-500/10", border: "border-teal-500/20", text: "text-teal-400" },
  green: { bg: "bg-green-500/10", border: "border-green-500/20", text: "text-green-400" },
  cyan: { bg: "bg-cyan-500/10", border: "border-cyan-500/20", text: "text-cyan-400" },
};

const strategicPaths = [
  {
    path: "A: ACOS only",
    desc: "Build orchestrator, no custom model",
    probability: "65-70%",
    cost: "$2-5M",
    time: "12-18 months",
    recommended: false,
  },
  {
    path: "B: AFM only",
    desc: "Build custom foundation model",
    probability: "15-20%",
    cost: "$50-100M",
    time: "24-36 months",
    recommended: false,
  },
  {
    path: "C: ACOS first, AFM later",
    desc: "Recommended",
    probability: "55-60%",
    cost: "$5-15M",
    time: "18-30 months",
    recommended: true,
  },
  {
    path: "D: Both simultaneously",
    desc: "Highest risk",
    probability: "30-35%",
    cost: "$50-100M",
    time: "24-36 months",
    recommended: false,
  },
];

const infrastructureDesign = [
  {
    category: "Development",
    icon: <Cpu className="w-4 h-4" />,
    desc: "4× A100s (Phase 1), scaling to 32-64× (Phase 3)",
    color: "emerald",
  },
  {
    category: "Training",
    icon: <Server className="w-4 h-4" />,
    desc: "Cloud GPU (AWS/GCP) + local fine-tuning",
    color: "teal",
  },
  {
    category: "Inference",
    icon: <Monitor className="w-4 h-4" />,
    desc: "Local GPU (RTX 4090) for consumer, A100 for enterprise",
    color: "green",
  },
  {
    category: "Storage",
    icon: <Database className="w-4 h-4" />,
    desc: "Vector DB (Qdrant/Milvus) + Knowledge Graph (Neo4j)",
    color: "cyan",
  },
  {
    category: "Deployment",
    icon: <Container className="w-4 h-4" />,
    desc: "Docker + Kubernetes for enterprise, Electron for desktop",
    color: "emerald",
  },
];

const topRisks = [
  {
    num: 1,
    category: "Technical",
    risk: "Stiefel optimization doesn't converge at scale",
    mitigation: "Fallback to standard fine-tuning",
    severity: "high",
  },
  {
    num: 2,
    category: "Market",
    risk: "Competitors add similar features",
    mitigation: "Patent protection + first-mover advantage",
    severity: "medium",
  },
  {
    num: 3,
    category: "Funding",
    risk: "Insufficient capital for Phase 3",
    mitigation: "Phase 1-2 generate revenue",
    severity: "medium",
  },
  {
    num: 4,
    category: "Talent",
    risk: "Rare Stiefel/Riemannian expertise",
    mitigation: "Academic partnerships",
    severity: "high",
  },
  {
    num: 5,
    category: "Timing",
    risk: "6-month MVP too aggressive",
    mitigation: "Phased release, feature flags",
    severity: "medium",
  },
];

const riskSeverityColors: Record<string, string> = {
  high: "bg-red-500/20 text-red-400 border-red-500/30",
  medium: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  low: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
};

export function Part11MasterPlan() {
  return (
    <div className="space-y-8">
      <div>
        <h2 id="part11-master-plan" className="text-2xl font-bold text-foreground mb-2">
          Part 11 — Master Plan
        </h2>
        <p className="text-muted-foreground">
          The definitive roadmap: Build ACOS first as orchestrator, then AFM as
          proprietary foundation model.
        </p>
      </div>

      {/* Verdict */}
      <Card className="border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardContent className="p-6">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
              <Target className="w-6 h-6" />
            </div>
            <div>
              <div className="text-xs font-mono text-emerald-400 mb-1">VERDICT</div>
              <div className="text-xl font-bold text-foreground mb-1">
                {verdict.path} — {verdict.description}
              </div>
              <p className="text-sm text-muted-foreground">{verdict.rationale}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* MVP Roadmap - Gantt-style */}
      <Card className="border-border/30">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-emerald-400" />
            <CardTitle className="text-lg" id="mvp-roadmap">6-Month MVP Roadmap</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mvpMonths.map((month, i) => {
              const colors = colorStyles[month.color];
              return (
                <motion.div
                  key={month.month}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className="flex flex-col md:flex-row gap-3"
                >
                  <div className={`w-20 h-20 md:w-16 md:h-full rounded-lg ${colors.bg} ${colors.border} border flex flex-col items-center justify-center flex-shrink-0`}>
                    <div className="text-[10px] text-muted-foreground font-mono">Month</div>
                    <div className={`text-2xl font-bold ${colors.text}`}>{month.month}</div>
                  </div>
                  <div className="flex-1 p-3 rounded-lg bg-muted/20 border border-border/20 card-hover-lift">
                    <div className="text-sm font-semibold text-foreground mb-1">
                      {month.title}
                    </div>
                    <p className="text-xs text-muted-foreground mb-2">
                      {month.description}
                    </p>
                    <Badge variant="outline" className="text-[10px] bg-muted/30">
                      <CheckCircle2 className="w-2.5 h-2.5 mr-1" />
                      {month.deliverable}
                    </Badge>
                  </div>
                </motion.div>
              );
            })}
          </div>

          {/* Gantt Bars */}
          <div className="mt-6 pt-4 border-t border-border/20">
            <div className="text-xs font-semibold text-muted-foreground mb-3 uppercase tracking-wider">
              Timeline Overview
            </div>
            <div className="space-y-1.5">
              {mvpMonths.map((month, i) => {
                const colors = colorStyles[month.color];
                return (
                  <div key={month.month} className="flex items-center gap-2">
                    <div className="w-20 text-[10px] text-muted-foreground font-mono text-right">
                      M{month.month}
                    </div>
                    <div className="flex-1 h-6 bg-muted/20 rounded relative">
                      <motion.div
                        className={`absolute top-0 left-0 h-full rounded ${colors.bg} border ${colors.border}`}
                        initial={{ width: 0 }}
                        animate={{ width: "100%" }}
                        transition={{ duration: 0.6, delay: 0.5 + i * 0.1 }}
                      />
                      <div className="absolute inset-0 flex items-center px-2">
                        <span className="text-[9px] font-medium text-foreground truncate">
                          {month.title}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Probability Radar */}
      <Card className="border-border/30">
        <CardHeader>
          <CardTitle className="text-lg" id="probability-assessment">Probability of Success Assessment</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={probabilityData} cx="50%" cy="50%" outerRadius="65%">
                <PolarGrid stroke="oklch(1 0 0 / 8%)" />
                <PolarAngleAxis
                  dataKey="axis"
                  tick={{ fontSize: 10, fill: "oklch(0.7 0 0)" }}
                />
                <PolarRadiusAxis
                  angle={30}
                  domain={[0, 100]}
                  tick={{ fontSize: 9, fill: "oklch(0.5 0 0)" }}
                />
                <Radar
                  name="Probability %"
                  dataKey="value"
                  stroke="#10b981"
                  fill="#10b981"
                  fillOpacity={0.2}
                  strokeWidth={2}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-3 gap-3 mt-4">
            <div className="text-center p-3 rounded-lg bg-muted/20">
              <div className="text-2xl font-bold text-emerald-400">65-70%</div>
              <div className="text-xs text-muted-foreground">ACOS Orchestrator</div>
            </div>
            <div className="text-center p-3 rounded-lg bg-muted/20">
              <div className="text-2xl font-bold text-amber-400">15-20%</div>
              <div className="text-xs text-muted-foreground">AFM Architecture</div>
            </div>
            <div className="text-center p-3 rounded-lg bg-muted/20">
              <div className="text-2xl font-bold text-teal-400">55-60%</div>
              <div className="text-xs text-muted-foreground">Combined Path</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Commercialization */}
      <Card className="border-border/30">
        <CardHeader>
          <CardTitle className="text-lg" id="commercialization-strategy">Commercialization Strategy</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {commercialization.map((product, i) => (
              <motion.div
                key={product.product}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.15 }}
                className="p-4 rounded-lg bg-muted/20 border border-border/20"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                    {product.icon}
                  </div>
                  <div>
                    <div className="text-sm font-semibold">{product.product}</div>
                    <Badge variant="outline" className="text-[10px] bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                      {product.type}
                    </Badge>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mb-3">
                  {product.description}
                </p>
                <div className="space-y-1">
                  {product.features.map((feature) => (
                    <div key={feature} className="flex items-center gap-1.5 text-xs">
                      <CheckCircle2 className="w-3 h-3 text-emerald-500 flex-shrink-0" />
                      <span>{feature}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Strategic Recommendation */}
      <Card className="border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Target className="w-5 h-5 text-emerald-400" />
            <CardTitle className="text-lg text-emerald-400" id="strategic-paths">Strategic Path Comparison</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Path</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Probability</TableHead>
                  <TableHead>Cost</TableHead>
                  <TableHead>Time</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {strategicPaths.map((row) => (
                  <TableRow key={row.path} className={row.recommended ? "bg-emerald-500/5" : ""}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm">{row.path}</span>
                        {row.recommended && (
                          <Badge variant="outline" className="text-[9px] bg-emerald-500/20 text-emerald-400 border-emerald-500/30">
                            Recommended
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">{row.desc}</TableCell>
                    <TableCell className="font-mono text-xs">{row.probability}</TableCell>
                    <TableCell className="font-mono text-xs">{row.cost}</TableCell>
                    <TableCell className="font-mono text-xs">{row.time}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Infrastructure Design */}
      <Card className="border-border/30">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Server className="w-5 h-5 text-teal-400" />
            <CardTitle className="text-lg" id="infrastructure-design">Infrastructure Design</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {infrastructureDesign.map((item, i) => {
              const colors = colorStyles[item.color];
              return (
                <motion.div
                  key={item.category}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className="p-3 rounded-lg bg-muted/20 border border-border/20"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <div className={`w-8 h-8 rounded-lg ${colors.bg} ${colors.border} border flex items-center justify-center ${colors.text}`}>
                      {item.icon}
                    </div>
                    <span className="text-sm font-semibold">{item.category}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{item.desc}</p>
                </motion.div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Risk Analysis */}
      <Card className="border-border/30">
        <CardHeader>
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-400" />
            <CardTitle className="text-lg" id="risk-analysis">Risk Analysis — Top 5 Risks</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {topRisks.map((risk, i) => (
              <motion.div
                key={risk.num}
                initial={{ opacity: 0, x: -15 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className="flex flex-col md:flex-row md:items-center gap-3 p-4 rounded-lg bg-muted/20 border border-border/20"
              >
                <div className="flex items-center gap-2 min-w-[80px]">
                  <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 font-bold text-xs flex-shrink-0">
                    #{risk.num}
                  </div>
                  <Badge variant="outline" className="text-[10px] bg-amber-500/10 text-amber-400 border-amber-500/20">
                    {risk.category}
                  </Badge>
                </div>
                <div className="flex-1">
                  <div className="text-sm font-semibold text-foreground">{risk.risk}</div>
                </div>
                <div className="flex items-center gap-2">
                  <Shield className="w-3.5 h-3.5 text-teal-400 flex-shrink-0" />
                  <span className="text-xs text-teal-400 font-mono">Mitigation: {risk.mitigation}</span>
                </div>
                <Badge variant="outline" className={`text-[10px] ${riskSeverityColors[risk.severity]}`}>
                  {risk.severity}
                </Badge>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
