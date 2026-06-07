"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
  Flame,
  Download,
  GitMerge,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ArrowRight,
  DollarSign,
  Server,
  AlertCircle,
  Brain,
} from "lucide-react";

const pathways = [
  {
    label: "Path A",
    title: "Train from Scratch",
    icon: <Flame className="w-5 h-5" />,
    color: "red",
    resources: "1000+ GPUs",
    feasibility: "Impossible for startup",
    verdict: "NOT RECOMMENDED",
    pros: ["Full architecture control", "No legacy constraints"],
    cons: ["Prohibitively expensive", "Years of training time", "Requires massive data"],
  },
  {
    label: "Path B",
    title: "Distill from Existing",
    icon: <Download className="w-5 h-5" />,
    color: "amber",
    resources: "50-100 GPUs",
    feasibility: "Loses AHC architecture",
    verdict: "NOT RECOMMENDED",
    pros: ["Faster to prototype", "Leverages existing models"],
    cons: ["Cannot preserve OTM structure", "Loses thread isolation", "Limited innovation"],
  },
  {
    label: "Path C",
    title: "Hybrid Strategy",
    icon: <GitMerge className="w-5 h-5" />,
    color: "emerald",
    resources: "4x A100s initially",
    feasibility: "Feasible for startup",
    verdict: "RECOMMENDED",
    pros: ["Preserves core innovations", "Incremental validation", "Risk-managed approach"],
    cons: ["Complex orchestration", "Multiple training phases"],
  },
];

const phases = [
  {
    phase: 1,
    title: "Connective Tissue Training",
    duration: "2 weeks",
    resources: "4x A100s",
    description: "Train OTM/NSK connective layers while keeping backbone frozen. Validates thread isolation on small scale.",
    success: "20%+ gains on thread isolation metrics",
    color: "emerald",
  },
  {
    phase: 2,
    title: "Neuro-Symbolic Fine-Tuning",
    duration: "4 weeks",
    resources: "8x A100s",
    description: "Synthetic data generation for Panini constraints and Nyaya verifier. Soft constraint integration testing.",
    success: "Constraint satisfaction > 85% on logic benchmarks",
    color: "teal",
  },
  {
    phase: 3,
    title: "Continuous Pre-training",
    duration: "8-12 weeks",
    resources: "32-64x A100s",
    description: "Full pre-training only if Phase 1 shows 20%+ gains. Scale up HBTA and OTM across all layers.",
    success: "Competitive with base model + thread isolation",
    color: "green",
  },
];

const computeRequirements = [
  { phase: "Phase 1", duration: "2 weeks", resources: "4× A100s", costEst: "~$5,000" },
  { phase: "Phase 2", duration: "4 weeks", resources: "8× A100s", costEst: "~$20,000" },
  { phase: "Phase 3", duration: "8-12 weeks", resources: "32-64× A100s", costEst: "~$200,000-$500,000" },
];

