"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Keyboard } from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Shortcut definitions                                               */
/* ------------------------------------------------------------------ */

interface ShortcutDef {
  keys: string[];
  description: string;
}

interface ShortcutGroup {
  category: string;
  shortcuts: ShortcutDef[];
}

const shortcutGroups: ShortcutGroup[] = [
  {
    category: "Navigation",
    shortcuts: [
      {
        keys: ["Ctrl", "K"],
        description: "Open Command Palette",
      },
      {
        keys: ["Alt", "Arrow Down"],
        description: "Next Section",
      },
      {
        keys: ["Alt", "Arrow Up"],
        description: "Previous Section",
      },
    ],
  },
  {
    category: "Actions",
    shortcuts: [
      {
        keys: ["Ctrl", "Shift", "B"],
        description: "Toggle Bookmark",
      },
      {
        keys: ["Ctrl", "Shift", "E"],
        description: "Export Current Section",
      },
    ],
  },
  {
    category: "Help",
    shortcuts: [
      {
        keys: ["?"],
        description: "Show Keyboard Shortcuts",
      },
      {
        keys: ["Escape"],
        description: "Close Modal/Panel",
      },
    ],
  },
];

/* ------------------------------------------------------------------ */
/*  Kbd badge component                                                */
/* ------------------------------------------------------------------ */

function KbdBadge({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="px-2 py-1 rounded bg-muted/40 border border-border/30 font-mono text-xs">
      {children}
    </kbd>
  );
}

/* ------------------------------------------------------------------ */
/*  KeyboardShortcuts component                                        */
/* ------------------------------------------------------------------ */

export function KeyboardShortcuts() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only trigger on "?" key
      if (e.key !== "?") return;

      // Do not trigger if user is typing in an input/textarea
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      ) {
        return;
      }

      e.preventDefault();
      setOpen((prev) => !prev);
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Keyboard className="w-5 h-5 text-emerald-400" />
            Keyboard Shortcuts
          </DialogTitle>
          <DialogDescription>
            Use these shortcuts to navigate and interact with ACOS more efficiently.
          </DialogDescription>
        </DialogHeader>

        <div className="mt-2 space-y-5">
          {shortcutGroups.map((group) => (
            <div key={group.category}>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-emerald-400 mb-3">
                {group.category}
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                {group.shortcuts.map((shortcut) => (
                  <div
                    key={shortcut.description}
                    className="flex items-center justify-between gap-2 px-3 py-2 rounded-md bg-muted/20 hover:bg-muted/30 transition-colors"
                  >
                    <span className="text-xs text-foreground/80 truncate">
                      {shortcut.description}
                    </span>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      {shortcut.keys.map((key, i) => (
                        <span key={key} className="flex items-center gap-1">
                          {i > 0 && (
                            <span className="text-muted-foreground text-[10px]">+</span>
                          )}
                          <KbdBadge>{key}</KbdBadge>
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
