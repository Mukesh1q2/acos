"use client";

import { Badge } from "@/components/ui/badge";

type StatusType =
  | "Proven"
  | "Proven (Theory)"
  | "Proven (Local)"
  | "Plausible"
  | "Experimental"
  | "High Risk"
  | "High Risk (Hardware)"
  | "planned"
  | "future"
  | "active";

const statusColors: Record<string, string> = {
  Proven: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  "Proven (Theory)": "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  "Proven (Local)": "bg-emerald-600/20 text-emerald-400 border-emerald-600/30",
  Plausible: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  Experimental: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  "High Risk": "bg-red-500/20 text-red-400 border-red-500/30",
  "High Risk (Hardware)": "bg-red-500/20 text-red-400 border-red-500/30",
  planned: "bg-teal-500/20 text-teal-400 border-teal-500/30",
  future: "bg-slate-500/20 text-slate-400 border-slate-500/30",
  active: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
};

interface StatusBadgeProps {
  status: StatusType;
  className?: string;
}

export function StatusBadge({ status, className = "" }: StatusBadgeProps) {
  const colorClass = statusColors[status] || "bg-slate-500/20 text-slate-400 border-slate-500/30";

  return (
    <Badge
      variant="outline"
      className={`${colorClass} font-mono text-xs px-2 py-0.5 ${className}`}
    >
      {status}
    </Badge>
  );
}
