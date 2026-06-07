"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { StatusBadge } from "./status-badge";
import { FlowChart } from "./flow-chart";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { Badge } from "@/components/ui/badge";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { AlertTriangle, Sigma, TrendingDown } from "lucide-react";

const componentData = [
  {
    component: "HBTA",
    status: "Plausible" as const,
    justification:
      "O(Nd²logN) proven, approximation error downgraded to Plausible. Crossover N>d·logN is severe constraint",
    complexity: 65,
  },
  {
    component: "OTM",
    status: "Proven (Theory)" as const,
    justification:
      "Mathematically proven zero interference in exact arithmetic. fp16 drift requires fp32 master copies and QR retraction",
    complexity: 80,
  },
  {
    component: "Stiefel Manifold Opt.",
    status: "Proven" as const,
    justification: "Convergence to stationary points mathematically sound",
    complexity: 50,
  },
  {
    component: "Pingala Gating",
    status: "Experimental" as const,
    justification:
      "Gradient death possible if gates saturate. Requires careful initialization",
    complexity: 40,
  },
  {
    component: "Panini Constraints",
    status: "Plausible" as const,
    justification:
      "Soft constraint integration via product logic theoretically sound but practically unverified for deep logic tasks",
    complexity: 55,
  },
  {
    component: "Nyaya Verifier",
    status: "Plausible" as const,
    justification:
      "Upgraded from linear to MLP. Capable of distributional plausibility, not formal logic verification",
    complexity: 45,
  },
  {
    component: "Meta-Controller",
    status: "Proven (Local)" as const,
    justification:
      "Lyapunov stability only local within projected compact set, not global",
    complexity: 70,
  },
];

const complexityData = componentData.map((d) => ({
  name: d.component,
  complexity: d.complexity,
  status: d.status,
}));

const getStatusColor = (status: string) => {
  if (status.includes("Proven")) return "#10b981";
  if (status === "Plausible") return "#f59e0b";
  if (status === "Experimental") return "#f97316";
  if (status.includes("High Risk")) return "#ef4444";
  return "#94a3b8";
};

const dependencySteps = [
  { id: "input", label: "Input Sequence", description: "Token embedding", color: "bg-slate-800 border-slate-600" },
  { id: "hbta", label: "HBTA", description: "O(N log N) attention", color: "bg-emerald-900/50 border-emerald-500/30" },
  { id: "otm", label: "OTM", description: "Thread isolation", color: "bg-teal-900/50 border-teal-500/30" },
  { id: "meta", label: "Meta-Controller", description: "Lyapunov scheduling", color: "bg-amber-900/30 border-amber-500/30" },
  { id: "panini", label: "Panini/Nyaya", description: "Neuro-symbolic layer", color: "bg-orange-900/30 border-orange-500/30" },
  { id: "correction", label: "Correction Loop", description: "Self-correction", color: "bg-emerald-900/50 border-emerald-500/30" },
  { id: "nyaya", label: "Nyaya Sampling", description: "Rejection sampling", color: "bg-teal-900/50 border-teal-500/30" },
];

const crossoverData = [
  { d: 256, nStar: "≈2,048", speedup: "≈1.6×", advantage: true },
  { d: 512, nStar: "≈4,608", speedup: "≈0.67×", advantage: false },
  { d: 768, nStar: "≈7,680", speedup: "≈0.44×", advantage: false },
  { d: 1024, nStar: "≈10,240", speedup: "≈0.33×", advantage: false },
];

const provenItems = [
  { label: "Theorem 3.4 (HBTA Complexity)", detail: "C_HBTA = O(Nd²logN) formally proven" },
  { label: "Theorem 4.4 (Orthogonality Preservation)", detail: "Cayley retraction preserves SᵀS = Iₖ" },
  { label: "Corollary 4.5 (Zero Interference)", detail: "⟨Sᵢ, Sⱼ⟩ = 0 for all i ≠ j, proven" },
  { label: "Theorem 5.3 (Local Lyapunov Stability)", detail: "Controller stable within projected compact set" },
  { label: "Theorem 6.1 (Bounded Convergence)", detail: "Bounded convergence for OTM updates" },
];

const plausibleItems = [
  { label: "Theorem 3.6 (HBTA Approximation Error)", detail: "Error bound assumes exponential attention decay — not empirically validated" },
  { label: "Panini Soft Constraints", detail: "Product logic integration theoretically sound but practically unverified" },
  { label: "Nyaya Distributional Plausibility", detail: "MLP verifier approximates plausibility, not formal validity" },
];

