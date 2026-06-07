"use client";

import { motion } from "framer-motion";

interface FlowStep {
  id: string;
  label: string;
  description?: string;
  color?: string;
}

interface FlowChartProps {
  steps: FlowStep[];
  direction?: "horizontal" | "vertical";
  animated?: boolean;
}

export function FlowChart({
  steps,
  direction = "horizontal",
  animated = true,
}: FlowChartProps) {
  const isHorizontal = direction === "horizontal";

  return (
    <div
      className={`flex ${isHorizontal ? "flex-row items-center overflow-x-auto pb-2" : "flex-col items-stretch"} gap-0`}
    >
      {steps.map((step, i) => (
        <div
          key={step.id}
          className={`flex ${isHorizontal ? "flex-row items-center" : "flex-col items-stretch"}`}
        >
          <motion.div
            className={`
              relative px-4 py-3 rounded-lg border
              ${step.color || "bg-card border-emerald-500/20"}
              min-w-[140px] text-center
            `}
            initial={animated ? { opacity: 0, scale: 0.9 } : undefined}
            animate={animated ? { opacity: 1, scale: 1 } : undefined}
            transition={{ duration: 0.4, delay: i * 0.12 }}
          >
            <div className="text-sm font-semibold text-foreground">
              {step.label}
            </div>
            {step.description && (
              <div className="text-xs text-muted-foreground mt-1">
                {step.description}
              </div>
            )}
            {/* Step number */}
            <div className="absolute -top-2 -left-2 w-5 h-5 rounded-full bg-emerald-600 text-white text-[10px] font-bold flex items-center justify-center">
              {i + 1}
            </div>
          </motion.div>

          {i < steps.length - 1 && (
            <motion.div
              className={`
                flex items-center justify-center
                ${isHorizontal ? "px-2" : "py-2 justify-center"}
              `}
              initial={animated ? { opacity: 0 } : undefined}
              animate={animated ? { opacity: 1 } : undefined}
              transition={{ duration: 0.3, delay: i * 0.12 + 0.2 }}
            >
              {isHorizontal ? (
                <svg width="32" height="16" className="flex-shrink-0">
                  <motion.line
                    x1="0"
                    y1="8"
                    x2="24"
                    y2="8"
                    className="stroke-emerald-500/50"
                    strokeWidth="2"
                  />
                  <polygon
                    points="24,4 32,8 24,12"
                    className="fill-emerald-500/50"
                  />
                </svg>
              ) : (
                <svg width="16" height="32" className="flex-shrink-0">
                  <motion.line
                    x1="8"
                    y1="0"
                    x2="8"
                    y2="24"
                    className="stroke-emerald-500/50"
                    strokeWidth="2"
                  />
                  <polygon
                    points="4,24 8,32 12,24"
                    className="fill-emerald-500/50"
                  />
                </svg>
              )}
            </motion.div>
          )}
        </div>
      ))}
    </div>
  );
}
