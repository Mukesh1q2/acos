"use client";

import { useState, useCallback, useMemo, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Play,
  FastForward,
  Pause,
  Info,
  Radio,
  GitBranch,
} from "lucide-react";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";

// ─── Types ───────────────────────────────────────────────────────────────────

type NodeId =
  | "root"
  | "upper-l"
  | "upper-r"
  | "mid-ll"
  | "mid-lr"
  | "mid-rl"
  | "mid-rr"
  | "t1"
  | "t2"
  | "t3"
  | "t4"
  | "t5"
  | "t6"
  | "t7"
  | "t8";

type NodeLevel = "root" | "upper" | "mid" | "leaf";

interface TreeNode {
  id: NodeId;
  label: string;
  level: NodeLevel;
  x: number;
  y: number;
  parent: NodeId | null;
  children: NodeId[];
}

type SpeedPreset = "slow" | "medium" | "fast";

interface ParticleState {
  id: number;
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  color: string;
}

// ─── Tree Data ───────────────────────────────────────────────────────────────

const NODES: TreeNode[] = [
  // Root
  { id: "root", label: "Global Context", level: "root", x: 400, y: 55, parent: null, children: ["upper-l", "upper-r"] },
  // Upper level
  { id: "upper-l", label: "Agg L", level: "upper", x: 200, y: 150, parent: "root", children: ["mid-ll", "mid-lr"] },
  { id: "upper-r", label: "Agg R", level: "upper", x: 600, y: 150, parent: "root", children: ["mid-rl", "mid-rr"] },
  // Mid level
  { id: "mid-ll", label: "Gated Sum", level: "mid", x: 100, y: 265, parent: "upper-l", children: ["t1", "t2"] },
  { id: "mid-lr", label: "Gated Sum", level: "mid", x: 300, y: 265, parent: "upper-l", children: ["t3", "t4"] },
  { id: "mid-rl", label: "Gated Sum", level: "mid", x: 500, y: 265, parent: "upper-r", children: ["t5", "t6"] },
  { id: "mid-rr", label: "Gated Sum", level: "mid", x: 700, y: 265, parent: "upper-r", children: ["t7", "t8"] },
  // Leaf level
  { id: "t1", label: "t1", level: "leaf", x: 50, y: 390, parent: "mid-ll", children: [] },
  { id: "t2", label: "t2", level: "leaf", x: 150, y: 390, parent: "mid-ll", children: [] },
  { id: "t3", label: "t3", level: "leaf", x: 250, y: 390, parent: "mid-lr", children: [] },
  { id: "t4", label: "t4", level: "leaf", x: 350, y: 390, parent: "mid-lr", children: [] },
  { id: "t5", label: "t5", level: "leaf", x: 450, y: 390, parent: "mid-rl", children: [] },
  { id: "t6", label: "t6", level: "leaf", x: 550, y: 390, parent: "mid-rl", children: [] },
  { id: "t7", label: "t7", level: "leaf", x: 650, y: 390, parent: "mid-rr", children: [] },
  { id: "t8", label: "t8", level: "leaf", x: 750, y: 390, parent: "mid-rr", children: [] },
];

const nodeMap = new Map<NodeId, TreeNode>(NODES.map((n) => [n.id, n]));

// ─── Helper Functions ────────────────────────────────────────────────────────

function getPathToRoot(nodeId: NodeId): NodeId[] {
  const path: NodeId[] = [];
  let current: NodeId | null = nodeId;
  while (current) {
    path.push(current);
    const node = nodeMap.get(current);
    current = node?.parent ?? null;
  }
  return path;
}

function getPathFromRoot(nodeId: NodeId): NodeId[] {
  return getPathToRoot(nodeId).reverse();
}

function getLevelColor(level: NodeLevel): string {
  switch (level) {
    case "root": return "#10b981";    // emerald-500
    case "upper": return "#22d3ee";   // cyan-400
    case "mid": return "#2dd4bf";     // teal-400
    case "leaf": return "#34d399";    // emerald-400
  }
}

function getLevelBgClass(level: NodeLevel): string {
  switch (level) {
    case "root": return "fill-emerald-500";
    case "upper": return "fill-cyan-400";
    case "mid": return "fill-teal-400";
    case "leaf": return "fill-emerald-400";
  }
}

function getPathLength(nodeId: NodeId): number {
  return getPathToRoot(nodeId).length - 1;
}

