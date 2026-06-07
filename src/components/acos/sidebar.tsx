"use client";

import { useState, useSyncExternalStore } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain,
  FileText,
  Layers,
  Cpu,
  GraduationCap,
  RotateCcw,
  Workflow,
  Monitor,
  Sparkles,
  TrendingUp,
  ShieldAlert,
  Map,
  Menu,
  X,
  ChevronRight,
  Sun,
  Moon,
} from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";

export interface NavItem {
  id: string;
  label: string;
  shortLabel: string;
  icon: React.ReactNode;
}

export const navItems: NavItem[] = [
  { id: "overview", label: "Overview", shortLabel: "Overview", icon: <Brain className="w-4 h-4" /> },
  { id: "part1", label: "Part 1 — Whitepaper Analysis", shortLabel: "Whitepaper", icon: <FileText className="w-4 h-4" /> },
  { id: "part2", label: "Part 2 — ACOS Design", shortLabel: "ACOS Design", icon: <Layers className="w-4 h-4" /> },
  { id: "part3", label: "Part 3 — AFM Architecture", shortLabel: "AFM Arch", icon: <Cpu className="w-4 h-4" /> },
  { id: "part4", label: "Part 4 — Training Strategy", shortLabel: "Training", icon: <GraduationCap className="w-4 h-4" /> },
  { id: "part5", label: "Part 5 — Continuous Learning", shortLabel: "Learning", icon: <RotateCcw className="w-4 h-4" /> },
  { id: "part6", label: "Part 6 — Model Orchestration", shortLabel: "Orchestration", icon: <Workflow className="w-4 h-4" /> },
  { id: "part7", label: "Part 7 — Multimodal Platform", shortLabel: "Multimodal", icon: <Monitor className="w-4 h-4" /> },
  { id: "part8", label: "Part 8 — Self-Evolution", shortLabel: "Evolution", icon: <Sparkles className="w-4 h-4" /> },
  { id: "part9", label: "Part 9 — Market Strategy", shortLabel: "Market", icon: <TrendingUp className="w-4 h-4" /> },
  { id: "part10", label: "Part 10 — Attack Analysis", shortLabel: "Attack", icon: <ShieldAlert className="w-4 h-4" /> },
  { id: "part11", label: "Part 11 — Master Plan", shortLabel: "Master Plan", icon: <Map className="w-4 h-4" /> },
];

interface SidebarProps {
  activeSection: string;
  onSectionChange: (id: string) => void;
}

export function Sidebar({ activeSection, onSectionChange }: SidebarProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { theme, setTheme } = useTheme();
  // Prevent hydration mismatch — only render theme toggle after mount
  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );

  const sidebarContent = (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="px-4 py-5 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center">
          <Brain className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="text-sm font-bold text-foreground tracking-tight">
            ACOS
          </div>
          <div className="text-[10px] text-muted-foreground font-mono">
            v0.1.0-alpha
          </div>
        </div>
      </div>

      <Separator className="bg-border/50" />

      {/* Navigation */}
      <ScrollArea className="flex-1 px-2 py-3">
        <div className="space-y-0.5">
          {navItems.map((item) => {
            const isActive = activeSection === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  onSectionChange(item.id);
                  setMobileOpen(false);
                }}
                className={`
                  w-full flex items-center gap-3 px-3 py-2 rounded-md text-left
                  transition-all duration-200 group relative
                  ${
                    isActive
                      ? "bg-emerald-600/15 text-emerald-400"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  }
                `}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeIndicator"
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-emerald-500 rounded-r"
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                  />
                )}
                <span
                  className={`flex-shrink-0 ${isActive ? "text-emerald-400" : "text-muted-foreground group-hover:text-foreground"}`}
                >
                  {item.icon}
                </span>
                <span className="text-sm truncate">{item.shortLabel}</span>
                {isActive && (
                  <ChevronRight className="w-3 h-3 ml-auto text-emerald-500" />
                )}
              </button>
            );
          })}
        </div>
      </ScrollArea>

      <Separator className="bg-border/50" />

      {/* Theme toggle */}
      <div className="px-3 py-3">
        {mounted ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="w-full justify-start gap-2 text-muted-foreground hover:text-foreground"
          >
            {theme === "dark" ? (
              <Sun className="w-4 h-4" />
            ) : (
              <Moon className="w-4 h-4" />
            )}
            <span className="text-xs">
              {theme === "dark" ? "Light Mode" : "Dark Mode"}
            </span>
          </Button>
        ) : (
          <div className="h-9 px-4 py-2 flex items-center gap-2">
            <div className="w-4 h-4" />
            <span className="text-xs text-muted-foreground">Loading...</span>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile hamburger */}
      <div className="lg:hidden fixed top-3 left-3 z-50">
        <Button
          variant="outline"
          size="icon"
          onClick={() => setMobileOpen(!mobileOpen)}
          className="bg-card/80 backdrop-blur-sm border-border/50"
        >
          {mobileOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
        </Button>
      </div>

      {/* Mobile drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="lg:hidden fixed inset-0 bg-black/50 z-40"
              onClick={() => setMobileOpen(false)}
            />
            <motion.aside
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="lg:hidden fixed left-0 top-0 bottom-0 w-[260px] bg-slate-950 border-r border-border/30 z-50"
            >
              {sidebarContent}
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-[220px] flex-col border-r border-border/30 bg-slate-950 flex-shrink-0">
        {sidebarContent}
      </aside>
    </>
  );
}
