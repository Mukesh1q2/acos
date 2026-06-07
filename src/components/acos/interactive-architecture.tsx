"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain,
  Database,
  GitBranch,
  Settings,
  Users,
  ChevronDown,
  Sparkles,
  Network,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

interface LayerData {
  name: string;
  color: string;          // tailwind bg class
  hoverColor: string;     // brighter version for hover
  border: string;         // tailwind border class
  icon: React.ReactNode;
  description: string;
  details: string;
}

const LAYERS: LayerData[] = [
  {
    name: "Cognitive Agent Framework",
    color: "bg-emerald-700",
    hoverColor: "bg-emerald-600",
    border: "border-emerald-500/40",
    icon: <Users className="w-4 h-4" />,
    description: "7 Agent Types orchestrating cognitive tasks",
    details: "7 Agent Types | Reasoning, Coding, Research, Verification, Planning, Creative, Memory",
  },
  {
    name: "Knowledge Fabric",
    color: "bg-emerald-600",
    hoverColor: "bg-emerald-500",
    border: "border-emerald-400/40",
    icon: <Network className="w-4 h-4" />,
    description: "4 Knowledge Sources unified into a coherent fabric",
    details: "4 Knowledge Sources | Knowledge Graph, Vector DB, Symbolic Layer, Citation Tracking",
  },
  {
    name: "Hierarchical Memory",
    color: "bg-teal-600",
    hoverColor: "bg-teal-500",
    border: "border-teal-400/40",
    icon: <Database className="w-4 h-4" />,
    description: "5 Memory Tiers from working to procedural",
    details: "5 Memory Tiers | Working, Episodic, Semantic, Long-Term, Procedural",
  },
  {
    name: "Multi-Thread Reasoning",
    color: "bg-teal-700",
    hoverColor: "bg-teal-600",
    border: "border-teal-400/40",
    icon: <GitBranch className="w-4 h-4" />,
    description: "8 Thread Types with zero interference",
    details: "8 Thread Types | Analytical, Mathematical, Coding, Scientific, Memory, Verification, Planning, Creative",
  },
  {
    name: "AFM (Avadhan Foundation Model)",
    color: "bg-slate-700",
    hoverColor: "bg-slate-600",
    border: "border-slate-400/40",
    icon: <Brain className="w-4 h-4" />,
    description: "Mamba-OTM Hybrid backbone with NSK LoRA",
    details: "Mamba-OTM Hybrid | Mamba backbone + OTM every 4th layer + NSK LoRA adapters",
  },
  {
    name: "Cognitive Kernel (OS Layer)",
    color: "bg-slate-800",
    hoverColor: "bg-slate-700",
    border: "border-slate-500/40",
    icon: <Settings className="w-4 h-4" />,
    description: "3 OS Services managing processes and memory",
    details: "3 OS Services | Process Manager, Memory Manager, Lyapunov Scheduler",
  },
];

/* ------------------------------------------------------------------ */
/*  Particle component – a single dot flowing upward                   */
/* ------------------------------------------------------------------ */

function FlowParticle({ delay, left }: { delay: number; left: string }) {
  return (
    <motion.span
      className="absolute w-1.5 h-1.5 rounded-full bg-emerald-400/70"
      style={{ left }}
      initial={{ bottom: "-4px", opacity: 0 }}
      animate={{
        bottom: ["-4px", "100%"],
        opacity: [0, 1, 1, 0],
      }}
      transition={{
        duration: 2.2,
        delay,
        repeat: Infinity,
        ease: "linear",
      }}
    />
  );
}

/* ------------------------------------------------------------------ */
/*  Connector between layers                                           */
/* ------------------------------------------------------------------ */