function getSpeedMs(speed: SpeedPreset): number {
  switch (speed) {
    case "slow": return 1200;
    case "medium": return 700;
    case "fast": return 350;
  }
}

const LEAF_IDS: NodeId[] = NODES.filter((n) => n.level === "leaf").map((n) => n.id);

// ─── Edges ───────────────────────────────────────────────────────────────────

const EDGES: { from: NodeId; to: NodeId }[] = [];
NODES.forEach((node) => {
  node.children.forEach((childId) => {
    EDGES.push({ from: node.id, to: childId });
  });
});

// ─── Sub-components ──────────────────────────────────────────────────────────

function TreeEdge({
  from,
  to,
  highlighted,
  direction,
}: {
  from: TreeNode;
  to: TreeNode;
  highlighted: boolean;
  direction: "up" | "down" | "none";
}) {
  const midY = (from.y + to.y) / 2;
  const path = `M ${from.x} ${from.y} C ${from.x} ${midY}, ${to.x} ${midY}, ${to.x} ${to.y}`;

  return (
    <g>
      {/* Base edge */}
      <motion.path
        d={path}
        fill="none"
        stroke={highlighted ? getLevelColor(from.level) : "oklch(1 0 0 / 8%)"}
        strokeWidth={highlighted ? 2.5 : 1}
        strokeLinecap="round"
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.02 }}
      />
      {/* Highlighted glow */}
      {highlighted && (
        <motion.path
          d={path}
          fill="none"
          stroke={getLevelColor(from.level)}
          strokeWidth={6}
          strokeLinecap="round"
          opacity={0.15}
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.6 }}
          style={{ filter: "blur(4px)" }}
        />
      )}
      {/* Direction arrow indicator */}
      {direction !== "none" && highlighted && (
        <motion.circle
          r={3}
          fill={direction === "up" ? "#fbbf24" : "#34d399"}
          initial={{ opacity: 0, cx: direction === "up" ? from.x : to.x, cy: direction === "up" ? from.y : to.y }}
          animate={{
            cx: direction === "up" ? [from.x, to.x] : [to.x, from.x],
            cy: direction === "up" ? [from.y, to.y] : [to.y, from.y],
            opacity: [0, 1, 1, 0],
          }}
          transition={{
            cx: { duration: 1.5, repeat: Infinity, ease: "easeInOut" },
            cy: { duration: 1.5, repeat: Infinity, ease: "easeInOut" },
            opacity: { duration: 1.5, repeat: Infinity },
          }}
        />
      )}
    </g>
  );
}

