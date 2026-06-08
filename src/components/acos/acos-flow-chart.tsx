"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import {
  Brain,
  Users,
  Network,
  Database,
  GitBranch,
  Cpu,
  Settings,
  ArrowUp,
  ArrowDown,
  Sparkles,
  ChevronDown,
  Eye,
  EyeOff,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface SubComponent {
  name: string;
  desc: string;
}

interface FlowLayer {
  id: string;
  name: string;
  icon: React.ElementType;
  description: string;
  color: string;
  bgClass: string;
  borderClass: string;
  iconClass: string;
  glowColor: string;
  subComponents: SubComponent[];
}

interface FlowConnection {
  from: string;
  to: string;
  direction: "up" | "down" | "bidirectional";
  label: string;
}

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

const LAYERS: FlowLayer[] = [
  {
    id: "cognitive-agent",
    name: "Cognitive Agent Framework",
    icon: Users,
    description: "7 specialized agent types orchestrating cognitive tasks with cooperation model",
    color: "emerald",
    bgClass: "bg-emerald-500/10",
    borderClass: "border-emerald-500/25",
    iconClass: "text-emerald-400",
    glowColor: "rgba(16,185,129,0.25)",
    subComponents: [
      { name: "Reasoning Agent", desc: "Logical deduction and inference" },
      { name: "Coding Agent", desc: "Code generation and debugging" },
      { name: "Research Agent", desc: "Information retrieval and synthesis" },
      { name: "Verification Agent", desc: "Output validation and fact-checking" },
      { name: "Planning Agent", desc: "Task decomposition and scheduling" },
      { name: "Creative Agent", desc: "Generative and divergent thinking" },
      { name: "Memory Agent", desc: "Knowledge consolidation and retrieval" },
    ],
  },
  {
    id: "knowledge-fabric",
    name: "Knowledge Fabric",
    icon: Network,
    description: "Unified knowledge representation across multiple paradigms",
    color: "teal",
    bgClass: "bg-teal-500/10",
    borderClass: "border-teal-500/25",
    iconClass: "text-teal-400",
    glowColor: "rgba(20,184,166,0.25)",
    subComponents: [
      { name: "Knowledge Graph", desc: "Entity-relationship structured knowledge" },
      { name: "Vector DB", desc: "Semantic similarity search" },
      { name: "Symbolic Layer", desc: "Panini constraint integration" },
      { name: "Citation Tracking", desc: "Provenance and source verification" },
    ],
  },
  {
    id: "hierarchical-memory",
    name: "Hierarchical Memory",
    icon: Database,
    description: "5-tier memory system inspired by human cognition",
    color: "green",
    bgClass: "bg-green-500/10",
    borderClass: "border-green-500/25",
    iconClass: "text-green-400",
    glowColor: "rgba(34,197,94,0.25)",
    subComponents: [
      { name: "Working Memory", desc: "8K tokens - Instant access" },
      { name: "Episodic Memory", desc: "100K tokens - Fast recall" },
      { name: "Semantic Memory", desc: "1M+ vectors - Medium speed" },
      { name: "Long-Term Memory", desc: "10M+ vectors - Deep storage" },
      { name: "Procedural Memory", desc: "Unlimited - Compiled skills" },
    ],
  },
  {
    id: "multi-thread",
    name: "Multi-Thread Reasoning",
    icon: GitBranch,
    description: "8 specialized thread types with proven isolation guarantees",
    color: "cyan",
    bgClass: "bg-cyan-500/10",
    borderClass: "border-cyan-500/25",
    iconClass: "text-cyan-400",
    glowColor: "rgba(6,182,212,0.25)",
    subComponents: [
      { name: "Analytical Thread", desc: "Logical analysis and deduction" },
      { name: "Mathematical Thread", desc: "Numerical computation" },
      { name: "Coding Thread", desc: "Program synthesis" },
      { name: "Scientific Thread", desc: "Hypothesis testing" },
      { name: "Memory Thread", desc: "Recall and consolidation" },
      { name: "Verification Thread", desc: "Output validation" },
      { name: "Planning Thread", desc: "Task scheduling" },
      { name: "Creative Thread", desc: "Divergent generation" },
    ],
  },
  {
    id: "afm",
    name: "AFM (Avadhan Foundation Model)",
    icon: Brain,
    description: "Mamba-OTM Hybrid backbone with NSK LoRA adapters",
    color: "emerald",
    bgClass: "bg-emerald-600/10",
    borderClass: "border-emerald-400/25",
    iconClass: "text-emerald-300",
    glowColor: "rgba(16,185,129,0.3)",
    subComponents: [
      { name: "Mamba Backbone", desc: "Selective state space model for efficient sequence processing" },
      { name: "OTM Layers", desc: "Orthogonal Thread Memory every 4th layer" },
      { name: "NSK LoRA Adapters", desc: "Navaratna-Samanvaya-Kendra low-rank adaptation" },
      { name: "HBTA Attention", desc: "Hierarchical Block Token Attention for O(Nd^2*logN) scaling" },
    ],
  },
  {
    id: "cognitive-kernel",
    name: "Cognitive Kernel",
    icon: Cpu,
    description: "Core OS layer managing processes, memory, and scheduling",
    color: "slate",
    bgClass: "bg-slate-500/10",
    borderClass: "border-slate-400/25",
    iconClass: "text-slate-300",
    glowColor: "rgba(148,163,184,0.2)",
    subComponents: [
      { name: "Process Manager", desc: "Thread lifecycle management" },
      { name: "Memory Manager", desc: "Hierarchical memory allocation" },
      { name: "Lyapunov Scheduler", desc: "Stability-guaranteed resource scheduling" },
    ],
  },
];

