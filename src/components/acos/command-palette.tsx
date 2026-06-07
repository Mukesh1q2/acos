"use client";

import { useEffect, useState, useCallback } from "react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { navItems } from "@/components/acos/sidebar";
import { Keyboard } from "lucide-react";

interface CommandPaletteProps {
  onSectionChange: (id: string) => void;
}

export function CommandPalette({ onSectionChange }: CommandPaletteProps) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const runCommand = useCallback(
    (command: () => void) => {
      setOpen(false);
      command();
    },
    []
  );

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Search sections..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Navigation">
          {navItems.map((item, i) => (
            <CommandItem
              key={item.id}
              onSelect={() => runCommand(() => onSectionChange(item.id))}
            >
              <span className="text-muted-foreground">{item.icon}</span>
              <span>{item.label}</span>
              <span className="ml-auto text-xs text-muted-foreground font-mono">
                {i + 1 <= 9 ? `${i + 1}` : ""}
              </span>
            </CommandItem>
          ))}
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Keyboard Shortcuts">
          <CommandItem disabled>
            <Keyboard className="w-4 h-4" />
            <span>Toggle Command Palette</span>
            <span className="ml-auto text-xs text-muted-foreground font-mono">
              Ctrl+K
            </span>
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