function TreeNodeCircle({
  node,
  isSelected,
  isOnPath,
  onClick,
  animationDelay,
}: {
  node: TreeNode;
  isSelected: boolean;
  isOnPath: boolean;
  onClick: (id: NodeId) => void;
  animationDelay: number;
}) {
  const radius = node.level === "root" ? 28 : node.level === "upper" ? 22 : node.level === "mid" ? 18 : 14;
  const color = getLevelColor(node.level);
  const isLeaf = node.level === "leaf";

  const tooltipText = useMemo(() => {
    const pathLen = getPathLength(node.id);
    if (node.level === "root") return "Root: Global context vector. Receives aggregated info from all leaves.";
    if (node.level === "leaf") return `Leaf ${node.label}: Path to root = O(logN) = ${pathLen} hops`;
    return `${node.label}: Aggregates children via gated-sum. Path to root = ${pathLen} hops`;
  }, [node]);

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <g
          className="cursor-pointer"
          onClick={() => onClick(node.id)}
          role="button"
          aria-label={`Select ${node.label}`}
        >
          {/* Pulse glow for root */}
          {node.level === "root" && (
            <motion.circle
              cx={node.x}
              cy={node.y}
              r={radius + 8}
              fill="none"
              stroke="#10b981"
              strokeWidth={2}
              animate={{
                r: [radius + 6, radius + 14, radius + 6],
                opacity: [0.4, 0.1, 0.4],
              }}
              transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
            />
          )}

          {/* Selection ring */}
          {isSelected && (
            <motion.circle
              cx={node.x}
              cy={node.y}
              r={radius + 5}
              fill="none"
              stroke="#fbbf24"
              strokeWidth={2}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: "spring", stiffness: 300, damping: 20 }}
            />
          )}

          {/* Path highlight ring */}
          {isOnPath && !isSelected && (
            <motion.circle
              cx={node.x}
              cy={node.y}
              r={radius + 4}
              fill="none"
              stroke={color}
              strokeWidth={1.5}
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.6 }}
              transition={{ duration: 0.3 }}
            />
          )}

          {/* Node body */}
          <motion.circle
            cx={node.x}
            cy={node.y}
            r={radius}
            className={getLevelBgClass(node.level)}
            initial={{ scale: 0, opacity: 0 }}
            animate={{
              scale: 1,
              opacity: isSelected ? 1 : isOnPath ? 0.9 : 0.7,
            }}
            transition={{
              type: "spring",
              stiffness: 260,
              damping: 20,
              delay: animationDelay,
            }}
            style={{ filter: isOnPath || isSelected ? `drop-shadow(0 0 6px ${color})` : "none" }}
          />

          {/* Dark inner circle for contrast */}
          <motion.circle
            cx={node.x}
            cy={node.y}
            r={radius - 3}
            fill="oklch(0.13 0 0)"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{
              type: "spring",
              stiffness: 260,
              damping: 20,
              delay: animationDelay + 0.05,
            }}
          />

          {/* Label */}
          <motion.text
            x={node.x}
            y={node.y + 1}
            textAnchor="middle"
            dominantBaseline="middle"
            fill={color}
            fontSize={isLeaf ? 10 : node.level === "root" ? 9 : 8}
            fontWeight={node.level === "root" ? 700 : 600}
            fontFamily="monospace"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: animationDelay + 0.15 }}
          >
            {node.label}
          </motion.text>
        </g>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        className="bg-slate-800 text-slate-100 border-slate-700 text-xs max-w-[220px]"
      >
        <div className="flex items-start gap-1.5">
          <Info className="w-3 h-3 text-emerald-400 flex-shrink-0 mt-0.5" />
          <span>{tooltipText}</span>
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

function TravelingParticle({
  fromX,
  fromY,
  toX,
  toY,
  color,
  duration,
  delay,
  onComplete,
}: {
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  color: string;
  duration: number;
  delay: number;
  onComplete?: () => void;
}) {
  return (
    <motion.circle
      r={5}
      fill={color}
      initial={{ cx: fromX, cy: fromY, opacity: 0 }}
      animate={{
        cx: [fromX, toX],
        cy: [fromY, toY],
        opacity: [0, 1, 1, 0],
      }}
      transition={{
        duration,
        delay,
        ease: "easeInOut",
      }}
      onAnimationComplete={onComplete}
      style={{ filter: `drop-shadow(0 0 8px ${color})` }}
    />
  );
}

// ─── Comparison Panel ────────────────────────────────────────────────────────

