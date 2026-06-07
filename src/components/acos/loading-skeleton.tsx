"use client";

import { Card, CardContent } from "@/components/ui/card";

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
