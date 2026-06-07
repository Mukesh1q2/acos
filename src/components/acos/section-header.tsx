'use client';

import { motion } from 'framer-motion';
import React from 'react';

interface SectionHeaderProps {
  sectionNumber: number;
  title: string;
  subtitle?: string;
  badge?: string;
  icon?: React.ReactNode;
  className?: string;
  id?: string;
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.05,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] },
  },
};

export function SectionHeader({
  sectionNumber,
  title,
  subtitle,
  badge,
  icon,
  className,
  id,
}: SectionHeaderProps) {
  const paddedNumber = String(sectionNumber).padStart(2, '0');

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className={`relative ${className ?? ''}`}
    >
      <div className="flex items-start gap-4">
        {/* Icon Container */}
        {icon && (
          <motion.div
            variants={itemVariants}
            className="w-12 h-12 rounded-xl bg-emerald-600/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0 animate-gradient-border"
          >
            {icon}
          </motion.div>
        )}

        <div className="relative flex-1 min-w-0">
          {/* Section number watermark */}
          <div
            className="absolute -top-6 -left-2 text-7xl font-bold select-none pointer-events-none bg-gradient-to-r from-emerald-500/10 to-teal-500/10 bg-clip-text text-transparent leading-none"
            aria-hidden="true"
          >
            {paddedNumber}
          </div>

          {/* Title */}
          <motion.h2
            id={id}
            variants={itemVariants}
            className="text-2xl md:text-3xl font-bold text-foreground relative"
          >
            {title}
            {/* Emerald underline decoration */}
            <div className="mt-1.5 h-0.5 w-16 bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full" />
          </motion.h2>

          {/* Badge */}
          {badge && (
            <motion.span
              variants={itemVariants}
              className="inline-flex px-2.5 py-0.5 rounded-full bg-emerald-600/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono mt-2 shadow-[0_0_8px_rgba(16,185,129,0.1)]"
            >
              {badge}
            </motion.span>
          )}

          {/* Subtitle */}
          {subtitle && (
            <motion.p
              variants={itemVariants}
              className="text-sm text-muted-foreground mt-2"
            >
              {subtitle}
            </motion.p>
          )}

          {/* Gradient line */}
          <motion.div
            variants={itemVariants}
            className="h-px bg-gradient-to-r from-emerald-500/30 via-teal-400/20 to-transparent mt-4"
          />
        </div>
      </div>
    </motion.div>
  );
}