const openItems = [
  { label: "Distance Concentration in Hierarchical Routing", detail: "Dot products concentrate in high dimensions — tree routing reliability unknown" },
  { label: "Nonlinear Bottleneck Optimality", detail: "Sphota autoencoder vs PCA optimality not analyzed" },
  { label: "MLP Verifier Logical Validity", detail: "Whether Nyaya MLP learns genuine logical validity remains open" },
];

export function Part1Analysis() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-2">
          Part 1 — Whitepaper Analysis
        </h2>
        <p className="text-muted-foreground">
          Critical assessment of each component in the Avadhan architecture, with
          mathematical justification and risk classification.
        </p>
      </div>

      {/* Component Classification Table */}
      <Card className="border-border/30">
        <CardHeader>
          <CardTitle className="text-lg">Component Classification</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[140px]">Component</TableHead>
                  <TableHead className="w-[160px]">Status</TableHead>
                  <TableHead>Justification</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {componentData.map((row, i) => (
                  <motion.tr
                    key={row.component}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, delay: i * 0.05 }}
                    className="border-b border-border/20"
                  >
                    <TableCell className="font-mono font-semibold text-sm">
                      {row.component}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={row.status} />
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {row.justification}
                    </TableCell>
                  </motion.tr>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Complexity Comparison Chart */}
      <Card className="border-border/30">
        <CardHeader>
          <CardTitle className="text-lg">Implementation Complexity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={complexityData} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(1 0 0 / 5%)" />
                <XAxis
                  type="number"
                  domain={[0, 100]}
                  tick={{ fontSize: 11, fill: "oklch(0.7 0 0)" }}
                />
                <YAxis
                  dataKey="name"
                  type="category"
                  width={120}
                  tick={{ fontSize: 11, fill: "oklch(0.7 0 0)" }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "oklch(0.2 0 0)",
                    border: "1px solid oklch(1 0 0 / 10%)",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                />
                <Bar dataKey="complexity" radius={[0, 4, 4, 0]}>
                  {complexityData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={getStatusColor(entry.status)}
                      fillOpacity={0.6}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Dependency Map */}
      <Card className="border-border/30">
        <CardHeader>
          <CardTitle className="text-lg">Dependency Map</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto pb-2">
            <FlowChart steps={dependencySteps} direction="horizontal" />
          </div>
          <p className="text-xs text-muted-foreground mt-4">
            Input tokens flow through HBTA for O(N log N) attention, then OTM for
            orthogonal thread isolation. The Meta-Controller schedules thread
            execution using Lyapunov stability. Panini/Nyaya apply neuro-symbolic
            constraints, with the correction loop feeding back through Nyaya
            rejection sampling.
          </p>
        </CardContent>
      </Card>

      {/* Mathematical Foundations */}
      <Card className="border-border/30">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Sigma className="w-5 h-5 text-emerald-400" />
            <CardTitle className="text-lg">Mathematical Foundations</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="p-4 rounded-lg bg-muted/20 border border-border/20"
            >
              <div className="text-sm font-semibold text-emerald-400 mb-2">HBTA Complexity</div>
              <code className="text-xs font-mono text-foreground block bg-card/50 p-3 rounded-md border border-border/10">
                C_HBTA = O(Nd²logN)
              </code>
              <div className="mt-2 text-xs text-muted-foreground">
                Breakdown: C_agg = O(Nd²) aggregation per level, C_attn = O(Nd²) attention computation, C_broad = O(Nd²) gated-sum broadcast. Total across logN levels.
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="p-4 rounded-lg bg-muted/20 border border-border/20"
            >
              <div className="text-sm font-semibold text-teal-400 mb-2">OTM Cayley Retraction</div>
              <code className="text-xs font-mono text-foreground block bg-card/50 p-3 rounded-md border border-border/10">
                S_{'{t+1}'} = (I + A)⁻¹(I - A)S_t, where A = ηW/2, W = ΔS^T - SΔ^T
              </code>
              <div className="mt-2 text-xs text-muted-foreground">
                Cayley retraction preserves orthogonality: S_{'{t+1}'}^T S_{'{t+1}'} = I_K by construction. The skew-symmetric matrix W ensures (I+A)⁻¹(I-A) is orthogonal.
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="p-4 rounded-lg bg-muted/20 border border-border/20"
            >
              <div className="text-sm font-semibold text-green-400 mb-2">Stiefel Gradient</div>
              <code className="text-xs font-mono text-foreground block bg-card/50 p-3 rounded-md border border-border/10">
                grad_R F(S) = ∇_S F - S·sym(S^T ∇_S F)
              </code>
              <div className="mt-2 text-xs text-muted-foreground">
                Riemannian gradient on Stiefel Manifold St(d,K). sym(M) = (M + M^T)/2 projects the Euclidean gradient onto the tangent space of the manifold.
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="p-4 rounded-lg bg-muted/20 border border-border/20"
            >
              <div className="text-sm font-semibold text-cyan-400 mb-2">Gated-Sum Broadcast</div>
              <code className="text-xs font-mono text-foreground block bg-card/50 p-3 rounded-md border border-border/10">
                ctx_i = Σ_k G_k(W_k · anc_k(i)), ctx ∈ R^d
              </code>
              <div className="mt-2 text-xs text-muted-foreground">
                Replaces leaf concatenation from v1. Each ancestor contribution is gated by learned G_k, allowing the model to selectively attend to relevant hierarchical context.
              </div>
            </motion.div>
          </div>
        </CardContent>
      </Card>

      {/* Crossover Analysis */}
      <Card className="border-border/30">
        <CardHeader>
          <div className="flex items-center gap-2">
            <TrendingDown className="w-5 h-5 text-amber-400" />
            <CardTitle className="text-lg">HBTA vs FlashAttention Crossover Analysis</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>d (dim)</TableHead>
                  <TableHead>N* (approx.)</TableHead>
                  <TableHead>Speedup at N=4096</TableHead>
                  <TableHead>HBTA Advantage?</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {crossoverData.map((row) => (
                  <TableRow key={row.d}>
                    <TableCell className="font-mono text-sm">{row.d}</TableCell>
                    <TableCell className="font-mono text-sm">{row.nStar}</TableCell>
                    <TableCell className="font-mono text-sm">{row.speedup}</TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={`text-[10px] ${
                          row.advantage
                            ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                            : "bg-red-500/10 text-red-400 border-red-500/20"
                        }`}
                      >
                        {row.advantage ? "Yes" : "No (slower)"}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="mt-4 p-3 rounded-lg bg-amber-500/5 border border-amber-500/20 flex items-start gap-2"
          >
            <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-muted-foreground">
              <span className="text-amber-400 font-semibold">Key Finding:</span> HBTA&apos;s advantage is realised only at large N (N ≳ 5,000–10,000 for typical d). For short-to-medium sequences with large d, FlashAttention is faster. This motivates the Hybrid Attention approach: FlashAttention for N &lt; 4096, switch to HBTA for N &gt; 4096.
            </p>
          </motion.div>
        </CardContent>
      </Card>

      {/* Proven vs Plausible Inventory */}
      <Card className="border-border/30">
        <CardHeader>
          <CardTitle className="text-lg">Proven vs Plausible Inventory</CardTitle>
        </CardHeader>
        <CardContent>
          <Accordion type="multiple" className="w-full">
            <AccordionItem value="proven">
              <AccordionTrigger>
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                  <span className="text-sm font-semibold">Proven ({provenItems.length})</span>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-2">
                  {provenItems.map((item, i) => (
                    <motion.div
                      key={item.label}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="flex items-start gap-2 p-2 rounded-md bg-emerald-500/5 border border-emerald-500/10"
                    >
                      <StatusBadge status="Proven" />
                      <div>
                        <div className="text-sm font-medium">{item.label}</div>
                        <div className="text-xs text-muted-foreground mt-0.5">{item.detail}</div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="plausible">
              <AccordionTrigger>
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                  <span className="text-sm font-semibold">Plausible ({plausibleItems.length})</span>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-2">
                  {plausibleItems.map((item, i) => (
                    <motion.div
                      key={item.label}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="flex items-start gap-2 p-2 rounded-md bg-amber-500/5 border border-amber-500/10"
                    >
                      <StatusBadge status="Plausible" />
                      <div>
                        <div className="text-sm font-medium">{item.label}</div>
                        <div className="text-xs text-muted-foreground mt-0.5">{item.detail}</div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="open">
              <AccordionTrigger>
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-slate-400" />
                  <span className="text-sm font-semibold">Open Questions ({openItems.length})</span>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-2">
                  {openItems.map((item, i) => (
                    <motion.div
                      key={item.label}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="flex items-start gap-2 p-2 rounded-md bg-slate-500/5 border border-slate-500/10"
                    >
                      <Badge variant="outline" className="text-[10px] bg-slate-500/20 text-slate-400 border-slate-500/30 flex-shrink-0">
                        Open
                      </Badge>
                      <div>
                        <div className="text-sm font-medium">{item.label}</div>
                        <div className="text-xs text-muted-foreground mt-0.5">{item.detail}</div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </CardContent>
      </Card>
    </div>
  );
}
