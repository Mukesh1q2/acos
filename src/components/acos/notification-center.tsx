"use client";

import {
  useEffect,
  useCallback,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bell,
  Info,
  CheckCircle,
  AlertTriangle,
  Trophy,
  CheckCheck,
  Trash2,
} from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { navItems } from "@/components/acos/sidebar";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export type NotificationType = "info" | "success" | "warning" | "achievement";

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: number;
  read: boolean;
  sectionId?: string;
}

/* ------------------------------------------------------------------ */
/*  localStorage helpers                                               */
/* ------------------------------------------------------------------ */

const STORAGE_KEY = "acos-notifications";
const MAX_NOTIFICATIONS = 50;

function readNotifications(): Notification[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeNotifications(notifications: Notification[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(notifications));
  } catch {
    // Silently fail if localStorage is unavailable
  }
}

/* ------------------------------------------------------------------ */
/*  External store for cross-component reactivity                      */
/* ------------------------------------------------------------------ */

let listeners: Array<() => void> = [];
let cachedNotifications: Notification[] | null = null;
const EMPTY_NOTIFICATIONS: Notification[] = [];

// Track auto-dismiss timers
const dismissTimers: Map<string, ReturnType<typeof setTimeout>> = new Map();

function getSnapshot(): Notification[] {
  if (cachedNotifications === null) {
    cachedNotifications = readNotifications();
  }
  return cachedNotifications;
}

function getServerSnapshot(): Notification[] {
  return EMPTY_NOTIFICATIONS;
}

function setNotificationState(newNotifications: Notification[]) {
  cachedNotifications = newNotifications;
  writeNotifications(newNotifications);
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void): () => void {
  listeners = [...listeners, listener];
  return () => {
    listeners = listeners.filter((l) => l !== listener);
  };
}

/* ------------------------------------------------------------------ */
/*  Auto-dismiss for info/success types                                */
/* ------------------------------------------------------------------ */

function scheduleAutoDismiss(id: string, type: NotificationType) {
  // Only auto-dismiss info and success after 10s
  if (type !== "info" && type !== "success") return;

  // Clear existing timer if any
  const existing = dismissTimers.get(id);
  if (existing) clearTimeout(existing);

  const timer = setTimeout(() => {
    const current = getSnapshot();
    const filtered = current.filter((n) => n.id !== id);
    if (filtered.length !== current.length) {
      setNotificationState(filtered);
    }
    dismissTimers.delete(id);
  }, 10000);

  dismissTimers.set(id, timer);
}

/* ------------------------------------------------------------------ */
/*  Relative time helper                                               */
/* ------------------------------------------------------------------ */

function formatRelativeTime(timestamp: number): string {
  const now = Date.now();
  const diffMs = now - timestamp;

  if (diffMs < 60 * 1000) return "just now";

  const diffMinutes = Math.floor(diffMs / (60 * 1000));
  if (diffMinutes < 60) return `${diffMinutes}m ago`;

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

/* ------------------------------------------------------------------ */
/*  Icon helper by type                                                */
/* ------------------------------------------------------------------ */

function getNotificationIcon(type: NotificationType): ReactNode {
  switch (type) {
    case "info":
      return <Info className="w-4 h-4 text-sky-400" />;
    case "success":
      return <CheckCircle className="w-4 h-4 text-emerald-400" />;
    case "warning":
      return <AlertTriangle className="w-4 h-4 text-amber-400" />;
    case "achievement":
      return <Trophy className="w-4 h-4 text-yellow-400" />;
  }
}

/* ------------------------------------------------------------------ */
/*  Public API functions                                               */
/* ------------------------------------------------------------------ */

export function addNotification(
  notif: Omit<Notification, "id" | "timestamp" | "read">
) {
  const current = getSnapshot();
  const newNotif: Notification = {
    ...notif,
    id: crypto.randomUUID(),
    timestamp: Date.now(),
    read: false,
  };

  // Add to front, limit to MAX_NOTIFICATIONS
  const updated = [newNotif, ...current].slice(0, MAX_NOTIFICATIONS);
  setNotificationState(updated);

  // Schedule auto-dismiss for info/success
  scheduleAutoDismiss(newNotif.id, notif.type);
}

export function markAsRead(id: string) {
  const current = getSnapshot();
  const updated = current.map((n) =>
    n.id === id ? { ...n, read: true } : n
  );
  setNotificationState(updated);
}

export function markAllRead() {
  const current = getSnapshot();
  const updated = current.map((n) => ({ ...n, read: true }));
  setNotificationState(updated);
}

export function clearAll() {
  setNotificationState([]);
  // Clear all dismiss timers
  dismissTimers.forEach((timer) => clearTimeout(timer));
  dismissTimers.clear();
}

/* ------------------------------------------------------------------ */
/*  Hook: useNotifications                                             */
/* ------------------------------------------------------------------ */

export function useNotifications() {
  const notifications = useSyncExternalStore(
    subscribe,
    getSnapshot,
    getServerSnapshot
  );

  const unreadCount = notifications.filter((n) => !n.read).length;

  return { notifications, unreadCount };
}

/* ------------------------------------------------------------------ */
/*  Provider (listens for storage events from other tabs)              */
/* ------------------------------------------------------------------ */

export function NotificationProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    const handleStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) {
        cachedNotifications = null; // Invalidate cache
        listeners.forEach((l) => l());
      }
    };
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  return <>{children}</>;
}

