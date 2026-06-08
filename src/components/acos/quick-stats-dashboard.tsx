"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { motion, useInView } from "framer-motion";
import {
  Activity,
  Zap,
  Database,
  Shield,
  CheckCircle,
  DollarSign,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

/* ------------------------------------------------------------------ */
/*  Animated Counter Hook                                              */
/* ------------------------------------------------------------------ */

function useAnimatedCounter(
  target: number,
  duration: number = 1500,
  startOnView: boolean = true
) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true });
  const hasStarted = useRef(false);

  useEffect(() => {
    if (startOnView && !isInView) return;
    if (hasStarted.current) return;
    hasStarted.current = true;

    const startTime = Date.now();
    const step = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.round(eased * target));
      if (progress < 1) {
        requestAnimationFrame(step);
      }
    };
    requestAnimationFrame(step);
  }, [isInView, startOnView, target, duration]);

  return { count, ref };
}

/* ------------------------------------------------------------------ */
/*  Sparkline Data                                                     */
/* ------------------------------------------------------------------ */

interface StatConfig {
  id: string;
  icon: React.ReactNode;
  label: string;
  value: number;
  suffix: string;
  prefix?: string;
  displayOverride?: string;
  delta: string;
  deltaType: "positive" | "negative" | "neutral";
  sparklineData: number[];
  colorTheme: {
    primary: string;
    gradient: string;
    border: string;
    bg: string;
    iconBg: string;
    iconText: string;
    sparkStroke: string;
    sparkFillStart: string;
    sparkFillEnd: string;
    deltaText: string;
  };
}

const stats: StatConfig[] = [
  {
    id: "attention-speedup",
    icon: <Zap className="w-4.5 h-4.5" />,
    label: "Attention Speedup",
    value: 77,
    suffix: "x",
    delta: "+77x vs Standard",
    deltaType: "positive",
    sparklineData: [5, 12, 18, 28, 35, 42, 50, 58, 65, 72, 77],
    colorTheme: {
      primary: "emerald",
      gradient: "from-emerald-500/10 via-emerald-600/5 to-transparent",
      border: "border-emerald-500/20",
      bg: "bg-emerald-500/5",
      iconBg: "bg-emerald-500/15",
      iconText: "text-emerald-400",
      sparkStroke: "#10b981",
      sparkFillStart: "rgba(16, 185, 129, 0.2)",
      sparkFillEnd: "rgba(16, 185, 129, 0)",
      deltaText: "text-emerald-400",
    },
  },
  {
    id: "memory-reduction",
    icon: <Database className="w-4.5 h-4.5" />,
    label: "Memory Reduction",
    value: 250,
    suffix: "x",
    delta: "250x less RAM",
    deltaType: "positive",
    sparklineData: [10, 30, 55, 80, 100, 130, 160, 190, 220, 240, 250],
    colorTheme: {
      primary: "teal",
      gradient: "from-teal-500/10 via-teal-600/5 to-transparent",
      border: "border-teal-500/20",
      bg: "bg-teal-500/5",
      iconBg: "bg-teal-500/15",
      iconText: "text-teal-400",
      sparkStroke: "#14b8a6",
      sparkFillStart: "rgba(20, 184, 166, 0.2)",
      sparkFillEnd: "rgba(20, 184, 166, 0)",
      deltaText: "text-teal-400",
    },
  },
  {
    id: "knowledge-retention",
    icon: <Activity className="w-4.5 h-4.5" />,
    label: "Knowledge Retention",
    value: 86,
    suffix: "%",
    delta: "+68% vs fine-tuning",
    deltaType: "positive",
    sparklineData: [95, 94, 93, 92, 91, 90, 89, 88, 87, 86, 86],
    colorTheme: {
      primary: "green",
      gradient: "from-green-500/10 via-green-600/5 to-transparent",
      border: "border-green-500/20",
      bg: "bg-green-500/5",
      iconBg: "bg-green-500/15",
      iconText: "text-green-400",
      sparkStroke: "#22c55e",
      sparkFillStart: "rgba(34, 197, 94, 0.2)",
      sparkFillEnd: "rgba(34, 197, 94, 0)",
      deltaText: "text-green-400",
    },
  },
  {
    id: "thread-isolation",
    icon: <Shield className="w-4.5 h-4.5" />,
    label: "Thread Isolation",
    value: 0,
    suffix: "%",
    delta: "0% interference",
    deltaType: "neutral",
    sparklineData: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    colorTheme: {
      primary: "cyan",
      gradient: "from-cyan-500/10 via-cyan-600/5 to-transparent",
      border: "border-cyan-500/20",
      bg: "bg-cyan-500/5",
      iconBg: "bg-cyan-500/15",
      iconText: "text-cyan-400",
      sparkStroke: "#06b6d4",
      sparkFillStart: "rgba(6, 182, 212, 0.2)",
      sparkFillEnd: "rgba(6, 182, 212, 0)",
      deltaText: "text-cyan-400",
    },
  },
  {
    id: "convergence-proof",
    icon: <CheckCircle className="w-4.5 h-4.5" />,
    label: "Convergence Proof",
    value: 0, // won't be animated since displayOverride is used
    suffix: "",
    displayOverride: "Local",
    delta: "Mathematically proven",
    deltaType: "positive",
    sparklineData: [80, 70, 55, 45, 38, 30, 25, 20, 18, 16, 15],
    colorTheme: {
      primary: "emerald",
      gradient: "from-emerald-500/10 via-emerald-600/5 to-transparent",
      border: "border-emerald-500/20",
      bg: "bg-emerald-500/5",
      iconBg: "bg-emerald-500/15",
      iconText: "text-emerald-400",
      sparkStroke: "#10b981",
      sparkFillStart: "rgba(16, 185, 129, 0.2)",
      sparkFillEnd: "rgba(16, 185, 129, 0)",
      deltaText: "text-emerald-400",
    },
  },
  {
    id: "training-cost",
    icon: <DollarSign className="w-4.5 h-4.5" />,
    label: "Training Cost",
    value: 25,
    suffix: "K",
    prefix: "$",
    delta: "Phase 1-2 affordable",
    deltaType: "negative",
    sparklineData: [120, 100, 85, 70, 55, 45, 38, 32, 28, 26, 25],
    colorTheme: {
      primary: "amber",
      gradient: "from-amber-500/10 via-amber-600/5 to-transparent",
      border: "border-amber-500/20",
      bg: "bg-amber-500/5",
      iconBg: "bg-amber-500/15",
      iconText: "text-amber-400",
      sparkStroke: "#f59e0b",
      sparkFillStart: "rgba(245, 158, 11, 0.2)",
      sparkFillEnd: "rgba(245, 158, 11, 0)",
      deltaText: "text-amber-400",
    },
  },
];