function LayerConnector({
  hovered,
  index,
}: {
  hovered: boolean;
  index: number;
}) {
  const positions = ["16%", "35%", "50%", "65%", "84%"];

  return (
    <div className="relative flex items-center justify-center h-6 w-full">
      {/* Vertical line */}
      <motion.div
        className="absolute w-px h-full bg-gradient-to-t from-emerald-500/10 via-emerald-500/30 to-emerald-500/10"
        animate={{ opacity: hovered ? 1 : 0.5 }}
        transition={{ duration: 0.3 }}
      />

      {/* Pulsing dot on the line */}
      <motion.div
        className="absolute w-2 h-2 rounded-full bg-emerald-400"
        animate={{
          scale: hovered ? [1, 1.6, 1] : [1, 1.2, 1],
          opacity: hovered ? [0.5, 1, 0.5] : [0.3, 0.6, 0.3],
        }}
        transition={{
          duration: hovered ? 0.8 : 1.6,
          repeat: Infinity,
          ease: "easeInOut",
          delay: index * 0.15,
        }}
      />

      {/* Flowing particles */}
      {positions.map((left, i) => (
        <FlowParticle
          key={i}
          delay={i * 0.35 + index * 0.2}
          left={left}
        />
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Tooltip that appears on hover                                      */
/* ------------------------------------------------------------------ */

function LayerTooltip({ description }: { description: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -8, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: -8, scale: 0.95 }}
      transition={{ duration: 0.2 }}
      className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-full ml-4 z-30 pointer-events-none"
    >
      <div className="relative px-3 py-2 rounded-lg bg-slate-900 border border-emerald-500/30 shadow-lg shadow-emerald-500/10 text-xs text-emerald-200 max-w-[220px] whitespace-normal">
        {description}
        {/* Arrow */}
        <div className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-full">
          <div className="w-0 h-0 border-t-[6px] border-t-transparent border-b-[6px] border-b-transparent border-r-[6px] border-r-slate-900" />
        </div>
      </div>
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/*  Expand detail panel                                                */
/* ------------------------------------------------------------------ */

function DetailPanel({ details }: { details: string }) {
  return (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: "auto", opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      transition={{ duration: 0.3, ease: "easeInOut" }}
      className="overflow-hidden"
    >
      <div className="flex items-center gap-2 px-4 py-3 bg-slate-900/80 border border-emerald-500/15 rounded-b-lg -mt-1 text-xs text-slate-300 font-mono">
        <Sparkles className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
        {details}
      </div>
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main component                                                     */
/* ------------------------------------------------------------------ */

export function InteractiveArchitecture() {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const toggleExpand = useCallback((idx: number) => {
    setExpandedIdx((prev) => (prev === idx ? null : idx));
  }, []);

  return (
    <div className="w-full max-w-2xl mx-auto select-none">
      {/* 3D perspective wrapper */}
      <div
        className="relative"
        style={{ perspective: "1200px" }}
      >
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7 }}
          style={{
            transformStyle: "preserve-3d",
            transform: "rotateX(8deg)",
          }}
          className="space-y-0"
        >
          {LAYERS.map((layer, i) => {
            const isHovered = hoveredIdx === i;
            const isExpanded = expandedIdx === i;
            const isAdjacentHovered =
              hoveredIdx !== null && Math.abs(hoveredIdx - i) === 1;

            return (
              <div key={layer.name}>
                {/* Layer card */}
                <motion.div
                  layout
                  initial={{ opacity: 0, scaleX: 0.4 }}
                  animate={{ opacity: 1, scaleX: 1 }}
                  transition={{
                    duration: 0.45,
                    delay: 0.3 + i * 0.1,
                    layout: { duration: 0.3 },
                  }}
                  onMouseEnter={() => setHoveredIdx(i)}
                  onMouseLeave={() => setHoveredIdx(null)}
                  onClick={() => toggleExpand(i)}
                  className="relative cursor-pointer group"
                >
                  {/* Main layer bar */}
                  <motion.div
                    animate={{
                      y: isHovered ? -4 : 0,
                      boxShadow: isHovered
                        ? "0 8px 30px rgba(16,185,129,0.25), 0 0 15px rgba(16,185,129,0.1)"
                        : isAdjacentHovered
                          ? "0 2px 10px rgba(16,185,129,0.1)"
                          : "0 1px 3px rgba(0,0,0,0.2)",
                    }}
                    transition={{ duration: 0.25 }}
                    className={`
                      relative flex items-center gap-3 px-4 py-3 rounded-lg
                      ${isHovered ? layer.hoverColor : layer.color}
                      border ${isHovered ? "border-emerald-400/50" : layer.border}
                      text-white text-sm font-medium
                      transition-colors duration-200
                    `}
                  >
                    {/* Icon */}
                    <span
                      className={`flex-shrink-0 transition-transform duration-200 ${
                        isHovered ? "scale-110 text-emerald-200" : "text-white/80"
                      }`}
                    >
                      {layer.icon}
                    </span>

                    {/* Layer name */}
                    <span className="flex-1 truncate">{layer.name}</span>

                    {/* Expand chevron */}
                    <motion.span
                      animate={{ rotate: isExpanded ? 180 : 0 }}
                      transition={{ duration: 0.25 }}
                      className="flex-shrink-0 text-white/50 group-hover:text-white/80 transition-colors"
                    >
                      <ChevronDown className="w-4 h-4" />
                    </motion.span>

                    {/* Glow overlay on hover */}
                    {isHovered && (
                      <motion.div
                        layoutId="layer-glow"
                        className="absolute inset-0 rounded-lg pointer-events-none"
                        style={{
                          background:
                            "linear-gradient(135deg, rgba(16,185,129,0.15) 0%, transparent 60%)",
                        }}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                      />
                    )}

                    {/* Tooltip on hover */}
                    <AnimatePresence>
                      {isHovered && (
                        <LayerTooltip description={layer.description} />
                      )}
                    </AnimatePresence>
                  </motion.div>
                </motion.div>

                {/* Expandable detail panel */}
                <AnimatePresence>
                  {isExpanded && <DetailPanel details={layer.details} />}
                </AnimatePresence>

                {/* Connector to next layer */}
                {i < LAYERS.length - 1 && (
                  <LayerConnector
                    hovered={isHovered || isAdjacentHovered}
                    index={i}
                  />
                )}
              </div>
            );
          })}
        </motion.div>
      </div>

      {/* Subtle decorative label */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.2 }}
        className="text-center text-xs text-muted-foreground mt-6 font-mono"
      >
        Hover to inspect &middot; Click to expand details
      </motion.p>
    </div>
  );
}