/* ------------------------------------------------------------------ */
/*  NotificationCenter Component                                       */
/* ------------------------------------------------------------------ */

export function NotificationCenter({
  onNavigate,
}: {
  onNavigate?: (sectionId: string) => void;
}) {
  const { notifications, unreadCount } = useNotifications();

  const handleNotificationClick = useCallback(
    (notif: Notification) => {
      if (!notif.read) {
        markAsRead(notif.id);
      }
      if (notif.sectionId && onNavigate) {
        onNavigate(notif.sectionId);
      }
    },
    [onNavigate]
  );

  const handleMarkAllRead = useCallback(() => {
    markAllRead();
  }, []);

  const handleClearAll = useCallback(() => {
    clearAll();
  }, []);

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          className="relative flex items-center justify-center w-8 h-8 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-all duration-200"
          aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
        >
          <Bell className="w-4 h-4" />
          {unreadCount > 0 && (
            <motion.span
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="absolute -top-1 -right-1 flex items-center justify-center min-w-[16px] h-4 px-1 rounded-full bg-emerald-500 text-[9px] font-bold text-white shadow-sm"
            >
              {unreadCount > 9 ? "9+" : unreadCount}
            </motion.span>
          )}
        </button>
      </PopoverTrigger>
      <PopoverContent
        align="end"
        className="w-80 p-0 bg-popover border-border/40 shadow-xl"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border/20">
          <div className="flex items-center gap-2">
            <Bell className="w-4 h-4 text-emerald-400" />
            <h4 className="text-sm font-semibold text-foreground">
              Notifications
            </h4>
            {unreadCount > 0 && (
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded-full">
                {unreadCount}
              </span>
            )}
          </div>
          {notifications.length > 0 && (
            <div className="flex items-center gap-1">
              <button
                onClick={handleMarkAllRead}
                className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-emerald-400 transition-colors duration-200 px-1.5 py-1 rounded hover:bg-muted/30"
                aria-label="Mark all notifications as read"
              >
                <CheckCheck className="w-3 h-3" />
                <span>Mark all read</span>
              </button>
              <button
                onClick={handleClearAll}
                className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-red-400 transition-colors duration-200 px-1.5 py-1 rounded hover:bg-muted/30"
                aria-label="Clear all notifications"
              >
                <Trash2 className="w-3 h-3" />
                <span>Clear all</span>
              </button>
            </div>
          )}
        </div>

        {/* Notification list */}
        <div className="max-h-80 overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <Bell className="w-8 h-8 text-muted-foreground/20 mb-3" />
              <p className="text-xs text-muted-foreground">
                No notifications yet
              </p>
              <p className="text-[10px] text-muted-foreground/60 mt-1">
                Stay tuned for updates and achievements
              </p>
            </div>
          ) : (
            <AnimatePresence initial={false}>
              {notifications.map((notif) => {
                const navItem = notif.sectionId
                  ? navItems.find((n) => n.id === notif.sectionId)
                  : null;
                return (
                  <motion.div
                    key={notif.id}
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2 }}
                    className={`
                      group flex items-start gap-3 px-4 py-3 border-b border-border/10 last:border-b-0
                      cursor-pointer transition-colors duration-150
                      ${
                        notif.read
                          ? "bg-transparent opacity-60"
                          : "bg-emerald-500/5 border-l-2 border-l-emerald-500"
                      }
                      hover:bg-muted/20
                    `}
                    onClick={() => handleNotificationClick(notif)}
                  >
                    <div className="flex-shrink-0 mt-0.5">
                      {getNotificationIcon(notif.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-xs font-medium ${
                            notif.read ? "text-muted-foreground" : "text-foreground"
                          }`}
                        >
                          {notif.title}
                        </span>
                        {notif.type === "achievement" && (
                          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-full bg-yellow-500/15 text-yellow-400 border border-yellow-500/20">
                            ACHIEVEMENT
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-muted-foreground mt-0.5 leading-relaxed line-clamp-2">
                        {notif.message}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[9px] text-muted-foreground/60">
                          {formatRelativeTime(notif.timestamp)}
                        </span>
                        {navItem && (
                          <span className="text-[9px] text-emerald-400/80 flex items-center gap-0.5">
                            {navItem.icon}
                            <span>{navItem.shortLabel}</span>
                          </span>
                        )}
                      </div>
                    </div>
                    {!notif.read && (
                      <div className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0 mt-1.5" />
                    )}
                  </motion.div>
                );
              })}
            </AnimatePresence>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
