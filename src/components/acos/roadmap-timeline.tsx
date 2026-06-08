"use client";

import { motion } from "framer-motion";
import {
  Route,
  CheckCircle,
  Clock,
  Circle,
  Package,
  Zap,
  Brain,
  Cpu,
  Rocket,
  Flame,
  ChevronRight,
} from "lucide-react";

type MilestoneStatus = "completed" | "in-progress" | "upcoming";

interface Milestone {
  month: number;
  title: string;
  bullets: string[];
  deliverable: string;
  status: MilestoneStatus;
  color: string;
  statusLabel: string;
}

interface Phase {
  name: string;
  months: number[];
  color: string;
  icon: React.ReactNode;
}

const milestones: Milestone[] = [
  {
    month: 1,
    title: "HBTA/OTM Layer",
    bullets: [
      "Build HBTA/OTM layer in PyTorch",
      "Validate thread isolation on small scale",
      "Benchmark against FlashAttention",
    ],
    deliverable: "PyTorch module + benchmarks",
    status: "completed",
    color: "emerald",
    statusLabel: "Foundation",
  },
  {
    month: 2,
    title: "Cognitive Kernel",
    bullets: [
      "Wrap Llama-3-8B with Cognitive Kernel",
      "Implement process manager, memory manager",
      "Implement Lyapunov scheduler",
    ],
    deliverable: "Kernel-wrapped Llama-3-8B",
    status: "completed",
    color: "teal",
    statusLabel: "Core",
  },
  {
    month: 3,
    title: "Upload & Learn",
    bullets: [
      "Build Upload & Learn pipeline (RAG + LoRA)",
      "Document ingestion, vector storage",
      "LoRA fine-tuning per user",
    ],
    deliverable: "Document learning pipeline",
    status: "in-progress",
    color: "green",
    statusLabel: "Intelligence",
  },
  {
    month: 4,
    title: "Chat Interface",
    bullets: [
      "React-based chat with thread visualization",
      "Real-time streaming, memory recall",
      "Multi-thread display",
    ],
    deliverable: "Full chat application",
    status: "upcoming",
    color: "cyan",
    statusLabel: "Interface",
  },
  {
    month: 5,
    title: "CUDA Optimization",
    bullets: [
      "CUDA kernel optimization for QR/Cayley transforms",
      "Custom attention kernels for HBTA",
      "Memory optimization for consumer GPUs",
    ],
    deliverable: "Optimized CUDA kernels",
    status: "upcoming",
    color: "emerald",
    statusLabel: "Performance",
  },
  {
    month: 6,
    title: "Beta Launch",
    bullets: [
      '"ACOS for Laptops" local deployment package',
      "Onboarding flow, initial user testing",
      "Polish and stabilization",
    ],
    deliverable: "Public beta release",
    status: "upcoming",
    color: "teal",
    statusLabel: "Launch",
  },
];

const phases: Phase[] = [
  { name: "Foundation", months: [1, 2], color: "emerald", icon: <Zap className="w-4 h-4" /> },
  { name: "Intelligence", months: [3, 4], color: "cyan", icon: <Brain className="w-4 h-4" /> },
  { name: "Launch", months: [5, 6], color: "teal", icon: <Rocket className="w-4 h-4" /> },
];

const colorMap: Record<string, { bg: string; text: string; border: string; glow: string; badge: string; line: string }> = {
  emerald: {
    bg: "bg-emerald-500/10",
    text: "text-emerald-400",
    border: "border-emerald-500/30",
    glow: "shadow-emerald-500/20",
    badge: "bg-emerald-600",
    line: "from-emerald-500",
  },
  teal: {
    bg: "bg-teal-500/10",
    text: "text-teal-400",
    border: "border-teal-500/30",
    glow: "shadow-teal-500/20",
    badge: "bg-teal-600",
    line: "from-teal-500",
  },
  green: {
    bg: "bg-green-500/10",
    text: "text-green-400",
    border: "border-green-500/30",
    glow: "shadow-green-500/20",
    badge: "bg-green-600",
    line: "from-green-500",
  },
  cyan: {
    bg: "bg-cyan-500/10",
    text: "text-cyan-400",
    border: "border-cyan-500/30",
    glow: "shadow-cyan-500/20",
    badge: "bg-cyan-600",
    line: "from-cyan-500",
  },
};