const CONNECTIONS: FlowConnection[] = [
  { from: "cognitive-agent", to: "knowledge-fabric", direction: "bidirectional", label: "Query / Response" },
  { from: "knowledge-fabric", to: "hierarchical-memory", direction: "bidirectional", label: "Store / Retrieve" },
  { from: "hierarchical-memory", to: "multi-thread", direction: "bidirectional", label: "Context / State" },
  { from: "multi-thread", to: "afm", direction: "down", label: "Compute Requests" },
  { from: "afm", to: "cognitive-kernel", direction: "bidirectional", label: "Schedule / Execute" },
];

/* ------------------------------------------------------------------ */
/*  SVG Flow Particle                                                  */
/* ------------------------------------------------------------------ */

function SvgFlowParticle({
  delay,
  yStart,
  yEnd,
  x,
  color,
}: {
  delay: number;
  yStart: number;
  yEnd: number;
  x: number;
  color: string;
}) {
  return (
    <motion.circle
      cx={x}
      r="2.5"
      fill={color}
      initial={{ cy: yStart, opacity: 0 }}
      animate={{
        cy: [yStart, yEnd],
        opacity: [0, 1, 1, 0],
      }}
      transition={{
        duration: 2.5,
        delay,
        repeat: Infinity,
        ease: "linear",
      }}
    />
  );
}

/* ------------------------------------------------------------------ */
/*  SVG Connection with arrows                                         */
/* ------------------------------------------------------------------ */

