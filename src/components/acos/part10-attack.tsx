"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  AlertTriangle,
  Flame,
  Bug,
  Cpu,
  Zap,
  Wrench,
  Search,
  HelpCircle,
  TrendingUp,
} from "lucide-react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ZAxis,
} from "recharts";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const failurePoints = [
  { id: 1, name: "Speed", description: "HBTA slower than FlashAttention for N<5000", probability: 0.7, impact: 0.6, severity: "critical" },
  { id: 2, name: "Hardware Drift", description: "fp16 instability causes thread collapse", probability: 0.8, impact: 0.9, severity: "critical" },
  { id: 3, name: "Training Complexity", description: "Stiefel Manifold hard to converge", probability: 0.6, impact: 0.7, severity: "high" },
  { id: 4, name: "Context Fragmentation", description: "Binary tree misses cross-boundary info", probability: 0.5, impact: 0.5, severity: "high" },
  { id: 5, name: "Distillation Loss", description: "Forcing pre-trained embeddings into orthogonal matrix", probability: 0.7, impact: 0.8, severity: "high" },
  { id: 6, name: "Distance Concentration", description: "Dot products concentrate in high dimensions, making tree routing unreliable", probability: 0.6, impact: 0.7, severity: "high" },
  { id: 7, name: "Gate Saturation", description: "Pingala gates can saturate causing gradient death", probability: 0.4, impact: 0.4, severity: "medium" },
  { id: 8, name: "Panini Mask Collapse", description: "Constraint masks can become transparent (c->inf)", probability: 0.4, impact: 0.5, severity: "medium" },
  { id: 9, name: "Nyaya Verifier Collapse", description: "When V_j(h)->1, gradient->0, uninformative", probability: 0.4, impact: 0.5, severity: "medium" },
  { id: 10, name: "Memory Bottleneck", description: "Nonlinear autoencoder may converge to worse than PCA", probability: 0.5, impact: 0.5, severity: "medium" },
  { id: 11, name: "Stiefel Retraction Overhead", description: "QR/Cayley per step adds latency", probability: 0.7, impact: 0.6, severity: "high" },
  { id: 12, name: "fp32 Master Copy", description: "Memory overhead for K=1000 impractical", probability: 0.5, impact: 0.4, severity: "medium" },
  { id: 13, name: "No Global Stability", description: "Controller only locally Lyapunov stable", probability: 0.4, impact: 0.5, severity: "medium" },
  { id: 14, name: "Crossover Point", description: "d=512, N=4096 -> HBTA slower", probability: 0.7, impact: 0.6, severity: "high" },
  { id: 15, name: "Binary Tree Rigidity", description: "Non-hierarchical patterns poorly handled", probability: 0.4, impact: 0.4, severity: "medium" },
  { id: 16, name: "Scaling K>50", description: "Cayley numerically unsafe, must use QR", probability: 0.5, impact: 0.5, severity: "medium" },
  { id: 17, name: "Riemannian Optimization", description: "Notoriously difficult for large models", probability: 0.7, impact: 0.8, severity: "high" },
  { id: 18, name: "Sleep Cycle Scheduling", description: "Downtime for consolidation", probability: 0.3, impact: 0.2, severity: "low" },
  { id: 19, name: "Knowledge Graph Consistency", description: "Updates under concurrent access", probability: 0.4, impact: 0.4, severity: "medium" },
  { id: 20, name: "Multi-Model Consensus Timeout", description: "No agreed standard for timeout", probability: 0.3, impact: 0.3, severity: "low" },
  { id: 21, name: "Local Model Memory", description: "8-16GB consumer hardware constraint", probability: 0.7, impact: 0.7, severity: "high" },
  { id: 22, name: "Gradient Accumulation", description: "Stiefel + standard params complicated", probability: 0.4, impact: 0.4, severity: "medium" },
  { id: 23, name: "Thread Deadlock", description: "Multi-agent scenarios", probability: 0.4, impact: 0.5, severity: "medium" },
  { id: 24, name: "CUDA Kernel Maturity", description: "Custom kernels for QR/Cayley unproven", probability: 0.6, impact: 0.7, severity: "high" },
  { id: 25, name: "Data Pipeline", description: "Billion-scale vector store performance", probability: 0.5, impact: 0.5, severity: "medium" },
];

