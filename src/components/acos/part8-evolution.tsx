"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  ShieldCheck,
  Sparkles,
  Wrench,
  Brain,
  AlertTriangle,
  Search,
  Cpu,
  Target,
  RefreshCw,
  Users,
} from "lucide-react";
import { SectionHeader } from "./section-header";

const capabilities = [
  {
    name: "Prompt Evolution",
    category: "Realistic",
    description: "System can refine and optimize its own prompts based on user feedback and task outcomes",
    risk: "low",
    timeline: "Near-term",
    icon: <Wrench className="w-4 h-4" />,
  },
  {
    name: "Skill Acquisition",
    category: "Realistic",
    description: "Learn new skills from demonstration and instruction without forgetting prior skills",
    risk: "low",
    timeline: "Near-term",
    icon: <ShieldCheck className="w-4 h-4" />,
  },
  {
    name: "Architecture Search",
    category: "Realistic",
    description: "Experimentally search for optimal layer configurations and hyperparameters",
    risk: "medium",
    timeline: "Mid-term",
    icon: <Search className="w-4 h-4" />,
  },
  {
    name: "Self-Modifying Architecture",
    category: "Speculative",
    description: "Autonomously modify its own neural architecture during runtime",
    risk: "high",
    timeline: "Far-term",
    icon: <Cpu className="w-4 h-4" />,
  },
  {
    name: "Autonomous Goal Generation",
    category: "Speculative",
    description: "Generate its own objectives and learning goals without human direction",
    risk: "high",
    timeline: "Far-term",
    icon: <Sparkles className="w-4 h-4" />,
  },
];

const categoryColors: Record<string, { bg: string; border: string; text: string }> = {
  Realistic: { bg: "bg-emerald-500/10", border: "border-emerald-500/20", text: "text-emerald-400" },
  Speculative: { bg: "bg-red-500/10", border: "border-red-500/20", text: "text-red-400" },
};

const riskColors: Record<string, string> = {
  low: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  medium: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  high: "bg-red-500/20 text-red-400 border-red-500/30",
};

const spectrumPositions = [
  { name: "Prompt Evolution", position: 10 },
  { name: "Skill Acquisition", position: 25 },
  { name: "Architecture Search", position: 50 },
  { name: "Self-Modifying Arch.", position: 75 },
  { name: "Autonomous Goals", position: 95 },
];

