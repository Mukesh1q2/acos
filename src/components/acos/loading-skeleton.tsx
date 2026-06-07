"use client";

import { Card, CardContent } from "@/components/ui/card";

/* ------------------------------------------------------------------ */
/*  Original LoadingSkeleton                                           */
/* ------------------------------------------------------------------ */

interface LoadingSkeletonProps {
  /** Number of card placeholders to show (default 4) */
  cards?: number;
  /** Show a title placeholder (default true) */
  showTitle?: boolean;
}

export function LoadingSkeleton({ cards = 4, showTitle = true }: LoadingSkeletonProps) {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Title placeholder */}
      {showTitle && (
        <div className="text-center space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-600/10 border border-emerald-500/20">
            <div className="w-3 h-3 rounded-full bg-emerald-500/20" />
            <div className="w-24 h-2.5 rounded bg-emerald-500/15" />
          </div>
          <div className="mx-auto w-48 h-7 rounded-lg bg-emerald-500/10" />
          <div className="mx-auto w-64 h-3 rounded bg-muted/30" />
        </div>
      )}

      {/* Card placeholders */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {Array.from({ length: cards }).map((_, i) => (
          <Card
            key={i}
            className="border-emerald-500/10 bg-emerald-500/[0.02]"
          >
            <CardContent className="p-4 space-y-3">
              {/* Header line */}
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex-shrink-0" />
                <div className="flex-1 space-y-1.5">
                  <div className="w-2/3 h-3 rounded bg-emerald-500/10" />
                  <div className="w-1/3 h-2 rounded bg-muted/20" />
                </div>
              </div>
              {/* Body lines */}
              <div className="space-y-2">
                <div className="w-full h-2 rounded bg-muted/20" />
                <div className="w-5/6 h-2 rounded bg-muted/15" />
                <div className="w-3/4 h-2 rounded bg-muted/10" />
              </div>
              {/* Bottom badge */}
              <div className="flex gap-2">
                <div className="w-14 h-5 rounded-md bg-emerald-500/8" />
                <div className="w-10 h-5 rounded-md bg-emerald-500/5" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  CardSkeleton — shimmer animation variant                           */
/* ------------------------------------------------------------------ */

interface CardSkeletonProps {
  /** Number of card skeletons (default 3) */
  count?: number;
  /** Grid columns (default 2) */
  columns?: number;
  className?: string;
}

export function CardSkeleton({ count = 3, columns = 2, className }: CardSkeletonProps) {
  return (
    <div
      className={`grid gap-4 ${columns === 1 ? "grid-cols-1" : columns === 2 ? "grid-cols-1 md:grid-cols-2" : "grid-cols-1 md:grid-cols-2 lg:grid-cols-3"}`}
    >
      {Array.from({ length: count }).map((_, i) => (
        <Card
          key={i}
          className={`border-emerald-500/10 bg-emerald-500/[0.02] overflow-hidden ${className ?? ""}`}
        >
          <CardContent className="p-5 space-y-3">
            {/* Header */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg skeleton-shimmer flex-shrink-0" />
              <div className="flex-1 space-y-2">
                <div className="w-3/5 h-3 rounded skeleton-shimmer" />
                <div className="w-2/5 h-2 rounded skeleton-shimmer" />
              </div>
            </div>
            {/* Body */}
            <div className="space-y-2">
              <div className="w-full h-2 rounded skeleton-shimmer" />
              <div className="w-4/5 h-2 rounded skeleton-shimmer" />
            </div>
            {/* Footer badges */}
            <div className="flex gap-2 pt-1">
              <div className="w-16 h-5 rounded-md skeleton-shimmer" />
              <div className="w-12 h-5 rounded-md skeleton-shimmer" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  TextSkeleton — varying width lines with shimmer                    */
/* ------------------------------------------------------------------ */

interface TextSkeletonProps {
  /** Number of text lines (default 3) */
  lines?: number;
  className?: string;
}

const lineWidths = ["w-full", "w-5/6", "w-4/5", "w-3/4", "w-2/3", "w-1/2"];

export function TextSkeleton({ lines = 3, className }: TextSkeletonProps) {
  return (
    <div className={`space-y-2 ${className ?? ""}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={`h-3 rounded skeleton-shimmer ${lineWidths[i % lineWidths.length]}`}
        />
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  ChartSkeleton — placeholder chart shape with shimmer               */
/* ------------------------------------------------------------------ */

interface ChartSkeletonProps {
  className?: string;
}

export function ChartSkeleton({ className }: ChartSkeletonProps) {
  return (
    <Card className={`border-emerald-500/10 bg-emerald-500/[0.02] overflow-hidden ${className ?? ""}`}>
      <CardContent className="p-5">
        {/* Chart title */}
        <div className="flex items-center justify-between mb-4">
          <div className="w-1/3 h-4 rounded skeleton-shimmer" />
          <div className="flex gap-2">
            <div className="w-16 h-5 rounded-full skeleton-shimmer" />
            <div className="w-16 h-5 rounded-full skeleton-shimmer" />
          </div>
        </div>

        {/* Y-axis labels + chart area */}
        <div className="flex gap-3">
          {/* Y-axis */}
          <div className="flex flex-col justify-between py-1">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="w-8 h-2 rounded skeleton-shimmer" />
            ))}
          </div>

          {/* Chart area with bars */}
          <div className="flex-1">
            <div className="flex items-end gap-2 h-32">
              {[40, 65, 45, 80, 55, 70, 35, 60, 50, 75, 42, 68].map((height, i) => (
                <div
                  key={i}
                  className="flex-1 rounded-t skeleton-shimmer"
                  style={{ height: `${height}%` }}
                />
              ))}
            </div>
            {/* X-axis line */}
            <div className="w-full h-px bg-emerald-500/15 mt-1" />
            {/* X-axis labels */}
            <div className="flex justify-between mt-2">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="w-8 h-2 rounded skeleton-shimmer" />
              ))}
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 mt-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-sm bg-emerald-500/20" />
            <div className="w-16 h-2 rounded skeleton-shimmer" />
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-sm bg-muted/30" />
            <div className="w-16 h-2 rounded skeleton-shimmer" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