const engineeringChallenges = [
  "Custom CUDA kernels for QR/Cayley transforms",
  "fp16->fp32 casting overhead on consumer GPUs",
  "Memory-mapped vector stores at billion-scale",
  "Thread deadlock prevention in multi-agent scenarios",
  "Latency budget for real-time chat (<200ms)",
  "Gradient accumulation across Stiefel+standard parameters",
  "Knowledge graph consistency under concurrent updates",
  "Sleep cycle scheduling without user-facing downtime",
  "Model consensus timeout handling and fallback",
  "Local model memory footprint on consumer hardware (8-16GB)",
  "HBTA tree construction for non-power-of-2 sequences",
  "Gated-sum broadcast kernel optimization",
  "Riemannian gradient computation in mixed precision",
  "Dynamic thread allocation without contention",
  "Episodic memory index maintenance at scale",
  "Cross-model embedding alignment",
  "Adaptive QR re-orthogonalization frequency",
  "Panini constraint mask initialization strategy",
  "Nyaya verifier training data generation",
  "Multi-GPU Stiefel matrix synchronization",
  "Inference batching with variable thread counts",
  "Memory consolidation scheduling algorithm",
  "Conflict resolution between parallel reasoning threads",
  "Model hot-swapping without context loss",
  "Progressive model loading for fast startup",
];

const researchGaps = [
  "No empirical validation of HBTA approximation error bound",
  "Distance concentration in hierarchical routing unresolved",
  "Nonlinear Sphota bottleneck vs PCA not analyzed",
  "Nyaya verifier logical validity unverified",
  "Optimal thread count K for various tasks unknown",
  "Interaction between Stiefel optimization and Adam",
  "Long-term memory consolidation mechanisms",
  "Scaling laws for AHC architecture",
  "Transfer learning with orthogonal constraints",
  "Multi-modal integration with OTM",
  "Continual learning benchmark suite",
  "Energy-based model vs discriminator for Nyaya",
  "Hierarchical memory retrieval accuracy",
  "Thread composition strategies",
  "Gradient death detection and recovery",
  "Optimal gating initialization for Pingala",
  "Cross-architecture distillation techniques",
  "Memory decay scheduling algorithms",
  "Self-evolution safety bounds",
  "Cognitive thread priority algorithms",
  "Knowledge graph evolution mechanisms",
  "Agent cooperation protocols",
  "Distributed Stiefel optimization",
  "Hardware-aware thread scheduling",
  "Formal verification of ACOS properties",
];

const assumptions = [
  "Exponential attention decay assumption for HBTA error bound",
  "Stiefel Manifold is the right geometry for thread memory",
  "Orthogonal threads lead to better task performance",
  "Binary tree hierarchy matches cognitive structure",
  "Gated-sum preserves sufficient information",
  "Three-tier memory is sufficient for cognition",
  "Soft logic constraints (Panini) can guide reasoning",
  "Distributional plausibility (Nyaya) approximates validity",
  "Local Lyapunov stability is sufficient in practice",
  "Mixed-precision training works with Stiefel constraints",
  "Consumer hardware can support meaningful ACOS instances",
  "Continuous learning is commercially valuable",
  "Thread isolation prevents cross-task contamination",
  "Knowledge fabric scales to enterprise data volumes",
  "Multi-model consensus improves output quality",
  "Sleep-phase consolidation doesn't disrupt service",
  "LoRA adapters preserve Panini constraint semantics",
  "HBTA+FlashAttention hybrid is implementable",
  "Mamba-OTM hybrid converges during training",
  "The market wants a cognitive OS (not just LLMs)",
  "Open source + commercial license is viable",
  "6-month MVP timeline is achievable",
  "4x A100s sufficient for Phase 1 validation",
  "Existing models can be wrapped by ACOS",
  "Self-evolution can be made safe via Nyaya verification",
];