const colorStyles: Record<string, { bg: string; border: string; text: string; badge: string }> = {
  red: { bg: "bg-red-500/10", border: "border-red-500/20", text: "text-red-400", badge: "bg-red-500/20 text-red-400 border-red-500/30" },
  amber: { bg: "bg-amber-500/10", border: "border-amber-500/20", text: "text-amber-400", badge: "bg-amber-500/20 text-amber-400 border-amber-500/30" },
  emerald: { bg: "bg-emerald-500/10", border: "border-emerald-500/20", text: "text-emerald-400", badge: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
  teal: { bg: "bg-teal-500/10", border: "border-teal-500/20", text: "text-teal-400", badge: "bg-teal-500/20 text-teal-400 border-teal-500/30" },
  green: { bg: "bg-green-500/10", border: "border-green-500/20", text: "text-green-400", badge: "bg-green-500/20 text-green-400 border-green-500/30" },
};

export function Part4Training() {
  return (
    <div className="space-y-8">
      <div>
        <h2 id="training-strategy" className="text-2xl font-bold text-foreground mb-2">
          Part 4 — Training Strategy
        </h2>
        <p className="text-muted-foreground">
          Three possible training pathways for AFM, with the recommended hybrid
          strategy broken into three incremental phases.
        </p>
        <Badge variant="outline" className="text-[10px] bg-emerald-500/10 text-emerald-400 border-emerald-500/20 font-mono mt-2">
          PATH C: HYBRID STRATEGY
        </Badge>
      </div>

      {/* Pathway Cards — Gradient Header on first (emerald) card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {pathways.map((path, i) => {
          const colors = colorStyles[path.color];
          return (
            <motion.div
              key={path.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.15 }}
            >
              <Card className={`card-hover-lift h-full ${path.color === "emerald" ? "border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10 ring-1 ring-emerald-500/30" : "border-border/30"}`}>
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg ${colors.bg} ${colors.border} border flex items-center justify-center ${colors.text}`}>
                      {path.icon}
                    </div>
                    <div>
                      <CardDescription className="text-xs font-mono">
                        {path.label}
                      </CardDescription>
                      <CardTitle className="text-base">{path.title}</CardTitle>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center gap-2 text-xs">
                    <Clock className="w-3 h-3 text-muted-foreground" />
                    <span className="text-muted-foreground">Resources:</span>
                    <span className="font-mono">{path.resources}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {path.feasibility}
                  </div>
                  <Badge
                    variant="outline"
                    className={`text-xs ${colors.badge}`}
                  >
                    {path.verdict}
                  </Badge>
                  <div className="space-y-1.5 pt-2">
                    <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Pros
                    </div>
                    {path.pros.map((pro) => (
                      <div key={pro} className="flex items-center gap-1.5 text-xs">
                        <CheckCircle2 className="w-3 h-3 text-emerald-500 flex-shrink-0" />
                        <span>{pro}</span>
                      </div>
                    ))}
                  </div>
                  <div className="space-y-1.5">
                    <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Cons
                    </div>
                    {path.cons.map((con) => (
                      <div key={con} className="flex items-center gap-1.5 text-xs">
                        <AlertTriangle className="w-3 h-3 text-amber-500 flex-shrink-0" />
                        <span>{con}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </div>

      {/* Phase Timeline */}
      <div>
        <h3 className="text-lg font-semibold text-foreground mb-4">
          Path C: Hybrid Strategy Phases
        </h3>
        <div className="space-y-0">
          {phases.map((phase, i) => {
            const colors = colorStyles[phase.color];
            return (
              <motion.div
                key={phase.phase}
                initial={{ opacity: 0, x: -30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + i * 0.2 }}
                className="relative"
              >
                {/* Timeline line */}
                {i < phases.length - 1 && (
                  <div className="absolute left-5 top-14 bottom-0 w-0.5 bg-border/30" />
                )}
                <div className="flex gap-4 pb-6">
                  {/* Phase indicator */}
                  <div className={`w-10 h-10 rounded-full ${colors.bg} border ${colors.border} flex items-center justify-center ${colors.text} font-bold text-sm flex-shrink-0 z-10`}>
                    {phase.phase}
                  </div>
                  <Card className="card-hover-lift flex-1 border-border/30">
                    <CardContent className="p-4">
                      <div className="flex flex-col md:flex-row md:items-center justify-between mb-2">
                        <div>
                          <div className="text-sm font-semibold text-foreground">
                            {phase.title}
                          </div>
                          <div className="flex items-center gap-3 mt-1">
                            <Badge variant="outline" className="text-[10px] font-mono bg-muted/30">
                              <Clock className="w-2.5 h-2.5 mr-1" />
                              {phase.duration}
                            </Badge>
                            <Badge variant="outline" className="text-[10px] font-mono bg-muted/30">
                              {phase.resources}
                            </Badge>
                          </div>
                        </div>
                      </div>
                      <p className="text-xs text-muted-foreground mt-2">
                        {phase.description}
                      </p>
                      <div className="mt-2 text-xs">
                        <span className="text-muted-foreground">Success criterion: </span>
                        <span className={colors.text}>{phase.success}</span>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* Phase Dependency Flow */}
      <Card className="card-hover-lift border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
              <GitMerge className="w-5 h-5" />
            </div>
            <div>
              <CardTitle className="text-lg text-emerald-400">Phase Dependency Flow</CardTitle>
              <CardDescription className="text-emerald-400/70">Gated progression with go/no-go decision points</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-3">
            {[
              {
                label: "Phase 1: Connective Tissue",
                sub: "Train OTM/NSK layers",
                color: "bg-emerald-900/50 border-emerald-500/30",
                note: undefined,
              },
              {
                label: "Gate: Validate",
                sub: "Only proceed if Phase 1 validates",
                color: "bg-amber-900/30 border-amber-500/30",
                note: "Must show thread isolation gains",
              },
              {
                label: "Phase 2: Neuro-Symbolic FT",
                sub: "Panini/Nyaya fine-tuning",
                color: "bg-teal-900/50 border-teal-500/30",
                note: undefined,
              },
              {
                label: "Gate: 20%+ Check",
                sub: "Only proceed if Phase 1 shows 20%+ gains",
                color: "bg-amber-900/30 border-amber-500/30",
                note: "Critical go/no-go decision",
              },
              {
                label: "Phase 3: Full Pre-training",
                sub: "Scale up across all layers",
                color: "bg-green-900/50 border-green-500/30",
                note: undefined,
              },
            ].map((step, i) => (
              <div key={step.label} className="flex flex-col items-center">
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: i * 0.15 }}
                  className={`px-6 py-3 rounded-lg border ${step.color} text-center min-w-[240px]`}
                >
                  <div className="text-sm font-semibold">{step.label}</div>
                  <div className="text-[10px] text-muted-foreground">{step.sub}</div>
                  {step.note && (
                    <div className="mt-1 text-[9px] text-amber-400 font-mono">
                      ! {step.note}
                    </div>
                  )}
                </motion.div>
                {i < 4 && (
                  <ArrowRight className="w-4 h-4 text-emerald-500/50 rotate-90 my-1" />
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Compute Requirements */}
      <Card className="card-hover-lift border-border/30">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
              <DollarSign className="w-5 h-5" />
            </div>
            <div>
              <CardTitle className="text-lg">Compute Requirements</CardTitle>
              <CardDescription>Hardware and cost estimates per training phase</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Phase</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Resources</TableHead>
                  <TableHead>Cost Est.</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {computeRequirements.map((row) => (
                  <TableRow key={row.phase}>
                    <TableCell className="font-semibold text-sm">{row.phase}</TableCell>
                    <TableCell className="font-mono text-xs">{row.duration}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-[10px] bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                        <Server className="w-2.5 h-2.5 mr-1" />
                        {row.resources}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs">{row.costEst}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="mt-4 p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20 flex items-start gap-2"
          >
            <AlertCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-muted-foreground">
              <span className="text-emerald-400 font-semibold">Total estimated cost:</span> Phase 1-2 can be completed for ~$25,000, making initial validation affordable. Phase 3 ($200K-$500K) is only pursued if Phase 1 validates, minimizing risk.
            </p>
          </motion.div>
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
                Key Innovation: Gated Incremental Training
              </div>
              <p className="text-xs text-muted-foreground">
                Path C&apos;s gated approach is uniquely suited for a startup: Phase 1 costs only ~$5,000
                and validates the core OTM/NSK hypothesis before committing further resources. This
                de-risks the entire training pipeline — if thread isolation doesn&apos;t show 20%+ gains,
                the project pivots without having spent $500K. The connective tissue strategy (training
                only new layers while freezing the backbone) is analogous to surgical precision: modify
                only what&apos;s necessary, validate empirically, then scale. This is the path that makes
                ACOS economically viable while preserving all theoretical innovations.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
