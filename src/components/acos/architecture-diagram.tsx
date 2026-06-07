"use client";

import { motion } from "framer-motion";

interface ArchNode {
  id: string;
  label: string;
  sublabel?: string;
  x: number;
  y: number;
  color: string;
}

interface ArchConnection {
  from: string;
  to: string;
  label?: string;
}

interface ArchitectureDiagramProps {
  nodes: ArchNode[];
  connections: ArchConnection[];
  width?: number;
  height?: number;
}

export function ArchitectureDiagram({
  nodes,
  connections,
  width = 600,
  height = 400,
}: ArchitectureDiagramProps) {
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full h-auto"
      role="img"
      aria-label="Architecture diagram"
    >
      <defs>
        <marker
          id="arrowhead"
          markerWidth="8"
          markerHeight="6"
          refX="8"
          refY="3"
          orient="auto"
        >
          <polygon
            points="0 0, 8 3, 0 6"
            className="fill-emerald-500/50"
          />
        </marker>
        <filter id="glow">
          <feGaussianBlur stdDeviation="3" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Connections */}
      {connections.map((conn, i) => {
        const from = nodeMap.get(conn.from);
        const to = nodeMap.get(conn.to);
        if (!from || !to) return null;
        return (
          <g key={`conn-${i}`}>
            <motion.line
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              className="stroke-emerald-500/30"
              strokeWidth="2"
              markerEnd="url(#arrowhead)"
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ duration: 0.8, delay: i * 0.15 }}
            />
            {conn.label && (
              <text
                x={(from.x + to.x) / 2}
                y={(from.y + to.y) / 2 - 8}
                textAnchor="middle"
                className="fill-muted-foreground text-[10px] font-mono"
              >
                {conn.label}
              </text>
            )}
          </g>
        );
      })}

      {/* Nodes */}
      {nodes.map((node, i) => (
        <g key={node.id}>
          <motion.rect
            x={node.x - 60}
            y={node.y - 20}
            width="120"
            height="40"
            rx="8"
            className={`${node.color} stroke-emerald-500/20`}
            strokeWidth="1"
            filter="url(#glow)"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.4, delay: i * 0.1 }}
          />
          <motion.text
            x={node.x}
            y={node.sublabel ? node.y - 4 : node.y + 4}
            textAnchor="middle"
            className="fill-foreground text-[11px] font-semibold"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3, delay: i * 0.1 + 0.2 }}
          >
            {node.label}
          </motion.text>
          {node.sublabel && (
            <motion.text
              x={node.x}
              y={node.y + 10}
              textAnchor="middle"
              className="fill-muted-foreground text-[8px] font-mono"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3, delay: i * 0.1 + 0.3 }}
            >
              {node.sublabel}
            </motion.text>
          )}
        </g>
      ))}
    </svg>
  );
}
