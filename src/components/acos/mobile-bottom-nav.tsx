'use client';

import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Drawer } from 'vaul';
import {
  Brain,
  Layers,
  RotateCcw,
  Route,
  MoreHorizontal,
  Search,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { navItems } from '@/components/acos/sidebar';

interface MobileBottomNavProps {
  activeSection: string;
  onSectionChange: (id: string) => void;
}

// 5 primary navigation targets shown in the bottom bar
const primaryNavItems = [
  { id: 'overview', label: 'Overview', icon: Brain },
  { id: 'part2', label: 'ACOS Design', icon: Layers },
  { id: 'part5', label: 'Learning', icon: RotateCcw },
  { id: 'roadmap', label: 'Roadmap', icon: Route },
  { id: 'more', label: 'More', icon: MoreHorizontal },
] as const;

export function MobileBottomNav({ activeSection, onSectionChange }: MobileBottomNavProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredNavItems = useMemo(() => {
    if (!searchQuery.trim()) return navItems;
    const q = searchQuery.toLowerCase();
    return navItems.filter(
      (item) =>
        item.label.toLowerCase().includes(q) ||
        item.shortLabel.toLowerCase().includes(q) ||
        item.id.toLowerCase().includes(q)
    );
  }, [searchQuery]);

  const handleSelect = (id: string) => {
    onSectionChange(id);
    setSearchQuery('');
  };

  // Determine if a primary tab is "active"
  // The "More" tab is active when the current section is not one of the first 4 primary items
  const isMoreActive = !primaryNavItems.slice(0, 4).some((item) => item.id === activeSection);

  return (
    <>
      {/* Bottom Navigation Bar — mobile only */}
      <nav
        className="lg:hidden fixed bottom-0 left-0 right-0 z-50 bg-card/95 backdrop-blur-lg border-t border-border/30"
        style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
        aria-label="Mobile navigation"
      >
        {/* Gradient top border matching footer style */}
        <div
          className="absolute top-0 left-0 right-0 h-px pointer-events-none"
          style={{
            background:
              'linear-gradient(90deg, transparent 0%, oklch(0.696 0.17 162.48 / 0.3) 25%, oklch(0.7 0.15 180 / 0.5) 50%, oklch(0.696 0.17 162.48 / 0.3) 75%, transparent 100%)',
          }}
        />

        <div className="flex items-stretch justify-around h-14">
          {primaryNavItems.map((item) => {
            const isMore = item.id === 'more';
            const isActive = isMore ? isMoreActive : activeSection === item.id;
            const Icon = item.icon;

            return (
              <Drawer.Root
                key={item.id}
                snapPoints={[0.4, 0.85]}
                dismissible
                shouldScaleBackground
              >
                <Drawer.Trigger asChild>
                  <button
                    className={`
                      relative flex flex-col items-center justify-center flex-1
                      transition-colors duration-200 outline-none
                      focus-visible:ring-2 focus-visible:ring-emerald-500/50 focus-visible:ring-offset-1
                      ${isMore ? 'cursor-pointer' : 'cursor-pointer'}
                    `}
                    onClick={() => {
                      if (!isMore) {
                        handleSelect(item.id);
                      }
                    }}
                    aria-label={item.label}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    {/* Active indicator dot */}
                    {isActive && (
                      <motion.div
                        layoutId="mobileBottomNavIndicator"
                        className="absolute top-0.5 w-1 h-1 rounded-full bg-emerald-500"
                        transition={{ type: 'spring', stiffness: 400, damping: 30, mass: 0.6 }}
                      />
                    )}

                    <Icon
                      className={`w-5 h-5 mb-0.5 transition-colors duration-200 ${
                        isActive
                          ? 'text-emerald-500'
                          : 'text-muted-foreground'
                      }`}
                      strokeWidth={isActive ? 2.2 : 1.8}
                    />

                    <span
                      className={`text-[10px] leading-tight transition-colors duration-200 ${
                        isActive
                          ? 'text-emerald-500 font-medium'
                          : 'text-muted-foreground'
                      }`}
                    >
                      {item.label}
                    </span>
                  </button>
                </Drawer.Trigger>

                {/* "More" Drawer content */}
                {isMore && (
                  <Drawer.Portal>
                    <Drawer.Overlay className="fixed inset-0 bg-black/50 z-50" />
                    <Drawer.Content className="fixed bottom-0 left-0 right-0 z-50 bg-card/98 backdrop-blur-lg border-t border-border/30 rounded-t-xl max-h-[85vh] flex flex-col">
                      {/* Handle bar */}
                      <div className="flex justify-center pt-3 pb-2">
                        <Drawer.Handle className="w-10 h-1.5 rounded-full bg-muted-foreground/25" />
                      </div>

                      {/* Search input */}
                      <div className="px-4 pb-3">
                        <div className="relative">
                          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                          <Input
                            type="text"
                            placeholder="Search sections..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-9 h-9 bg-muted/30 border-border/30 text-sm"
                          />
                        </div>
                      </div>

                      {/* Scrollable grid of all sections */}
                      <div className="flex-1 overflow-y-auto px-4 pb-6 min-h-0">
                        <div className="grid grid-cols-3 gap-2">
                          {filteredNavItems.map((navItem) => {
                            const isItemActive = activeSection === navItem.id;
                            return (
                              <button
                                key={navItem.id}
                                onClick={() => handleSelect(navItem.id)}
                                className={`
                                  flex flex-col items-center justify-center gap-1.5 p-3 rounded-lg
                                  transition-all duration-200 outline-none
                                  focus-visible:ring-2 focus-visible:ring-emerald-500/50
                                  ${
                                    isItemActive
                                      ? 'bg-emerald-600/15 border border-emerald-500/20'
                                      : 'bg-muted/20 border border-transparent hover:bg-muted/40 hover:border-border/30'
                                  }
                                `}
                                aria-current={isItemActive ? 'page' : undefined}
                              >
                                <span
                                  className={`flex-shrink-0 ${
                                    isItemActive ? 'text-emerald-500' : 'text-muted-foreground'
                                  }`}
                                >
                                  {navItem.icon}
                                </span>
                                <span
                                  className={`text-[10px] leading-tight text-center truncate w-full ${
                                    isItemActive
                                      ? 'text-emerald-500 font-medium'
                                      : 'text-muted-foreground'
                                  }`}
                                >
                                  {navItem.shortLabel}
                                </span>
                              </button>
                            );
                          })}
                        </div>

                        {filteredNavItems.length === 0 && (
                          <div className="text-center text-muted-foreground text-sm py-8">
                            No sections found.
                          </div>
                        )}
                      </div>

                      {/* Bottom safe area spacer */}
                      <div style={{ height: 'env(safe-area-inset-bottom, 0px)' }} />
                    </Drawer.Content>
                  </Drawer.Portal>
                )}
              </Drawer.Root>
            );
          })}
        </div>
      </nav>
    </>
  );
}