function ConnectionLine({
  connection,
  index,
  showParticles,
}: {
  connection: FlowConnection;
  index: number;
  showParticles: boolean;
}) {
  const svgHeight = 48;
  const midX = 50; // percent

  const fromIdx = LAYERS.findIndex((l) => l.id === connection.from);
  const isUpward = connection.direction === "up";
  const isBidirectional = connection.direction === "bidirectional";

  // Color based on layer pair
  const color = fromIdx % 2 === 0 ? "#10b981" : "#14b8a6";
  const fadeColor = fromIdx % 2 === 0 ? "rgba(16,185,129,0.3)" : "rgba(20,184,166,0.3)";

  return (
    <div className="relative w-full h-12 flex items-center justify-center">
      <svg
        width="100%"
        height={svgHeight}
        viewBox={`0 0 100 ${svgHeight}`}
        preserveAspectRatio="none"
        className="absolute inset-0"
      >
        {/* Main line */}
        <motion.line
          x1={midX}
          y1={4}
          x2={midX}
          y2={svgHeight - 4}
          stroke={fadeColor}
          strokeWidth="1.5"
          strokeDasharray={isBidirectional ? "none" : "4 3"}
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.6, delay: 0.3 + index * 0.1 }}
        />

        {/* Down arrow (default) */}
        {(!isUpward || isBidirectional) && (
          <polygon
            points={`${midX - 3},${svgHeight - 10} ${midX + 3},${svgHeight - 10} ${midX},${svgHeight - 4}`}
            fill={fadeColor}
          />
        )}

        {/* Up arrow (for bidirectional or upward) */}
        {(isUpward || isBidirectional) && (
          <polygon
            points={`${midX - 3},10 ${midX + 3},10 ${midX},4`}
            fill={fadeColor}
          />
        )}

        {/* Animated particles moving downward */}
        {showParticles && (!isUpward || isBidirectional) && (
          <>
            <SvgFlowParticle delay={0} yStart={4} yEnd={svgHeight - 4} x={midX - 4} color={color} />
            <SvgFlowParticle delay={0.8} yStart={4} yEnd={svgHeight - 4} x={midX + 4} color={color} />
            <SvgFlowParticle delay={1.6} yStart={4} yEnd={svgHeight - 4} x={midX} color={color} />
          </>
        )}

        {/* Animated particles moving upward */}
        {showParticles && (isUpward || isBidirectional) && (
          <>
            <SvgFlowParticle delay={0.4} yStart={svgHeight - 4} yEnd={4} x={midX - 3} color={color} />
            <SvgFlowParticle delay={1.2} yStart={svgHeight - 4} yEnd={4} x={midX + 3} color={color} />
          </>
        )}

        {/* Connection label */}
        <text
          x={midX + 12}
          y={svgHeight / 2 + 3}
          fill="rgba(148,163,184,0.5)"
          fontSize="5"
          fontFamily="monospace"
        >
          {connection.label}
        </text>
      </svg>

      {/* Direction indicator badges */}
      <div className="absolute left-4 top-1/2 -translate-y-1/2 flex items-center gap-1">
        {(isUpward || isBidirectional) && (
          <ArrowUp className="w-3 h-3 text-emerald-400/60" />
        )}
        {(!isUpward || isBidirectional) && (
          <ArrowDown className="w-3 h-3 text-teal-400/60" />
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Expanded sub-component panel                                       */
/* ------------------------------------------------------------------ */

function ExpandedPanel({ layer }: { layer: FlowLayer }) {
  return (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: "auto", opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="overflow-hidden"
    >
      <div className="mt-2 p-4 rounded-xl bg-card/60 border border-border/20 backdrop-blur-sm">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-xs font-mono text-emerald-400 uppercase tracking-wider">
            Sub-Components ({layer.subComponents.length})
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {layer.subComponents.map((sub, i) => (
            <motion.div
              key={sub.name}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: i * 0.05 }}
              className="p-2.5 rounded-lg bg-muted/20 border border-border/10"
            >
              <div className="text-sm font-medium text-foreground">
                {sub.name}
              </div>
              <div className="text-xs text-muted-foreground mt-0.5">
                {sub.desc}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/*  Layer card                                                         */
/* ------------------------------------------------------------------ */

function LayerCard({
  layer,
  index,
  isHovered,
  isExpanded,
  onHover,
  onLeave,
  onToggle,
}: {
  layer: FlowLayer;
  index: number;
  isHovered: boolean;
  isExpanded: boolean;
  onHover: () => void;
  onLeave: () => void;
  onToggle: () => void;
}) {
  const IconComp = layer.icon;

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: 0.15 + index * 0.1 }}
    >
      <Card
        className={`
          card-hover-lift cursor-pointer transition-all duration-300
          ${layer.borderClass}
          ${isExpanded ? "ring-1 ring-emerald-500/30" : ""}
        `}
        onMouseEnter={onHover}
        onMouseLeave={onLeave}
        onClick={onToggle}
      >
        <CardContent className="p-4 md:p-5">
          <div className="flex items-center gap-3 md:gap-4">
            {/* Icon */}
            <motion.div
              className={`
                w-10 h-10 md:w-12 md:h-12 rounded-xl ${layer.bgClass} ${layer.borderClass}
                border flex items-center justify-center ${layer.iconClass} flex-shrink-0
              `}
              animate={{
                scale: isHovered ? 1.15 : 1,
                boxShadow: isHovered
                  ? `0 0 20px ${layer.glowColor}`
                  : "0 0 0px transparent",
              }}
              transition={{ duration: 0.25 }}
            >
              <IconComp className="w-5 h-5 md:w-6 md:h-6" />
            </motion.div>

            {/* Text content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <motion.h3
                  className="text-sm md:text-base font-semibold text-foreground truncate"
                  animate={{
                    color: isHovered ? "#34d399" : undefined,
                  }}
                  transition={{ duration: 0.2 }}
                >
                  {layer.name}
                </motion.h3>
                <span className="flex-shrink-0 px-1.5 py-0.5 rounded text-[10px] font-mono bg-muted/40 text-muted-foreground border border-border/20">
                  L{index + 1}
                </span>
              </div>
              <p className="text-xs md:text-sm text-muted-foreground mt-0.5 line-clamp-2">
                {layer.description}
              </p>
            </div>

            {/* Expand chevron */}
            <motion.div
              className="flex-shrink-0 text-muted-foreground/50"
              animate={{ rotate: isExpanded ? 180 : 0 }}
              transition={{ duration: 0.25 }}
            >
              <ChevronDown className="w-5 h-5" />
            </motion.div>
          </div>
        </CardContent>

        {/* Hover glow overlay */}
        <AnimatePresence>
          {isHovered && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="absolute inset-0 rounded-xl pointer-events-none"
              style={{
                background: `linear-gradient(135deg, ${layer.glowColor} 0%, transparent 60%)`,
              }}
            />
          )}
        </AnimatePresence>
      </Card>

      {/* Expanded sub-component panel */}
      <AnimatePresence>
        {isExpanded && <ExpandedPanel layer={layer} />}
      </AnimatePresence>
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main component                                                     */
/* ------------------------------------------------------------------ */

export function ACOSFlowChart() {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [showParticles, setShowParticles] = useState(true);

  const toggleExpand = useCallback((id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  }, []);

  return (
    <div className="w-full space-y-0">
      {/* Header with toggle */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Settings className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
            Cognitive Stack Data Flow
          </span>
        </div>
        <button
          onClick={() => setShowParticles((prev) => !prev)}
          className={`
            flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
            transition-all duration-200 border
            ${
              showParticles
                ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-400"
                : "bg-muted/30 border-border/20 text-muted-foreground"
            }
          `}
        >
          {showParticles ? (
            <>
              <Eye className="w-3.5 h-3.5" />
              <span>Data Flow On</span>
            </>
          ) : (
            <>
              <EyeOff className="w-3.5 h-3.5" />
              <span>Data Flow Off</span>
            </>
          )}
        </button>
      </div>

      {/* Stack visualization */}
      <div className="relative space-y-0">
        {LAYERS.map((layer, i) => {
          const isHovered = hoveredId === layer.id;
          const isExpanded = expandedId === layer.id;

          return (
            <div key={layer.id}>
              {/* Layer card */}
              <LayerCard
                layer={layer}
                index={i}
                isHovered={isHovered}
                isExpanded={isExpanded}
                onHover={() => setHoveredId(layer.id)}
                onLeave={() => setHoveredId(null)}
                onToggle={() => toggleExpand(layer.id)}
              />

              {/* Connection to next layer */}
              {i < LAYERS.length - 1 && (
                <ConnectionLine
                  connection={CONNECTIONS[i]}
                  index={i}
                  showParticles={showParticles}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="mt-6 p-3 rounded-lg bg-muted/10 border border-border/10">
        <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <ArrowUp className="w-3 h-3 text-emerald-400" />
            <ArrowDown className="w-3 h-3 text-teal-400" />
            <span>Bidirectional flow</span>
          </div>
          <div className="flex items-center gap-1.5">
            <ArrowDown className="w-3 h-3 text-teal-400" />
            <span>Unidirectional flow</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400/70 animate-pulse" />
            <span>Active data particle</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-mono bg-muted/40 px-1.5 py-0.5 rounded border border-border/20">L1-L6</span>
            <span>Layer index</span>
          </div>
        </div>
      </div>

      {/* Hint text */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5 }}
        className="text-center text-xs text-muted-foreground/50 mt-3 font-mono"
      >
        Hover to highlight &middot; Click to expand sub-components
      </motion.p>
    </div>
  );
}
