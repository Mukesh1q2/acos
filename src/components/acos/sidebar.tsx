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
  Sigma,
  Route,
  BarChart3,
  Star,
  BookOpen,
  Activity,
  FlaskConical,
  TestTube,
} from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { useBookmarks } from "@/components/acos/bookmarks";
import { HistoryIndicator } from "@/components/acos/reading-history";
import { TourHelpButton } from "@/components/acos/onboarding-tour";
import { SectionCompletionIndicator } from "@/components/acos/section-completion";

export interface NavItem {
  id: string;
  label: string;
  shortLabel: string;
  icon: React.ReactNode;
}

export const navItems: NavItem[] = [
  { id: "overview", label: "Overview", shortLabel: "Overview", icon: <Brain className="w-4 h-4" /> },
  { id: "runtime", label: "Runtime", shortLabel: "Runtime", icon: <Activity className="w-4 h-4" /> },
  { id: "validation", label: "Validation Lab", shortLabel: "Validation", icon: <FlaskConical className="w-4 h-4" /> },
  { id: "scientific-validation", label: "Scientific Validation", shortLabel: "Sci Val", icon: <TestTube className="w-4 h-4" /> },
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
  { id: "roadmap", label: "Roadmap Timeline", shortLabel: "Roadmap", icon: <Route className="w-4 h-4" /> },
  { id: "theorems", label: "Theorem Explorer", shortLabel: "Theorems", icon: <Sigma className="w-4 h-4" /> },
  { id: "performance", label: "Performance Comparison", shortLabel: "Performance", icon: <BarChart3 className="w-4 h-4" /> },
  { id: "glossary", label: "Glossary", shortLabel: "Glossary", icon: <BookOpen className="w-4 h-4" /> },
];

interface SidebarProps {
  activeSection: string;
  onSectionChange: (id: string) => void;
  hidden?: boolean;
}

export function Sidebar({ activeSection, onSectionChange, hidden }: SidebarProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { theme, setTheme } = useTheme();
  const { isBookmarked } = useBookmarks();
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
        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-md shadow-emerald-500/20 logo-glow cursor-pointer">
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
      <ScrollArea data-tour="sidebar-nav" className="flex-1 px-2 py-3">
        <div className="space-y-1">
          {navItems.map((item) => {
            const isActive = activeSection === item.id;
            // Add section dividers
            const showDividerBefore = item.id === "part1" || item.id === "roadmap";
            return (
              <div key={item.id}>
                {showDividerBefore && (
                  <div className="flex items-center gap-2 px-3 py-2 mt-1">
                    <div className="flex-1 h-px bg-border/30" />
                    <span className="text-[9px] text-muted-foreground/50 uppercase tracking-wider font-mono">
                      {item.id === "part1" ? "Analysis" : "Interactive"}
                    </span>
                    <div className="flex-1 h-px bg-border/30" />
                  </div>
                )}
                <button
                  onClick={() => {
                    onSectionChange(item.id);
                    setMobileOpen(false);
                  }}
                  className={`
                    sidebar-nav-item
                    w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-left
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
                      className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-emerald-500 rounded-r"
                      transition={{ type: "spring", stiffness: 350, damping: 25, mass: 0.8 }}
                    />
                  )}
                  <span
                    className={`flex-shrink-0 ${isActive ? "text-emerald-400" : "text-muted-foreground group-hover:text-foreground"}`}
                  >
                    {item.icon}
                  </span>
                  <span className="text-sm truncate">{item.shortLabel}</span>
                  {isBookmarked(item.id) && !isActive && (
                    <Star className="w-3 h-3 ml-1 text-emerald-400 fill-emerald-400 flex-shrink-0 opacity-60" />
                  )}
                  {!isActive && (
                    <SectionCompletionIndicator sectionId={item.id} />
                  )}
                  {!isActive && !isBookmarked(item.id) && (
                    <HistoryIndicator sectionId={item.id} />
                  )}
                  {isActive && (
                    <ChevronRight className="w-3 h-3 ml-auto text-emerald-500" />
                  )}
                </button>
              </div>
            );
          })}
        </div>
      </ScrollArea>

      {/* Gradient line above footer */}
      <div className="mx-3 sidebar-gradient-line" />

      {/* Help tour button */}
      <div className="px-3 pt-3">
        <TourHelpButton />
      </div>

      {/* Theme toggle with animated transition */}
      <div className="px-3 pb-3 pt-1">
        {mounted ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="w-full justify-start gap-2 text-muted-foreground hover:text-foreground group/theme relative overflow-hidden"
          >
            <span className="relative w-4 h-4 flex-shrink-0">
              <motion.span
                initial={false}
                animate={{
                  rotate: theme === "dark" ? 0 : 180,
                  scale: theme === "dark" ? 1 : 0,
                  opacity: theme === "dark" ? 1 : 0,
                }}
                transition={{ duration: 0.3, ease: "easeInOut" }}
                className="absolute inset-0 flex items-center justify-center"
              >
                <Sun className="w-4 h-4" />
              </motion.span>
              <motion.span
                initial={false}
                animate={{
                  rotate: theme === "dark" ? -180 : 0,
                  scale: theme === "dark" ? 0 : 1,
                  opacity: theme === "dark" ? 0 : 1,
                }}
                transition={{ duration: 0.3, ease: "easeInOut" }}
                className="absolute inset-0 flex items-center justify-center"
              >
                <Moon className="w-4 h-4" />
              </motion.span>
            </span>
            <span className="text-xs">
              {theme === "dark" ? "Light Mode" : "Dark Mode"}
            </span>
            {/* Background glow on hover */}
            <span className="absolute inset-0 rounded-md bg-gradient-to-r from-emerald-500/0 via-emerald-500/5 to-teal-500/0 opacity-0 group-hover/theme:opacity-100 transition-opacity duration-300" />
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

  if (hidden) return null;

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
              transition={{ type: "spring", stiffness: 300, damping: 25, mass: 0.8 }}
              className="lg:hidden fixed left-0 top-0 bottom-0 w-[260px] bg-slate-950 border-r border-border/30 z-50"
            >
              {sidebarContent}
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Desktop sidebar */}
      <aside data-tour="sidebar" className="hidden lg:flex w-[220px] flex-col border-r border-border/30 glass-sidebar flex-shrink-0">
        {sidebarContent}
      </aside>
    </>
  );
}