function StatusIcon({ status, color }: { status: MilestoneStatus; color: string }) {
  const colors = colorMap[color] || colorMap.emerald;
  switch (status) {
    case "completed":
      return (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
          className={`${colors.text}`}
        >
          <CheckCircle className="w-6 h-6" />
        </motion.div>
      );
    case "in-progress":
      return (
        <motion.div
          animate={{ scale: [1, 1.2, 1] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          className="relative"
        >
          <div className={`w-6 h-6 rounded-full ${colors.badge} flex items-center justify-center`}>
            <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
          </div>
          <div className={`absolute inset-0 rounded-full ${colors.badge} animate-ping opacity-30`} />
        </motion.div>
      );
    case "upcoming":
      return <Circle className={`w-6 h-6 ${color === "emerald" ? "text-emerald-700" : color === "teal" ? "text-teal-700" : color === "cyan" ? "text-cyan-700" : "text-green-700"}`} />;
  }
}

function PhaseBadge({ phase }: { phase: Phase }) {
  const phaseColor = colorMap[phase.color] || colorMap.emerald;
  return (
    <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${phaseColor.bg} ${phaseColor.text} border ${phaseColor.border}`}>
      {phase.icon}
      <span>{phase.name}</span>
    </div>
  );
}

function FlowingConnector({ isActive, color, isVertical }: { isActive: boolean; color: string; isVertical: boolean }) {
  const colors = colorMap[color] || colorMap.emerald;

  if (isVertical) {
    return (
      <div className="flex flex-col items-center py-2 h-16 w-full">
        <div className="relative w-0.5 h-full bg-muted/30 overflow-hidden">
          <motion.div
            className={`absolute top-0 left-0 w-full bg-gradient-to-b ${colors.line} to-transparent`}
            initial={{ height: 0 }}
            animate={{ height: "100%" }}
            transition={{ duration: 1.5, ease: "easeOut" }}
          />
          {isActive && (
            <motion.div
              className={`absolute left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full ${colors.badge}`}
              animate={{ top: ["0%", "100%"] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
            />
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center h-full w-12 md:w-16 flex-shrink-0">
      <div className="relative w-full h-0.5 bg-muted/30 overflow-hidden">
        <motion.div
          className={`absolute top-0 left-0 h-full bg-gradient-to-r ${colors.line} to-transparent`}
          initial={{ width: 0 }}
          animate={{ width: "100%" }}
          transition={{ duration: 1.5, ease: "easeOut" }}
        />
        {isActive && (
          <motion.div
            className={`absolute top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full ${colors.badge}`}
            animate={{ left: ["0%", "100%"] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
          />
        )}
      </div>
      <ChevronRight className="w-3 h-3 text-muted-foreground/50 -ml-1 flex-shrink-0" />
    </div>
  );
}

function MilestoneCard({ milestone, index, isLast, isVertical }: { milestone: Milestone; index: number; isLast: boolean; isVertical: boolean }) {
  const colors = colorMap[milestone.color] || colorMap.emerald;
  const isCompleted = milestone.status === "completed";
  const isInProgress = milestone.status === "in-progress";

  return (
    <motion.div
      initial={{ opacity: 0, y: isVertical ? 20 : 30, x: isVertical ? 0 : -20 }}
      animate={{ opacity: 1, y: 0, x: 0 }}
      transition={{ duration: 0.5, delay: index * 0.15, ease: "easeOut" }}
      className="flex-shrink-0"
    >
      <div className="flex flex-col items-center">
        {/* Month badge + status */}
        <div className="flex items-center gap-2 mb-3">
          <motion.div
            className={`w-12 h-12 rounded-full ${colors.badge} flex items-center justify-center text-white font-bold text-lg shadow-lg ${isCompleted ? colors.glow : ""} ${isCompleted ? "shadow-lg" : ""}`}
            animate={isCompleted ? { boxShadow: [`0 0 0px ${colors.glow.replace("shadow-", "").replace("/20", "/0")}`, `0 0 15px rgba(16,185,129,0.3)`, `0 0 0px ${colors.glow.replace("shadow-", "").replace("/20", "/0")}`] } : {}}
            transition={isCompleted ? { duration: 3, repeat: Infinity, ease: "easeInOut" } : {}}
          >
            {milestone.month}
          </motion.div>
          <StatusIcon status={milestone.status} color={milestone.color} />
        </div>

        {/* Card */}
        <motion.div
          className={`
            relative w-64 md:w-72 rounded-xl border ${colors.border} ${colors.bg} p-5
            transition-all duration-300
            ${isCompleted ? `shadow-md ${colors.glow}` : ""}
            ${isInProgress ? "ring-1 ring-cyan-400/50" : ""}
          `}
          whileHover={{ y: -4, transition: { duration: 0.2 } }}
        >
          {/* Status tag */}
          <div className="flex items-center justify-between mb-3">
            <span className={`text-xs font-semibold uppercase tracking-wider ${colors.text}`}>
              {milestone.statusLabel}
            </span>
            {isInProgress && (
              <span className="text-[10px] font-mono text-cyan-400 bg-cyan-400/10 px-2 py-0.5 rounded-full border border-cyan-400/30">
                IN PROGRESS
              </span>
            )}
            {isCompleted && (
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-full border border-emerald-400/30">
                COMPLETED
              </span>
            )}
          </div>

          {/* Title */}
          <h3 className="text-base font-bold text-foreground mb-3">
            {milestone.title}
          </h3>

          {/* Bullets */}
          <ul className="space-y-1.5 mb-4">
            {milestone.bullets.map((bullet, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                <span className={`mt-1.5 w-1 h-1 rounded-full flex-shrink-0 ${colors.text} bg-current`} />
                <span>{bullet}</span>
              </li>
            ))}
          </ul>

          {/* Deliverable badge */}
          <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${colors.border} bg-background/50`}>
            <Package className={`w-3.5 h-3.5 flex-shrink-0 ${colors.text}`} />
            <span className="text-xs text-foreground font-medium">{milestone.deliverable}</span>
          </div>

          {/* Subtle glow overlay for completed */}
          {isCompleted && (
            <div className={`absolute inset-0 rounded-xl bg-gradient-to-b from-emerald-500/5 to-transparent pointer-events-none`} />
          )}
        </motion.div>
      </div>
    </motion.div>
  );
}

function ProgressBar() {
  const completedMonths = milestones.filter((m) => m.status === "completed").length;
  const totalMonths = milestones.length;
  const inProgressMonths = milestones.filter((m) => m.status === "in-progress").length;
  const progressPercent = ((completedMonths + inProgressMonths * 0.5) / totalMonths) * 100;

  return (
    <div className="mb-8 md:mb-10">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Route className="w-4 h-4 text-emerald-400" />
          <span className="text-sm font-semibold text-foreground">6-Month MVP Roadmap</span>
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <CheckCircle className="w-3 h-3 text-emerald-400" />
            {completedMonths} completed
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3 text-cyan-400" />
            {inProgressMonths} in progress
          </span>
          <span className="flex items-center gap-1">
            <Circle className="w-3 h-3 text-muted-foreground/50" />
            {totalMonths - completedMonths - inProgressMonths} upcoming
          </span>
        </div>
      </div>
      <div className="relative h-2 bg-muted/30 rounded-full overflow-hidden">
        <motion.div
          className="absolute top-0 left-0 h-full rounded-full bg-gradient-to-r from-emerald-500 via-teal-400 to-cyan-400"
          initial={{ width: 0 }}
          animate={{ width: `${progressPercent}%` }}
          transition={{ duration: 1.2, ease: "easeOut", delay: 0.3 }}
        />
        {/* Animated shimmer */}
        <motion.div
          className="absolute top-0 left-0 h-full w-8 bg-gradient-to-r from-transparent via-white/20 to-transparent"
          animate={{ x: ["-100%", "800%"] }}
          transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut", delay: 1.5 }}
        />
      </div>
      <div className="mt-1.5 flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          {completedMonths}/{totalMonths} months completed ({Math.round(progressPercent)}%)
        </span>
        <span className="text-xs font-mono text-muted-foreground">
          Month {completedMonths + 1} of {totalMonths}
        </span>
      </div>
    </div>
  );
}

function PhaseGroupings() {
  return (
    <div className="mb-8 md:mb-10">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
        Development Phases
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {phases.map((phase, i) => {
          const phaseMilestones = milestones.filter((m) => phase.months.includes(m.month));
          const allCompleted = phaseMilestones.every((m) => m.status === "completed");
          const hasInProgress = phaseMilestones.some((m) => m.status === "in-progress");
          const colors = colorMap[phase.color] || colorMap.emerald;

          return (
            <motion.div
              key={phase.name}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: i * 0.1 + 0.2 }}
              className={`
                relative rounded-xl border p-4 transition-all duration-300
                ${allCompleted ? `${colors.border} ${colors.bg}` : "border-border/30 bg-muted/10"}
                ${hasInProgress ? "ring-1 ring-cyan-400/30" : ""}
              `}
            >
              <div className="flex items-center gap-2 mb-2">
                <PhaseBadge phase={phase} />
                {allCompleted && <CheckCircle className="w-4 h-4 text-emerald-400" />}
                {hasInProgress && (
                  <span className="text-[10px] font-mono text-cyan-400 animate-pulse">ACTIVE</span>
                )}
              </div>
              <div className="flex items-center gap-2 mt-2">
                {phaseMilestones.map((m) => (
                  <div key={m.month} className="flex items-center gap-1">
                    <div className={`w-6 h-6 rounded-full text-xs font-bold flex items-center justify-center ${
                      m.status === "completed"
                        ? `${colorMap[m.color]?.badge || "bg-emerald-600"} text-white`
                        : m.status === "in-progress"
                        ? "bg-cyan-600 text-white animate-pulse"
                        : "bg-muted/50 text-muted-foreground"
                    }`}>
                      {m.month}
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

export function RoadmapTimeline() {
  return (
    <div className="py-2">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="mb-8"
      >
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-600 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Route className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground tracking-tight">
              Roadmap Timeline
            </h1>
            <p className="text-sm text-muted-foreground">
              ACOS 6-month MVP development journey
            </p>
          </div>
        </div>
      </motion.div>

      {/* Progress Bar */}
      <ProgressBar />

      {/* Phase Groupings */}
      <PhaseGroupings />

      {/* Timeline Section Title */}
      <motion.h3
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4"
      >
        Milestone Timeline
      </motion.h3>

      {/* Mobile: Vertical Timeline */}
      <div className="block md:hidden">
        <div className="relative">
          {/* Vertical line backbone */}
          <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gradient-to-b from-emerald-500/50 via-teal-500/30 to-muted/20" />

          <div className="space-y-0">
            {milestones.map((milestone, index) => {
              const colors = colorMap[milestone.color] || colorMap.emerald;
              const isCompleted = milestone.status === "completed";
              const isInProgress = milestone.status === "in-progress";

              return (
                <motion.div
                  key={milestone.month}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.5, delay: index * 0.12 }}
                  className="relative pl-16 pb-6"
                >
                  {/* Month badge on the line */}
                  <div className="absolute left-0 top-0">
                    <motion.div
                      className={`w-12 h-12 rounded-full ${colors.badge} flex items-center justify-center text-white font-bold text-lg shadow-lg z-10 relative ${isCompleted ? colors.glow : ""}`}
                      animate={isCompleted ? {
                        boxShadow: [
                          "0 0 0px rgba(16,185,129,0)",
                          "0 0 12px rgba(16,185,129,0.3)",
                          "0 0 0px rgba(16,185,129,0)",
                        ],
                      } : {}}
                      transition={isCompleted ? { duration: 3, repeat: Infinity } : {}}
                    >
                      {milestone.month}
                    </motion.div>
                    {/* Status indicator next to badge */}
                    <div className="absolute -right-1 -bottom-1">
                      <StatusIcon status={milestone.status} color={milestone.color} />
                    </div>
                  </div>

                  {/* Card */}
                  <motion.div
                    className={`
                      rounded-xl border ${colors.border} ${colors.bg} p-4
                      transition-all duration-300
                      ${isCompleted ? `shadow-md ${colors.glow}` : ""}
                      ${isInProgress ? "ring-1 ring-cyan-400/50" : ""}
                    `}
                    whileHover={{ y: -2, transition: { duration: 0.2 } }}
                  >
                    {/* Status tag */}
                    <div className="flex items-center justify-between mb-2">
                      <span className={`text-xs font-semibold uppercase tracking-wider ${colors.text}`}>
                        {milestone.statusLabel}
                      </span>
                      {isInProgress && (
                        <span className="text-[10px] font-mono text-cyan-400 bg-cyan-400/10 px-2 py-0.5 rounded-full border border-cyan-400/30">
                          IN PROGRESS
                        </span>
                      )}
                      {isCompleted && (
                        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-full border border-emerald-400/30">
                          COMPLETED
                        </span>
                      )}
                    </div>

                    <h3 className="text-base font-bold text-foreground mb-2">
                      {milestone.title}
                    </h3>

                    <ul className="space-y-1.5 mb-3">
                      {milestone.bullets.map((bullet, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                          <span className={`mt-1.5 w-1 h-1 rounded-full flex-shrink-0 ${colors.text} bg-current`} />
                          <span>{bullet}</span>
                        </li>
                      ))}
                    </ul>

                    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border ${colors.border} bg-background/50`}>
                      <Package className={`w-3.5 h-3.5 flex-shrink-0 ${colors.text}`} />
                      <span className="text-xs text-foreground font-medium">{milestone.deliverable}</span>
                    </div>
                  </motion.div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Desktop: Horizontal Timeline */}
      <div className="hidden md:block">
        <div className="overflow-x-auto pb-4 -mx-2 px-2 scrollbar-thin">
          <div className="flex items-start gap-0 min-w-max">
            {milestones.map((milestone, index) => {
              const isLast = index === milestones.length - 1;
              const connectorColor = index < milestones.length - 1 ? milestones[index + 1].color : milestone.color;
              const isActive = milestone.status === "completed" || milestone.status === "in-progress";

              return (
                <div key={milestone.month} className="flex items-start">
                  <MilestoneCard
                    milestone={milestone}
                    index={index}
                    isLast={isLast}
                    isVertical={false}
                  />
                  {!isLast && (
                    <div className="flex items-center pt-8">
                      <FlowingConnector
                        isActive={isActive}
                        color={connectorColor}
                        isVertical={false}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Legend */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.2 }}
        className="mt-8 p-4 rounded-xl border border-border/30 bg-muted/10"
      >
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
          Legend
        </h4>
        <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-400" />
            Completed milestone
          </span>
          <span className="flex items-center gap-2">
            <div className="relative w-4 h-4">
              <div className="w-4 h-4 rounded-full bg-cyan-600 flex items-center justify-center">
                <div className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
              </div>
            </div>
            In progress
          </span>
          <span className="flex items-center gap-2">
            <Circle className="w-4 h-4 text-muted-foreground/50" />
            Upcoming
          </span>
          <span className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-emerald-600 shadow-md shadow-emerald-500/20" />
            Animated glow = completed
          </span>
          <span className="flex items-center gap-2">
            <Package className="w-4 h-4 text-muted-foreground" />
            Deliverable
          </span>
        </div>
      </motion.div>

      {/* Key insight */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 1.4 }}
        className="mt-6 p-5 rounded-xl border border-emerald-500/20 bg-emerald-500/5"
      >
        <div className="flex items-start gap-3">
          <Flame className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-1">
              Critical Path
            </h4>
            <p className="text-sm text-muted-foreground leading-relaxed">
              The HBTA/OTM layer (Month 1) is the foundational bottleneck. All subsequent milestones
              depend on its correctness. The Cognitive Kernel (Month 2) extends this into a
              production-ready architecture. Upload &amp; Learn (Month 3, currently in progress) is the
              inflection point where ACOS transitions from infrastructure to intelligence.
            </p>
          </div>
        </div>
      </motion.div>

      {/* Technical dependencies */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 1.6 }}
        className="mt-4 p-5 rounded-xl border border-teal-500/20 bg-teal-500/5"
      >
        <div className="flex items-start gap-3">
          <Cpu className="w-5 h-5 text-teal-400 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-1">
              Technical Dependencies
            </h4>
            <div className="space-y-1.5 text-sm text-muted-foreground">
              <p>
                <span className="text-emerald-400 font-medium">Month 1 &rarr; Month 5:</span> HBTA implementation
                correctness determines CUDA optimization feasibility. Kernel design choices in Month 1
                constrain the QR/Cayley transform approach in Month 5.
              </p>
              <p>
                <span className="text-teal-400 font-medium">Month 2 &rarr; Month 4:</span> The Cognitive Kernel&apos;s
                process and memory managers define the API surface for the Chat Interface. Thread
                visualization in Month 4 requires OTM state from Month 2.
              </p>
              <p>
                <span className="text-cyan-400 font-medium">Month 3 &rarr; Month 6:</span> The Upload &amp; Learn pipeline
                provides the personalization engine for the Beta Launch. User onboarding in Month 6
                depends on LoRA fine-tuning stability from Month 3.
              </p>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