const scalabilityBottlenecks = [
  "HBTA tree depth grows as O(logN), memory per level grows",
  "OTM Cayley retraction: O(K^2*d) per step",
  "QR retraction: O(Kd^2) for K>50",
  "Episodic memory ANN search: O(d*logM_E) per retrieval",
  "Semantic memory graph traversal: O(V+E) worst case",
  "Multi-thread context: K simultaneous forward passes",
  "fp32 Stiefel buffer: Kd*4 bytes per layer",
  "Knowledge graph updates: O(V*E) for consistency",
  "Vector store index rebuild: O(M*logM*d)",
  "Model loading time for multi-model orchestration",
  "Gated-sum broadcast: K matrix-vector products per token",
  "Panini constraint masking: O(vocabulary) per token",
  "Nyaya MLP verification: O(d*d_v) per output token",
  "Sleep cycle consolidation: Full backward pass on M_E samples",
  "Multi-model consensus: 2-3× compute per query",
  "Thread synchronization overhead for real-time",
  "Memory bandwidth for Stiefel operations",
  "Gradient checkpointing for long sequences",
  "Distributed inference across model ensemble",
  "Context window management across models",
  "RAG pipeline latency for knowledge queries",
  "Embedding alignment across model boundaries",
  "Progressive loading vs full model startup",
  "Concurrent user session isolation",
  "Knowledge fabric update propagation",
];

const severityColors: Record<string, { bg: string; border: string; text: string; dot: string }> = {
  critical: { bg: "bg-red-500/10", border: "border-red-500/30", text: "text-red-400", dot: "#ef4444" },
  high: { bg: "bg-amber-500/10", border: "border-amber-500/30", text: "text-amber-400", dot: "#f59e0b" },
  medium: { bg: "bg-orange-500/10", border: "border-orange-500/30", text: "text-orange-400", dot: "#f97316" },
  low: { bg: "bg-emerald-500/10", border: "border-emerald-500/30", text: "text-emerald-400", dot: "#10b981" },
};

const severityBadgeColors: Record<string, string> = {
  critical: "bg-red-500/20 text-red-400 border-red-500/30",
  high: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  medium: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  low: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
};

const scatterData = failurePoints.map((fp) => ({
  x: fp.probability * 100,
  y: fp.impact * 100,
  z: fp.severity === "critical" ? 400 : fp.severity === "high" ? 250 : fp.severity === "medium" ? 150 : 80,
  name: fp.name,
  severity: fp.severity,
}));

interface ScatterTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: {
      name: string;
      severity: string;
      x: number;
      y: number;
    };
  }>;
}

function CustomScatterTooltip({ active, payload }: ScatterTooltipProps) {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0].payload;
  return (
    <div className="bg-card border border-border/50 rounded-lg p-2 text-xs shadow-lg">
      <div className="font-semibold">{data.name}</div>
      <div className="text-muted-foreground">
        Probability: {data.x}% * Impact: {data.y}%
      </div>
      <Badge
        variant="outline"
        className={`text-[9px] mt-1 ${severityColors[data.severity]?.bg || ""} ${severityColors[data.severity]?.text || ""} ${severityColors[data.severity]?.border || ""}`}
      >
        {data.severity}
      </Badge>
    </div>
  );
}