export function Part8Evolution() {
  return (
    <div className="space-y-10">
      <SectionHeader
        sectionNumber={8}
        title="Self-Evolution"
        subtitle="Self-modifying system with prompt evolution and reflection"
        badge="SELF-MODIFYING"
        icon={<Sparkles className="w-5 h-5" />}
        id="self-evolution"
      />

      {/* Capability Cards */}
      <div className="space-y-4">
        {capabilities.map((cap, i) => {
          const colors = categoryColors[cap.category];
          return (
            <motion.div
              key={cap.name}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
            >
              <Card className={`magnetic-hover card-hover-lift ${i === 0 ? "glass-card-premium border-emerald-500/20" : "border-border/30"}`}>
                <CardContent className="p-4">
                  {i === 0 && <div className="gradient-accent-bar mb-4" />}
                  <div className="flex flex-col md:flex-row md:items-center gap-4">
                    <div className={`w-10 h-10 rounded-lg ${colors.bg} ${colors.border} border flex items-center justify-center ${colors.text} flex-shrink-0`}>
                      {cap.icon}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-semibold">{cap.name}</span>
                        <Badge variant="outline" className={`text-[10px] ${colors.bg} ${colors.text} ${colors.border}`}>
                          {cap.category}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">{cap.description}</p>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <Badge variant="outline" className={`text-[10px] ${riskColors[cap.risk]}`}>
                        <AlertTriangle className="w-2.5 h-2.5 mr-1" />
                        {cap.risk} risk
                      </Badge>
                      <Badge variant="outline" className="text-[10px] bg-muted/30">
                        {cap.timeline}
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </div>

      {/* Spectrum Chart */}
      <Card className="card-hover-lift border-border/30">
        <CardHeader>
          <CardTitle className="text-lg">Safety-Speculation Spectrum</CardTitle>
          <CardDescription className="mb-2">Risk classification from safe to speculative</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="relative py-8">
            {/* Spectrum bar */}
            <div className="relative h-3 rounded-full bg-gradient-to-r from-emerald-500 via-amber-500 to-red-500 opacity-30" />

            {/* Labels */}
            <div className="flex justify-between mt-2">
              <span className="text-xs text-emerald-400 font-semibold">Safe</span>
              <span className="text-xs text-amber-400 font-semibold">Experimental</span>
              <span className="text-xs text-red-400 font-semibold">Speculative</span>
            </div>

            {/* Capability markers */}
            <div className="relative mt-6">
              {spectrumPositions.map((item, i) => (
                <motion.div
                  key={item.name}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 + i * 0.1 }}
                  className="absolute"
                  style={{ left: `${item.position}%`, transform: "translateX(-50%)" }}
                >
                  <div className={`w-3 h-3 rounded-full ${
                    item.position < 40 ? "bg-emerald-500" : item.position < 65 ? "bg-amber-500" : "bg-red-500"
                  }`} />
                  <div className="text-[9px] text-muted-foreground mt-1 whitespace-nowrap text-center max-w-[80px]">
                    {item.name}
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Key Insight */}
      <Card className="card-hover-lift border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardContent className="p-6">
          <div className="flex items-start gap-3">
            <Target className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
            <div>
              <div className="text-sm font-semibold text-foreground mb-1">
                Practical Stance on Self-Evolution
              </div>
              <p className="text-xs text-muted-foreground">
                ACOS focuses on realistic self-evolution: prompt optimization, skill
                acquisition, and architecture search. Self-modifying architectures
                and autonomous goal generation remain speculative and are
                deliberately deprioritized until safety guarantees are established.
                The Nyaya Verifier serves as the safety gate for all self-modification.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Reflection & Self-Critique */}
      <Card className="card-hover-lift border-teal-500/20 bg-gradient-to-r from-teal-900/10 to-emerald-900/10">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-teal-400" />
            <CardTitle className="text-lg text-teal-400">Reflection & Self-Critique</CardTitle>
          </div>
          <CardDescription className="text-teal-400/70 mb-2">Self-evaluation and correction mechanisms</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="p-4 rounded-lg bg-card/50 border border-teal-500/15">
              <div className="text-sm font-semibold text-teal-400 mb-2">Nyaya Self-Evaluation</div>
              <p className="text-xs text-muted-foreground mb-2">
                ACOS can evaluate its own outputs via the Nyaya Verifier energy function:
              </p>
              <code className="prose-code-block text-xs font-mono text-foreground block">
                E(h) = -1/d_v * 1^T log V(h) &gt;= 0
              </code>
              <p className="text-xs text-muted-foreground mt-2">
                When E(h) &gt; tau (exceeds the acceptance threshold), smooth rejection sampling refines the output.
              </p>
            </div>

            <div className="p-4 rounded-lg bg-card/50 border border-teal-500/15">
              <div className="text-sm font-semibold text-teal-400 mb-2">Smooth Rejection Sampling</div>
              <code className="prose-code-block text-xs font-mono text-foreground block">
                h_tilde = h_hat - eta_r * sigma((E(h_hat)-tau)/beta_r) * grad_h E(h_hat)
              </code>
              <p className="text-xs text-muted-foreground mt-2">
                Unlike hard rejection (discard and retry), smooth rejection sampling gradually adjusts the output toward the acceptance region. The sigmoid sigma controls the strength of correction -- weak when E is near tau, strong when E far exceeds tau.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Agent Evolution */}
      <Card className="card-hover-lift border-green-500/20 bg-gradient-to-r from-green-900/10 to-teal-900/10">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-green-400" />
            <CardTitle className="text-lg text-green-400">Agent Evolution</CardTitle>
          </div>
          <CardDescription className="text-green-400/70 mb-2">Dynamic composition and improvement</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-start gap-3 p-3 rounded-lg bg-card/50 border border-green-500/15">
              <RefreshCw className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
              <div>
                <div className="text-sm font-semibold text-green-400">Dynamic Agent Composition</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Agents can be composed dynamically. ACOS spawns agent combinations based on task requirements, learning which compositions work best over time through Meta-Controller feedback.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 rounded-lg bg-card/50 border border-green-500/15">
              <Sparkles className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
              <div>
                <div className="text-sm font-semibold text-green-400">Evolutionary Improvement</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Over time, ACOS learns which agent compositions produce the best results for specific task types. This is not random mutation — it is directed by Lyapunov stability guarantees and Nyaya verification of agent outputs.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
