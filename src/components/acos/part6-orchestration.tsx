"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Workflow,
  Search,
  Code,
  Calculator,
  ShieldCheck,
  ArrowRight,
  Cloud,
  Laptop,
  RefreshCw,
  DollarSign,
} from "lucide-react";
import { SectionHeader } from "./section-header";

const routingLevels = [
  {
    level: 1,
    title: "Intent Classification",
    description: "Fast, small model classifies the user's intent",
    model: "Lightweight classifier",
    latency: "< 10ms",
    color: "emerald",
  },
  {
    level: 2,
    title: "Thread Allocation",
    description: "Routes to specialized model combinations based on intent",
    model: "Dynamic routing",
    latency: "< 50ms",
    color: "teal",
  },
  {
    level: 3,
    title: "Consensus Check",
    description: "If >20% confidence margin disagreement -> spawn Verification Thread",
    model: "Meta-Controller",
    latency: "Variable",
    color: "amber",
  },
];

const supportedModels = [
  { name: "Gemma", provider: "Google", specialization: "General purpose", useCase: "Lightweight tasks" },
  { name: "Llama", provider: "Meta", specialization: "General purpose", useCase: "Open-source backbone" },
  { name: "Qwen", provider: "Alibaba", specialization: "Multilingual", useCase: "Non-English tasks" },
  { name: "DeepSeek-Coder", provider: "DeepSeek", specialization: "Code generation", useCase: "Programming tasks" },
  { name: "Mistral", provider: "Mistral AI", specialization: "Efficient reasoning", useCase: "Fast inference" },
  { name: "AFM", provider: "Avadhan", specialization: "Cognitive reasoning", useCase: "Thread-isolated reasoning" },
];

const routingExamples = [
  { intent: "Code Task", route: "DeepSeek-Coder + AFM", threads: ["Coding", "Verification"] },
  { intent: "Math Problem", route: "AFM Logic + WolframAlpha", threads: ["Mathematical", "Verification"] },
  { intent: "Research Query", route: "AFM + Web Search + Gemma", threads: ["Research", "Memory Retrieval"] },
  { intent: "Creative Writing", route: "Llama + AFM Creative", threads: ["Creative", "Planning"] },
];

const colorStyles: Record<string, { bg: string; border: string; text: string; dot: string }> = {
  emerald: { bg: "bg-emerald-500/10", border: "border-emerald-500/20", text: "text-emerald-400", dot: "bg-emerald-500" },
  teal: { bg: "bg-teal-500/10", border: "border-teal-500/20", text: "text-teal-400", dot: "bg-teal-500" },
  amber: { bg: "bg-amber-500/10", border: "border-amber-500/20", text: "text-amber-400", dot: "bg-amber-500" },
};

const cloudLocalItems = [
  {
    icon: <Laptop className="w-5 h-5" />,
    title: "Local Execution",
    desc: "AFM + lightweight models for privacy-sensitive tasks",
    color: "emerald",
    items: ["Privacy-first processing", "Low latency responses", "Works offline", "User data stays on device"],
  },
  {
    icon: <Cloud className="w-5 h-5" />,
    title: "Cloud Execution",
    desc: "Large models (Gemma/Llama) for compute-heavy tasks",
    color: "teal",
    items: ["Access to larger models", "More compute available", "Broader knowledge base", "Scalable resources"],
  },
  {
    icon: <RefreshCw className="w-5 h-5" />,
    title: "Hybrid Execution",
    desc: "AFM drafts locally, cloud models verify/refine",
    color: "amber",
    items: ["Best of both worlds", "Local draft + cloud verify", "Graceful degradation", "Cost optimized"],
  },
];

const costOptimization = [
  { query: "Simple queries", model: "Lightweight model (Gemma-2B)", reason: "Fast and cheap", icon: <DollarSign className="w-3.5 h-3.5" /> },
  { query: "Complex reasoning", model: "AFM with multiple threads", reason: "Deep analysis required", icon: <Workflow className="w-3.5 h-3.5" /> },
  { query: "Code tasks", model: "DeepSeek-Coder", reason: "Specialized, cheaper", icon: <Code className="w-3.5 h-3.5" /> },
  { query: "Consensus needed", model: "Multi-model voting", reason: "Highest confidence", icon: <ShieldCheck className="w-3.5 h-3.5" /> },
];