export function Part10Attack() {
  return (
    <div className="space-y-8">
      <div>
        <h2 id="attack-analysis" className="text-2xl font-bold text-foreground mb-2">
          Part 10 — Attack Analysis
        </h2>
        <p className="text-muted-foreground">
          Comprehensive risk analysis: 25 failure points, 25 engineering challenges,
          25 research gaps, 25 assumptions, and 25 scalability bottlenecks.
        </p>
        <Badge variant="outline" className="text-[10px] bg-emerald-500/10 text-emerald-400 border-emerald-500/20 font-mono">
          5 CRITICAL RISKS
        </Badge>
      </div>

      {/* Risk Heatmap */}
      <Card className="card-hover-lift border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardHeader>
          <CardTitle className="text-lg">Risk Heatmap (Probability x Impact)</CardTitle>
          <CardDescription>Visual mapping of all 25 failure points</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[350px]">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(1 0 0 / 5%)" />
                <XAxis
                  type="number"
                  dataKey="x"
                  name="Probability"
                  domain={[0, 100]}
                  tick={{ fontSize: 10, fill: "oklch(0.7 0 0)" }}
                  label={{ value: "Probability (%)", position: "bottom", fontSize: 10, fill: "oklch(0.5 0 0)" }}
                />
                <YAxis
                  type="number"
                  dataKey="y"
                  name="Impact"
                  domain={[0, 100]}
                  tick={{ fontSize: 10, fill: "oklch(0.7 0 0)" }}
                  label={{ value: "Impact (%)", angle: -90, position: "left", fontSize: 10, fill: "oklch(0.5 0 0)" }}
                />
                <ZAxis type="number" dataKey="z" range={[60, 400]} />
                <Tooltip content={<CustomScatterTooltip />} />
                <Scatter data={scatterData} fill="#8884d8">
                  {scatterData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={severityColors[entry.severity]?.dot || "#94a3b8"}
                      fillOpacity={0.7}
                    />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>

          {/* Legend */}
          <div className="flex items-center justify-center gap-4 mt-2">
            {["critical", "high", "medium", "low"].map((sev) => (
              <div key={sev} className="flex items-center gap-1.5">
                <div className={`w-2.5 h-2.5 rounded-full`} style={{ backgroundColor: severityColors[sev]?.dot }} />
                <span className="text-[10px] text-muted-foreground capitalize">{sev}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Tabbed 25-Item Lists */}
      <Card className="card-hover-lift border-border/30">
        <CardHeader>
          <CardTitle className="text-lg">Comprehensive Risk Inventory</CardTitle>
          <CardDescription>25 items across 5 risk categories</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="failures" className="w-full">
            <TabsList className="w-full flex flex-wrap h-auto gap-1 p-1">
              <TabsTrigger value="failures" className="text-xs flex-1 min-w-[120px]">
                <AlertTriangle className="w-3 h-3 mr-1" />
                Failures (25)
              </TabsTrigger>
              <TabsTrigger value="engineering" className="text-xs flex-1 min-w-[120px]">
                <Wrench className="w-3 h-3 mr-1" />
                Engineering (25)
              </TabsTrigger>
              <TabsTrigger value="research" className="text-xs flex-1 min-w-[120px]">
                <Search className="w-3 h-3 mr-1" />
                Research (25)
              </TabsTrigger>
              <TabsTrigger value="assumptions" className="text-xs flex-1 min-w-[120px]">
                <HelpCircle className="w-3 h-3 mr-1" />
                Assumptions (25)
              </TabsTrigger>
              <TabsTrigger value="scalability" className="text-xs flex-1 min-w-[120px]">
                <TrendingUp className="w-3 h-3 mr-1" />
                Scalability (25)
              </TabsTrigger>
            </TabsList>

            {/* Failure Points Tab */}
            <TabsContent value="failures">
              <div className="max-h-96 overflow-y-auto pr-2 custom-scrollbar">
                <div className="space-y-2">
                  {failurePoints.map((fp, i) => {
                    const colors = severityColors[fp.severity];
                    return (
                      <motion.div
                        key={fp.id}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.02 }}
                        className="flex flex-col md:flex-row md:items-center gap-2 p-3 rounded-lg bg-muted/20 border border-border/20 hover:bg-muted/30 transition-colors"
                      >
                        <div className="flex items-center gap-2 min-w-[40px]">
                          <div className={`w-6 h-6 rounded-md ${colors.bg} ${colors.border} border flex items-center justify-center ${colors.text} text-[10px] font-bold flex-shrink-0`}>
                            {fp.id}
                          </div>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-semibold">{fp.name}</span>
                            <Badge variant="outline" className={`text-[9px] ${severityBadgeColors[fp.severity]}`}>
                              {fp.severity}
                            </Badge>
                          </div>
                          <p className="text-xs text-muted-foreground mt-0.5">{fp.description}</p>
                        </div>
                        <div className="flex gap-3 flex-shrink-0">
                          <div className="text-center">
                            <div className="text-[9px] text-muted-foreground">Prob</div>
                            <div className={`text-xs font-bold ${colors.text}`}>{Math.round(fp.probability * 100)}%</div>
                          </div>
                          <div className="text-center">
                            <div className="text-[9px] text-muted-foreground">Impact</div>
                            <div className={`text-xs font-bold ${colors.text}`}>{Math.round(fp.impact * 100)}%</div>
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              </div>
            </TabsContent>

            {/* Engineering Challenges Tab */}
            <TabsContent value="engineering">
              <div className="max-h-96 overflow-y-auto pr-2 custom-scrollbar">
                <div className="space-y-2">
                  {engineeringChallenges.map((challenge, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.02 }}
                      className="flex items-start gap-3 p-2.5 rounded-md hover:bg-muted/20 transition-colors"
                    >
                      <div className="w-6 h-6 rounded-md bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 text-[10px] font-bold flex-shrink-0">
                        {i + 1}
                      </div>
                      <span className="text-sm text-foreground">{challenge}</span>
                    </motion.div>
                  ))}
                </div>
              </div>
            </TabsContent>

            {/* Research Gaps Tab */}
            <TabsContent value="research">
              <div className="max-h-96 overflow-y-auto pr-2 custom-scrollbar">
                <div className="space-y-2">
                  {researchGaps.map((gap, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.02 }}
                      className="flex items-start gap-3 p-2.5 rounded-md hover:bg-muted/20 transition-colors"
                    >
                      <div className="w-6 h-6 rounded-md bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400 text-[10px] font-bold flex-shrink-0">
                        {i + 1}
                      </div>
                      <span className="text-sm text-foreground">{gap}</span>
                    </motion.div>
                  ))}
                </div>
              </div>
            </TabsContent>

            {/* Assumptions Tab */}
            <TabsContent value="assumptions">
              <div className="max-h-96 overflow-y-auto pr-2 custom-scrollbar">
                <div className="space-y-2">
                  {assumptions.map((assumption, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.02 }}
                      className="flex items-start gap-3 p-2.5 rounded-md hover:bg-muted/20 transition-colors"
                    >
                      <div className="w-6 h-6 rounded-md bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 text-[10px] font-bold flex-shrink-0">
                        {i + 1}
                      </div>
                      <span className="text-sm text-foreground">{assumption}</span>
                    </motion.div>
                  ))}
                </div>
              </div>
            </TabsContent>

            {/* Scalability Bottlenecks Tab */}
            <TabsContent value="scalability">
              <div className="max-h-96 overflow-y-auto pr-2 custom-scrollbar">
                <div className="space-y-2">
                  {scalabilityBottlenecks.map((bottleneck, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.02 }}
                      className="flex items-start gap-3 p-2.5 rounded-md hover:bg-muted/20 transition-colors"
                    >
                      <div className="w-6 h-6 rounded-md bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-400 text-[10px] font-bold flex-shrink-0">
                        {i + 1}
                      </div>
                      <span className="text-sm text-foreground">{bottleneck}</span>
                    </motion.div>
                  ))}
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
