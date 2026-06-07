"use client";

import { useState, useEffect, useCallback, useRef, type RefObject } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface ReadingProgressProps {
  contentRef: RefObject<HTMLDivElement | null>;
}

export function ReadingProgress({ contentRef }: ReadingProgressProps) {
  const [progress, setProgress] = useState(0);

  const handleScroll = useCallback(() => {
    const el = contentRef.current;
    if (!el) return;

    const { scrollTop, scrollHeight, clientHeight } = el;
    const scrollable = scrollHeight - clientHeight;

    if (scrollable <= 0) {
      setProgress(0);
      return;
    }

    const pct = Math.min(100, (scrollTop / scrollable) * 100);
    setProgress(pct);
  }, [contentRef]);

  useEffect(() => {
    const el = contentRef.current;
    if (!el) return;

    el.addEventListener("scroll", handleScroll, { passive: true });
    return () => el.removeEventListener("scroll", handleScroll);
  }, [contentRef, handleScroll]);

  // Reset progress when section changes (detected via scroll position reset)
  const prevScrollTop = useRef(0);
  useEffect(() => {
    const el = contentRef.current;
    if (!el) return;

    const checkReset = () => {
      if (el.scrollTop < prevScrollTop.current - 50 && el.scrollTop < 10) {
        setProgress(0);
      }
      prevScrollTop.current = el.scrollTop;
    };

    const interval = setInterval(checkReset, 300);
    return () => clearInterval(interval);
  }, [contentRef]);

  const isVisible = progress > 0;

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="h-[2px] w-full bg-muted/20 flex-shrink-0 relative overflow-hidden"
        >
          <motion.div
            className="absolute top-0 left-0 h-full bg-gradient-to-r from-emerald-500 via-teal-400 to-emerald-400"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.15, ease: "easeOut" }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
