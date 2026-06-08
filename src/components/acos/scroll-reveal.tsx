"use client";

import { useRef, type ReactNode } from "react";
import { motion, useInView, useScroll, useTransform } from "framer-motion";

/* ------------------------------------------------------------------ */
/*  ScrollReveal                                                       */
/* ------------------------------------------------------------------ */

type RevealDirection = "up" | "left" | "right" | "fade";

interface ScrollRevealProps {
  children: ReactNode;
  /** Delay in seconds before animation starts (default 0) */
  delay?: number;
  /** Direction the element enters from (default 'up') */
  direction?: RevealDirection;
  /** Additional CSS classes */
  className?: string;
  /** Whether animation should only play once (default true) */
  once?: boolean;
}

const directionVariants: Record<RevealDirection, { hidden: { opacity: number; x?: number; y?: number }; visible: { opacity: number; x: number; y: number } }> = {
  up: {
    hidden: { opacity: 0, y: 30 },
    visible: { opacity: 1, y: 0 },
  },
  left: {
    hidden: { opacity: 0, x: -30 },
    visible: { opacity: 1, x: 0 },
  },
  right: {
    hidden: { opacity: 0, x: 30 },
    visible: { opacity: 1, x: 0 },
  },
  fade: {
    hidden: { opacity: 0 },
    visible: { opacity: 1, x: 0, y: 0 },
  },
};

export function ScrollReveal({
  children,
  delay = 0,
  direction = "up",
  className,
  once = true,
}: ScrollRevealProps) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once, margin: "-80px" });

  const variants = directionVariants[direction];

  return (
    <motion.div
      ref={ref}
      initial="hidden"
      animate={isInView ? "visible" : "hidden"}
      variants={variants}
      transition={{
        type: "spring",
        stiffness: 100,
        damping: 20,
        delay,
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/*  StaggerContainer                                                   */
/* ------------------------------------------------------------------ */

interface StaggerContainerProps {
  children: ReactNode;
  /** Delay between each child animation in seconds (default 0.1) */
  staggerDelay?: number;
  /** Additional CSS classes */
  className?: string;
}

export function StaggerContainer({
  children,
  staggerDelay = 0.1,
  className,
}: StaggerContainerProps) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <motion.div
      ref={ref}
      initial="hidden"
      animate={isInView ? "visible" : "hidden"}
      variants={{
        hidden: {},
        visible: {
          transition: {
            staggerChildren: staggerDelay,
          },
        },
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/*  StaggerItem — convenience wrapper for StaggerContainer children     */
/* ------------------------------------------------------------------ */

interface StaggerItemProps {
  children: ReactNode;
  /** Direction the item enters from (default 'up') */
  direction?: RevealDirection;
  className?: string;
}

export function StaggerItem({
  children,
  direction = "up",
  className,
}: StaggerItemProps) {
  const variants = directionVariants[direction];

  return (
    <motion.div
      variants={{
        hidden: variants.hidden,
        visible: {
          ...variants.visible,
          transition: {
            type: "spring",
            stiffness: 100,
            damping: 20,
          },
        },
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/*  ParallaxSection                                                    */
/* ------------------------------------------------------------------ */

interface ParallaxSectionProps {
  children: ReactNode;
  /** Parallax speed factor (default 0.1). Keep small for subtle effect. */
  speed?: number;
  /** Additional CSS classes */
  className?: string;
}

export function ParallaxSection({
  children,
  speed = 0.1,
  className,
}: ParallaxSectionProps) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  });

  // Map scroll progress to a subtle translateY, clamped to ~20px max
  const maxPx = 20;
  const y = useTransform(scrollYProgress, [0, 1], [maxPx * speed * 10, -maxPx * speed * 10]);

  return (
    <motion.div ref={ref} style={{ y }} className={className}>
      {children}
    </motion.div>
  );
}