function ComparisonPanel() {
  // Create all-to-all connections for standard attention
  const standardEdges = useMemo(() => {
    const edges: { x1: number; y1: number; x2: number; y2: number }[] = [];
    for (let i = 0; i < LEAF_IDS.length; i++) {
      for (let j = i + 1; j < LEAF_IDS.length; j++) {
        const a = nodeMap.get(LEAF_IDS[i]);
        const b = nodeMap.get(LEAF_IDS[j]);
        if (a && b) {
          edges.push({ x1: a.x, y1: a.y, x2: b.x, y2: b.y });
        }
      }
    }
    return edges;
  }, []);

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
      {/* Standard Attention */}
      <div className="rounded-lg border border-slate-700/50 bg-slate-900/50 p-3">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-2 h-2 rounded-full bg-slate-400" />
          <span className="text-xs font-semibold text-slate-300">Standard Attention</span>
        </div>
        <div className="text-[10px] text-slate-500 mb-2 font-mono">
          O(N^2 * d) — All-to-all connections
        </div>
        <svg viewBox="0 0 800 100" className="w-full h-16">
          {LEAF_IDS.map((id, i) => {
            const node = nodeMap.get(id);
            if (!node) return null;
            const x = 50 + i * 100;
            return (
              <g key={id}>
                <circle cx={x} cy={50} r={6} fill="oklch(0.7 0 0 / 30%)" />
                <text x={x} y={72} textAnchor="middle" fill="oklch(0.5 0 0)" fontSize={7} fontFamily="monospace">{id}</text>
              </g>
            );
          })}
          {/* Mesh of all-to-all lines */}
          {standardEdges.map((edge, i) => {
            const aIdx = LEAF_IDS.findIndex((id) => nodeMap.get(id)?.x === edge.x1);
            const bIdx = LEAF_IDS.findIndex((id) => nodeMap.get(id)?.x === edge.x2);
            const x1 = 50 + aIdx * 100;
            const x2 = 50 + bIdx * 100;
            return (
              <line
                key={`se-${i}`}
                x1={x1}
                y1={50}
                x2={x2}
                y2={50}
                stroke="oklch(0.6 0 0 / 12%)"
                strokeWidth={0.5}
              />
            );
          })}
        </svg>
        <div className="text-[10px] text-red-400/70 font-mono mt-1">
          28 connections for 8 tokens
        </div>
      </div>

      {/* HBTA */}
      <div className="rounded-lg border border-emerald-700/50 bg-emerald-900/20 p-3">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-2 h-2 rounded-full bg-emerald-400" />
          <span className="text-xs font-semibold text-emerald-300">HBTA (ACOS)</span>
        </div>
        <div className="text-[10px] text-emerald-500 mb-2 font-mono">
          O(N * d^2 * logN) — Tree structure
        </div>
        <svg viewBox="0 0 800 100" className="w-full h-16">
          {/* Simplified tree representation */}
          {LEAF_IDS.map((id, i) => {
            const x = 50 + i * 100;
            return (
              <g key={id}>
                <circle cx={x} cy={70} r={6} fill="#34d399" opacity={0.6} />
                <text x={x} y={92} textAnchor="middle" fill="#34d399" fontSize={7} fontFamily="monospace">{id}</text>
              </g>
            );
          })}
          {/* Mid-level nodes */}
          {[
            { x: 100, label: "M1" },
            { x: 300, label: "M2" },
            { x: 500, label: "M3" },
            { x: 700, label: "M4" },
          ].map((n) => (
            <g key={n.label}>
              <circle cx={n.x} cy={40} r={5} fill="#2dd4bf" opacity={0.6} />
              {/* Lines to children */}
              <line x1={n.x} y1={40} x2={n.x - 50} y2={70} stroke="#2dd4bf" strokeWidth={0.8} opacity={0.4} />
              <line x1={n.x} y1={40} x2={n.x + 50} y2={70} stroke="#2dd4bf" strokeWidth={0.8} opacity={0.4} />
            </g>
          ))}
          {/* Root */}
          <circle cx={400} cy={10} r={6} fill="#10b981" opacity={0.8} />
          <line x1={400} y1={10} x2={200} y2={40} stroke="#22d3ee" strokeWidth={0.8} opacity={0.4} />
          <line x1={400} y1={10} x2={600} y2={40} stroke="#22d3ee" strokeWidth={0.8} opacity={0.4} />
          {/* Upper nodes */}
          <circle cx={200} cy={40} r={5} fill="#22d3ee" opacity={0.6} />
          <circle cx={600} cy={40} r={5} fill="#22d3ee" opacity={0.6} />
        </svg>
        <div className="text-[10px] text-emerald-400/70 font-mono mt-1">
          14 connections for 8 tokens (logN path)
        </div>
      </div>
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

export function HBTATreeViz() {
  const [selectedLeaf, setSelectedLeaf] = useState<NodeId | null>(null);
  const [animating, setAnimating] = useState(false);
  const [animationType, setAnimationType] = useState<"query" | "broadcast" | null>(null);
  const [speed, setSpeed] = useState<SpeedPreset>("medium");
  const [particles, setParticles] = useState<ParticleState[]>([]);
  const [particleId, setParticleId] = useState(0);

  // Compute highlighted path
  const highlightedPath = useMemo(() => {
    if (!selectedLeaf) return new Set<NodeId>();
    return new Set(getPathToRoot(selectedLeaf));
  }, [selectedLeaf]);

  // Compute highlighted edges
  const highlightedEdges = useMemo(() => {
    if (!selectedLeaf) return new Set<string>();
    const path = getPathToRoot(selectedLeaf);
    const edgeSet = new Set<string>();
    for (let i = 0; i < path.length - 1; i++) {
      edgeSet.add(`${path[i + 1]}-${path[i]}`);
    }
    return edgeSet;
  }, [selectedLeaf]);

  const handleNodeClick = useCallback((nodeId: NodeId) => {
    const node = nodeMap.get(nodeId);
    if (node?.level === "leaf") {
      setSelectedLeaf((prev) => (prev === nodeId ? null : nodeId));
    }
  }, []);

  // Animate Query: particle travels from a random leaf to root
  const animateQuery = useCallback(() => {
    if (animating) return;
    const randomLeaf = LEAF_IDS[Math.floor(Math.random() * LEAF_IDS.length)];
    setSelectedLeaf(randomLeaf);
    setAnimationType("query");
    setAnimating(true);

    const path = getPathToRoot(randomLeaf);
    const duration = getSpeedMs(speed) / 1000;
    const newParticles: ParticleState[] = [];

    for (let i = 0; i < path.length - 1; i++) {
      const fromNode = nodeMap.get(path[i])!;
      const toNode = nodeMap.get(path[i + 1])!;
      newParticles.push({
        id: particleId + i,
        fromX: fromNode.x,
        fromY: fromNode.y,
        toX: toNode.x,
        toY: toNode.y,
        color: "#fbbf24", // amber for query
      });
    }

    setParticles(newParticles);
    setParticleId((prev) => prev + path.length);

    // Auto-clear after animation
    const totalDuration = (path.length - 1) * duration * 1000 + 800;
    setTimeout(() => {
      setAnimating(false);
      setAnimationType(null);
      setParticles([]);
    }, totalDuration);
  }, [animating, speed, particleId]);

  // Broadcast Context: particles flow from root to all leaves
  const animateBroadcast = useCallback(() => {
    if (animating) return;
    setAnimationType("broadcast");
    setAnimating(true);
    setSelectedLeaf(null);

    const duration = getSpeedMs(speed) / 1000;
    const newParticles: ParticleState[] = [];

    LEAF_IDS.forEach((leafId, leafIdx) => {
      const path = getPathFromRoot(leafId);
      for (let i = 0; i < path.length - 1; i++) {
        const fromNode = nodeMap.get(path[i])!;
        const toNode = nodeMap.get(path[i + 1])!;
        newParticles.push({
          id: particleId + leafIdx * 10 + i,
          fromX: fromNode.x,
          fromY: fromNode.y,
          toX: toNode.x,
          toY: toNode.y,
          color: "#34d399", // emerald for broadcast
        });
      }
    });

    setParticles(newParticles);
    setParticleId((prev) => prev + LEAF_IDS.length * 10);

    const totalDuration = 4 * duration * 1000 + 800;
    setTimeout(() => {
      setAnimating(false);
      setAnimationType(null);
      setParticles([]);
    }, totalDuration);
  }, [animating, speed, particleId]);

  // Cleanup animation on unmount
  useEffect(() => {
    return () => {
      setParticles([]);
    };
  }, []);

  const durationPerHop = getSpeedMs(speed) / 1000;

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-2">
        <motion.button
          onClick={animateQuery}
          disabled={animating}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-medium hover:bg-amber-500/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          {animating && animationType === "query" ? (
            <Pause className="w-3.5 h-3.5" />
          ) : (
            <Play className="w-3.5 h-3.5" />
          )}
          Animate Query
        </motion.button>

        <motion.button
          onClick={animateBroadcast}
          disabled={animating}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium hover:bg-emerald-500/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <Radio className="w-3.5 h-3.5" />
          Broadcast Context
        </motion.button>

        {/* Speed control */}
        <div className="flex items-center gap-1 ml-auto">
          <FastForward className="w-3 h-3 text-slate-400" />
          {(["slow", "medium", "fast"] as SpeedPreset[]).map((s) => (
            <motion.button
              key={s}
              onClick={() => setSpeed(s)}
              className={`px-2 py-1 rounded text-[10px] font-mono font-medium transition-colors ${
                speed === s
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                  : "text-slate-500 hover:text-slate-300 border border-transparent"
              }`}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              {s}
            </motion.button>
          ))}
        </div>
      </div>

      {/* Status info */}
      <AnimatePresence>
        {selectedLeaf && !animating && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            className="flex items-center gap-2 text-xs text-slate-400"
          >
            <GitBranch className="w-3.5 h-3.5 text-emerald-400" />
            <span>
              Query path: <span className="text-emerald-400 font-mono">{selectedLeaf}</span>
              {" -> "}
              <span className="text-emerald-400 font-mono">root</span>
              {" | "}
              <span className="text-amber-400 font-mono">O(logN) = {getPathLength(selectedLeaf)} hops</span>
            </span>
          </motion.div>
        )}
        {animating && animationType === "query" && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            className="flex items-center gap-2 text-xs text-amber-400"
          >
            <Play className="w-3.5 h-3.5" />
            <span>Query traveling to root... O(logN) path</span>
          </motion.div>
        )}
        {animating && animationType === "broadcast" && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            className="flex items-center gap-2 text-xs text-emerald-400"
          >
            <Radio className="w-3.5 h-3.5" />
            <span>Global context broadcasting to all leaves...</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* SVG Tree */}
      <div className="rounded-xl border border-border/30 bg-slate-950/50 overflow-hidden">
        <svg
          viewBox="0 0 800 440"
          className="w-full h-auto"
          role="img"
          aria-label="HBTA Binary Tree Visualization"
        >
          {/* Background grid pattern */}
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="oklch(1 0 0 / 3%)" strokeWidth="0.5" />
            </pattern>
            <radialGradient id="rootGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.3" />
              <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
            </radialGradient>
          </defs>
          <rect width="800" height="440" fill="url(#grid)" />

          {/* Root glow effect */}
          <circle cx="400" cy="55" r="60" fill="url(#rootGlow)" />

          {/* Edges */}
          {EDGES.map((edge) => {
            const fromNode = nodeMap.get(edge.from)!;
            const toNode = nodeMap.get(edge.to)!;
            const edgeKey = `${edge.from}-${edge.to}`;
            const isHighlighted = highlightedEdges.has(edgeKey);
            return (
              <TreeEdge
                key={edgeKey}
                from={fromNode}
                to={toNode}
                highlighted={isHighlighted}
                direction={isHighlighted && animationType === "query" ? "up" : isHighlighted && animationType === "broadcast" ? "down" : "none"}
              />
            );
          })}

          {/* Particles */}
          {particles.map((p, idx) => {
            const hopIndex = idx;
            return (
              <TravelingParticle
                key={p.id}
                fromX={p.fromX}
                fromY={p.fromY}
                toX={p.toX}
                toY={p.toY}
                color={p.color}
                duration={durationPerHop}
                delay={hopIndex * durationPerHop * 0.8}
              />
            );
          })}

          {/* Nodes */}
          {NODES.map((node, i) => {
            const delay = node.level === "root" ? 0 : node.level === "upper" ? 0.1 : node.level === "mid" ? 0.2 : 0.3;
            return (
              <TreeNodeCircle
                key={node.id}
                node={node}
                isSelected={selectedLeaf === node.id}
                isOnPath={highlightedPath.has(node.id)}
                onClick={handleNodeClick}
                animationDelay={delay + i * 0.02}
              />
            );
          })}

          {/* Level labels */}
          <motion.text
            x={790}
            y={58}
            textAnchor="end"
            fill="oklch(0.5 0 0)"
            fontSize={9}
            fontFamily="monospace"
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.6 }}
            transition={{ delay: 0.5 }}
          >
            Level 0
          </motion.text>
          <motion.text
            x={790}
            y={153}
            textAnchor="end"
            fill="oklch(0.5 0 0)"
            fontSize={9}
            fontFamily="monospace"
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.6 }}
            transition={{ delay: 0.6 }}
          >
            Level 1
          </motion.text>
          <motion.text
            x={790}
            y={268}
            textAnchor="end"
            fill="oklch(0.5 0 0)"
            fontSize={9}
            fontFamily="monospace"
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.6 }}
            transition={{ delay: 0.7 }}
          >
            Level 2
          </motion.text>
          <motion.text
            x={790}
            y={393}
            textAnchor="end"
            fill="oklch(0.5 0 0)"
            fontSize={9}
            fontFamily="monospace"
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.6 }}
            transition={{ delay: 0.8 }}
          >
            Leaves
          </motion.text>
        </svg>
      </div>

      {/* Instruction text */}
      <p className="text-[11px] text-muted-foreground flex items-center gap-1.5">
        <Info className="w-3 h-3" />
        Click any leaf node to trace its query path to root. Each path is O(logN) = 3 hops.
      </p>

      {/* Comparison Panel */}
      <ComparisonPanel />
    </div>
  );
}
