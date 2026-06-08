"use client";

import { useEffect, useState, useRef, type RefObject } from "react";
import { Clock } from "lucide-react";

interface ReadingTimeProps {
  contentRef: RefObject<HTMLDivElement | null>;
}

function estimateReadingTime(el: HTMLElement): number {
  const text = el.textContent || "";
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  // Average reading speed: 200 words per minute
  const minutes = Math.max(1, Math.ceil(words / 200));
  return minutes;
}

export function ReadingTime({ contentRef }: ReadingTimeProps) {
  const [minutes, setMinutes] = useState<number | null>(null);
  const measured = useRef(false);

  useEffect(() => {
    const el = contentRef.current;
    if (!el) return;

    // Defer measurement to allow content to render
    const raf = requestAnimationFrame(() => {
      const m = estimateReadingTime(el);
      setMinutes(m);
      measured.current = true;
    });

    return () => cancelAnimationFrame(raf);
  }, [contentRef]);

  // Re-measure when section content changes (observed via mutation)
  useEffect(() => {
    const el = contentRef.current;
    if (!el) return;

    const observer = new MutationObserver(() => {
      const m = estimateReadingTime(el);
      setMinutes(m);
    });

    observer.observe(el, { childList: true, subtree: true, characterData: true });
    return () => observer.disconnect();
  }, [contentRef]);

  if (minutes === null) return null;

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono text-muted-foreground bg-muted/30 border border-border/20">
      <Clock className="w-3 h-3" />
      {minutes} min read
    </span>
  );
}