export function Part6Orchestration() {
  return (
    <div className="space-y-8">
      <SectionHeader
        sectionNumber={6}
        title="Model Orchestration"
        subtitle="3-level Pingala routing for intelligent model selection"
        badge="3-LEVEL ROUTING"
        icon={<Workflow className="w-5 h-5" />}
        id="model-orchestration"
      />

      {/* Routing Levels */}
      <div className="space-y-4">
        {routingLevels.map((level, i) => {
          const colors = colorStyles[level.color];
          return (
            <motion.div
              key={level.level}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.15 }}
            >
              <Card className={`card-hover-lift ${i === 0 ? "border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10" : "border-border/30"}`}>
                <CardContent className="p-4">
                  <div className="flex flex-col md:flex-row md:items-center gap-4">
                    <div className={`w-12 h-12 rounded-xl ${colors.bg} ${colors.border} border flex items-center justify-center ${colors.text} font-bold text-lg flex-shrink-0`}>
                      L{level.level}
                    </div>
                    <div className="flex-1">
                      <div className="text-sm font-semibold text-foreground">
                        {level.title}
                      </div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {level.description}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge variant="outline" className="text-[10px] font-mono bg-muted/30">
                        {level.model}
                      </Badge>
                      <Badge variant="outline" className="text-[10px] font-mono bg-muted/30">
                        {level.latency}
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </div>

      {/* Routing Flow Diagram */}
      <Card className="card-hover-lift border-border/30">
        <CardHeader>
          <CardTitle className="text-lg">Routing Flow</CardTitle>
          <CardDescription>Step-by-step query processing pipeline</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-3">
            {[
              { label: "User Input", sub: "Query / Task", color: "bg-slate-800 border-slate-600" },
              { label: "Intent Classification", sub: "Level 1 — Fast classifier", color: "bg-emerald-900/50 border-emerald-500/30" },
              { label: "Thread Allocation", sub: "Level 2 — Dynamic routing", color: "bg-teal-900/50 border-teal-500/30" },
              { label: "Consensus Check", sub: "Level 3 — Verification", color: "bg-amber-900/30 border-amber-500/30" },
              { label: "Final Output", sub: "Verified response", color: "bg-emerald-900/50 border-emerald-500/30" },
            ].map((step, i) => (
              <div key={step.label} className="flex flex-col items-center">
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: i * 0.15 }}
                  className={`px-6 py-3 rounded-lg border ${step.color} text-center min-w-[200px]`}
                >
                  <div className="text-sm font-semibold">{step.label}</div>
                  <div className="text-[10px] text-muted-foreground">{step.sub}</div>
                </motion.div>
                {i < 4 && (
                  <ArrowRight className="w-4 h-4 text-emerald-500/50 rotate-90 my-1" />
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Supported Models */}
      <Card className="card-hover-lift border-border/30">
        <CardHeader>
          <CardTitle className="text-lg">Supported Models</CardTitle>
          <CardDescription>Models integrated into the ACOS routing system</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {supportedModels.map((model, i) => (
              <motion.div
                key={model.name}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.08 }}
                className={`p-3 rounded-lg bg-muted/20 border border-border/20 ${
                  model.name === "AFM" ? "ring-1 ring-emerald-500/30 bg-emerald-500/5" : ""
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <div className={`w-2 h-2 rounded-full ${model.name === "AFM" ? "bg-emerald-500" : "bg-muted-foreground/50"}`} />
                  <span className="text-sm font-semibold">{model.name}</span>
                </div>
                <div className="text-[10px] text-muted-foreground">
                  {model.provider} · {model.specialization}
                </div>
                <div className="text-[10px] text-muted-foreground mt-0.5">
                  Use: {model.useCase}
                </div>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Routing Examples */}
      <Card className="card-hover-lift border-border/30">
        <CardHeader>
          <CardTitle className="text-lg">Routing Examples</CardTitle>
          <CardDescription>How different task types are routed to model combinations</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {routingExamples.map((ex) => (
              <div
                key={ex.intent}
                className="flex flex-col md:flex-row md:items-center gap-3 p-3 rounded-lg bg-muted/20 border border-border/20"
              >
                <div className="flex items-center gap-2 min-w-[120px]">
                  <Search className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-sm font-semibold">{ex.intent}</span>
                </div>
                <ArrowRight className="w-3 h-3 text-muted-foreground hidden md:block" />
                <div className="flex items-center gap-2 min-w-[200px]">
                  <span className="text-xs font-mono text-teal-400">
                    {ex.route}
                  </span>
                </div>
                <div className="flex gap-1 flex-wrap">
                  {ex.threads.map((thread) => (
                    <Badge
                      key={thread}
                      variant="outline"
                      className="text-[10px] bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                    >
                      {thread}
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Local + Cloud Execution */}
      <Card className="card-hover-lift border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Cloud className="w-5 h-5 text-emerald-400" />
            <CardTitle className="text-lg text-emerald-400">Local + Cloud Execution</CardTitle>
          </div>
          <CardDescription className="text-emerald-400/70">Flexible deployment across local, cloud, and hybrid modes</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {cloudLocalItems.map((item, i) => {
              const colors = colorStyles[item.color];
              return (
                <motion.div
                  key={item.title}
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.15 }}
                  className="p-4 rounded-lg bg-card/50 border border-border/20"
                >
                  <div className={`w-10 h-10 rounded-lg ${colors.bg} ${colors.border} border flex items-center justify-center ${colors.text} mb-3`}>
                    {item.icon}
                  </div>
                  <div className="text-sm font-semibold text-foreground mb-1">{item.title}</div>
                  <p className="text-xs text-muted-foreground mb-3">{item.desc}</p>
                  <div className="space-y-1.5">
                    {item.items.map((subItem) => (
                      <div key={subItem} className="flex items-center gap-1.5 text-xs">
                        <div className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} />
                        <span className="text-muted-foreground">{subItem}</span>
                      </div>
                    ))}
                  </div>
                </motion.div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Cost Optimization */}
      <Card className="card-hover-lift border-border/30">
        <CardHeader>
          <div className="flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-emerald-400" />
            <CardTitle className="text-lg">Cost Optimization</CardTitle>
          </div>
          <CardDescription>Intelligent model selection for cost efficiency</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {costOptimization.map((item, i) => (
              <motion.div
                key={item.query}
                initial={{ opacity: 0, x: -15 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className="flex flex-col md:flex-row md:items-center gap-3 p-3 rounded-lg bg-muted/20 border border-border/20"
              >
                <div className="flex items-center gap-2 min-w-[140px]">
                  <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
                    {item.icon}
                  </div>
                  <span className="text-sm font-semibold">{item.query}</span>
                </div>
                <ArrowRight className="w-3 h-3 text-muted-foreground hidden md:block" />
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-[10px] bg-teal-500/10 text-teal-400 border-teal-500/20">
                    {item.model}
                  </Badge>
                </div>
                <span className="text-xs text-muted-foreground">{item.reason}</span>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