/* ------------------------------------------------------------------ */
/*  Sparkline Component                                                */
/* ------------------------------------------------------------------ */

function Sparkline({
  data,
  color,
  fillStart,
  fillEnd,
  delay = 0,
}: {
  data: number[];
  color: string;
  fillStart: string;
  fillEnd: string;
  delay?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true });
  const [animated, setAnimated] = useState(false);

  useEffect(() => {
    if (!isInView) return;
    const timeout = setTimeout(() => setAnimated(true), delay);
    return () => clearTimeout(timeout);
  }, [isInView, delay]);

  const width = 80;
  const height = 30;
  const padding = 2;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data.map((val, i) => {
    const x = padding + (i / (data.length - 1)) * (width - padding * 2);
    const y = height - padding - ((val - min) / range) * (height - padding * 2);
    return `${x},${y}`;
  });

  const linePath = points.join(" ");
  const fillPath = `${linePath} ${width - padding},${height - padding} ${padding},${height - padding}`;

  const gradientId = `sparkline-grad-${color.replace("#", "")}`;

  return (
    <div ref={ref} className="flex-shrink-0">
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        className="overflow-visible"
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={fillStart} />
            <stop offset="100%" stopColor={fillEnd} />
          </linearGradient>
        </defs>
        {/* Fill area */}
        <motion.polygon
          points={fillPath}
          fill={`url(#${gradientId})`}
          initial={{ opacity: 0 }}
          animate={animated ? { opacity: 1 } : { opacity: 0 }}
          transition={{ duration: 0.8, delay: 0.3 }}
        />
        {/* Line */}
        <motion.polyline
          points={linePath}
          fill="none"
          stroke={color}
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={
            animated
              ? { pathLength: 1, opacity: 1 }
              : { pathLength: 0, opacity: 0 }
          }
          transition={{ duration: 1.2, ease: "easeOut" }}
        />
        {/* End dot */}
        {data.length > 0 && (
          <motion.circle
            cx={padding + ((data.length - 1) / (data.length - 1)) * (width - padding * 2)}
            cy={height - padding - ((data[data.length - 1] - min) / range) * (height - padding * 2)}
            r="2.5"
            fill={color}
            initial={{ scale: 0, opacity: 0 }}
            animate={animated ? { scale: 1, opacity: 1 } : { scale: 0, opacity: 0 }}
            transition={{ duration: 0.3, delay: 1.2 }}
          />
        )}
      </svg>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Stat Card Component                                                */
/* ------------------------------------------------------------------ */

function StatCard({ stat, index }: { stat: StatConfig; index: number }) {
  const { count, ref } = useAnimatedCounter(stat.value, 1500);

  const DeltaIcon =
    stat.deltaType === "positive" ? TrendingUp : TrendingDown;

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 24, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        duration: 0.5,
        delay: index * 0.1,
        ease: [0.25, 0.46, 0.45, 0.94],
      }}
    >
      <Card
        className={`relative overflow-hidden border ${stat.colorTheme.border} ${stat.colorTheme.bg} backdrop-blur-sm card-hover-lift group h-full`}
      >
        {/* Subtle gradient background */}
        <div
          className={`absolute inset-0 bg-gradient-to-br ${stat.colorTheme.gradient} opacity-60`}
        />

        <CardContent className="relative z-10 p-4">
          {/* Top row: icon + label */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2.5">
              <div
                className={`w-8 h-8 rounded-lg ${stat.colorTheme.iconBg} border ${stat.colorTheme.border} flex items-center justify-center ${stat.colorTheme.iconText}`}
              >
                {stat.icon}
              </div>
              <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-wider leading-tight">
                {stat.label}
              </span>
            </div>
          </div>

          {/* Middle row: value + sparkline */}
          <div className="flex items-end justify-between gap-3">
            <div className="flex items-baseline gap-1">
              {stat.prefix && (
                <span
                  className={`text-lg font-semibold ${stat.colorTheme.iconText}`}
                >
                  {stat.prefix}
                </span>
              )}
              <span
                className={`text-2xl md:text-3xl font-bold ${stat.colorTheme.iconText}`}
              >
                {stat.displayOverride ?? (stat.value === 0 ? "0" : count)}
              </span>
              {stat.suffix && (
                <span
                  className={`text-sm font-semibold ${stat.colorTheme.iconText} opacity-80`}
                >
                  {stat.suffix}
                </span>
              )}
            </div>

            <Sparkline
              data={stat.sparklineData}
              color={stat.colorTheme.sparkStroke}
              fillStart={stat.colorTheme.sparkFillStart}
              fillEnd={stat.colorTheme.sparkFillEnd}
              delay={index * 100 + 300}
            />
          </div>

          {/* Bottom row: delta indicator */}
          <div className="flex items-center gap-1.5 mt-2.5">
            {stat.deltaType !== "neutral" && (
              <DeltaIcon className="w-3 h-3 flex-shrink-0" />
            )}
            <span
              className={`text-[11px] font-medium ${stat.colorTheme.deltaText} opacity-90`}
            >
              {stat.delta}
            </span>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export function QuickStatsDashboard() {
  const containerRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(containerRef, { once: true, margin: "-50px" });

  const getMotionProps = useCallback(
    (delay: number) => ({
      initial: { opacity: 0, y: 20 } as const,
      animate: (isInView
        ? { opacity: 1, y: 0 }
        : { opacity: 0, y: 20 }) as const,
      transition: { duration: 0.5, delay } as const,
    }),
    [isInView]
  );

  return (
    <div ref={containerRef}>
      {/* Section heading */}
      <motion.div
        {...getMotionProps(0)}
        className="flex items-center gap-2.5 mb-5"
      >
        <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
          <Activity className="w-4 h-4 text-emerald-400" />
        </div>
        <h2 className="text-lg font-semibold text-foreground">
          Performance Dashboard
        </h2>
        <div className="flex-1 h-px bg-gradient-to-r from-emerald-500/20 to-transparent ml-2" />
      </motion.div>

      {/* Stats grid: 2 cols mobile, 3 cols desktop */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 md:gap-4">
        {stats.map((stat, i) => (
          <StatCard key={stat.id} stat={stat} index={i} />
        ))}
      </div>

      {/* Bottom insight bar */}
      <motion.div
        {...getMotionProps(0.7)}
        className="mt-4 p-3 rounded-lg bg-card/40 border border-border/20 flex items-center gap-2 text-[11px] text-muted-foreground"
      >
        <Zap className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
        <span>
          All metrics measured against standard LLM baselines. HBTA = Hierarchical
          Binary Tree Attention, OTM = Orthogonal Thread Memory.
        </span>
      </motion.div>
    </div>
  );
}
