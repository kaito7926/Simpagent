import React, { useMemo, useState } from "react";
import Image from "next/image";
import {
  ChevronDown,
  ChevronRight,
  Clock3,
  MessageSquarePlus,
  PanelLeftClose,
  Search,
  Settings2,
  Shield,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
} from "lucide-react";

import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

import type { ConversationSummary } from "@/lib/chat-types";

import { ConversationMenu } from "./ConversationMenu";

export type AppWorkspaceView =
  | "chat"
  | "overview"
  | "users"
  | "security-events"
  | "tool-executions"
  | "gateway-evidence"
  | "orchestration"
  | "settings";

export type ChatNavigationProps = {
  conversations: ConversationSummary[];
  activeConversationId: string | null;
  currentUserEmail: string;
  nextCursor: string | null;
  loading: boolean;
  loadingMore: boolean;
  deletingConversationId: string | null;
  adminCanRead: boolean;
  adminError: string | null;
  now?: Date;
  collapsed?: boolean;
  currentView?: AppWorkspaceView;
  onNewChat: () => void;
  onSelectConversation: (conversationId: string) => void;
  onSelectView?: (view: AppWorkspaceView) => void;
  onLoadMore: () => void;
  onDeleteConversation: (conversationId: string) => void | Promise<void>;
  onSignOut: () => void | Promise<void>;
  onToggleCollapse?: () => void;
};

export type ConversationGroup = {
  label: "Today" | "Yesterday" | "Previous 7 Days" | "Older";
  items: ConversationSummary[];
};

const DAY_MS = 24 * 60 * 60 * 1000;

function startOfDay(value: Date): Date {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}

function groupLabel(updatedAt: string, now: Date): ConversationGroup["label"] {
  const updated = startOfDay(new Date(updatedAt));
  const today = startOfDay(now);
  const diffDays = Math.floor((today.getTime() - updated.getTime()) / DAY_MS);
  if (diffDays <= 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays <= 7) return "Previous 7 Days";
  return "Older";
}

export function groupConversations(
  conversations: ConversationSummary[],
  now = new Date(),
): ConversationGroup[] {
  const buckets: ConversationGroup[] = [
    { label: "Today", items: [] },
    { label: "Yesterday", items: [] },
    { label: "Previous 7 Days", items: [] },
    { label: "Older", items: [] },
  ];
  const sorted = [...conversations].sort((left, right) =>
    right.updated_at.localeCompare(left.updated_at),
  );
  for (const conversation of sorted) {
    const label = groupLabel(conversation.updated_at, now);
    buckets.find((bucket) => bucket.label === label)?.items.push(conversation);
  }
  return buckets.filter((bucket) => bucket.items.length > 0);
}

const ADMIN_ITEMS: Array<{ id: AppWorkspaceView; label: string; icon: React.ReactNode }> = [
  { id: "overview", label: "Overview", icon: <Sparkles size={14} strokeWidth={1.75} /> },
  { id: "users", label: "Users", icon: <Shield size={14} strokeWidth={1.75} /> },
  { id: "security-events", label: "Security events", icon: <ShieldCheck size={14} strokeWidth={1.75} /> },
  { id: "tool-executions", label: "Tool executions", icon: <Search size={14} strokeWidth={1.75} /> },
  { id: "gateway-evidence", label: "Gateway evidence", icon: <Shield size={14} strokeWidth={1.75} /> },
  { id: "orchestration", label: "Orchestration", icon: <SlidersHorizontal size={14} strokeWidth={1.75} /> },
];

function SectionHeader(props: {
  title: string;
  icon: React.ReactNode;
  collapsed: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      aria-expanded={!props.collapsed}
      className="group flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-xs font-semibold tracking-wider text-zinc-500 hover:text-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-zinc-400 dark:hover:text-zinc-200"
      onClick={props.onToggle}
      type="button"
    >
      <div className="flex items-center gap-2">
        <span className="text-zinc-400 dark:text-zinc-500" aria-hidden="true">{props.icon}</span>
        {props.title}
      </div>
      <span aria-hidden="true">
        {props.collapsed ? (
          <ChevronRight className="h-3.5 w-3.5 text-zinc-400 dark:text-zinc-500" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5 text-zinc-400 dark:text-zinc-500" />
        )}
      </span>
    </button>
  );
}

function EmptyConversationPanel(props: { title: string; body: string }) {
  return (
    <div className="select-none rounded-lg border border-dashed border-zinc-200 px-3 py-3 text-center text-xs text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
      <p className="mb-1 font-medium text-zinc-700 dark:text-zinc-300">{props.title}</p>
      <span>{props.body}</span>
    </div>
  );
}

export function ChatSidebar({
  conversations,
  activeConversationId,
  currentUserEmail,
  nextCursor,
  loading,
  loadingMore,
  deletingConversationId,
  adminCanRead,
  adminError,
  now,
  collapsed = false,
  currentView = "chat",
  onNewChat,
  onSelectConversation,
  onSelectView,
  onLoadMore,
  onDeleteConversation,
  onSignOut,
  onToggleCollapse,
}: ChatNavigationProps) {
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [chatSectionCollapsed, setChatSectionCollapsed] = useState(false);
  const [adminSectionCollapsed, setAdminSectionCollapsed] = useState(false);
  const groups = useMemo(() => groupConversations(conversations, now), [conversations, now]);

  const filteredGroups = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return groups;
    return groups
      .map((group) => ({
        ...group,
        items: group.items.filter((conversation) => {
          const title = (conversation.title ?? "New chat").toLowerCase();
          const subtitle = (conversation.state_label ?? `${conversation.message_count} messages`).toLowerCase();
          return title.includes(normalized) || subtitle.includes(normalized);
        }),
      }))
      .filter((group) => group.items.length > 0);
  }, [groups, query]);

  if (collapsed) {
    return (
      <aside className="z-50 flex h-full w-16 shrink-0 flex-col border-r border-zinc-200/60 bg-white transition-all duration-300 dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex items-center justify-center border-b border-zinc-200/60 px-3 py-3 dark:border-zinc-800">
          <button
            onClick={onToggleCollapse}
            className="rounded-xl p-2 hover:bg-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:hover:bg-zinc-800"
            aria-label="Open sidebar"
          >
            <PanelLeftClose className="h-5 w-5 rotate-180" />
          </button>
        </div>

        <div className="flex flex-1 flex-col items-center gap-2 pt-4">
          <button
            onClick={onNewChat}
            className="rounded-xl p-2.5 hover:bg-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:hover:bg-zinc-800 transition-colors"
            title="New Chat"
          >
            <MessageSquarePlus className="h-5 w-5" />
          </button>

          <button
            onClick={() => onSelectView?.("settings")}
            className={cn(
              "rounded-xl p-2.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
              currentView === "settings"
                ? "bg-blue-50 text-blue-900 dark:bg-blue-500/10 dark:text-blue-100"
                : "hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300",
            )}
            title="Settings"
          >
            <Settings2 className="h-5 w-5" />
          </button>
        </div>
      </aside>
    );
  }

  return (
    <aside className="z-50 flex h-full w-80 shrink-0 flex-col border-r border-zinc-200/60 bg-white transition-all duration-300 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-center gap-2 border-b border-zinc-200/60 px-3 py-3 dark:border-zinc-800">
        <div className="flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center overflow-hidden rounded-full border border-zinc-200 bg-white shadow-sm dark:border-zinc-700">
            <Image alt="SimpAgent mark" height={22} src="/brand/auroraguard-logo-mark-white.png" width={22} />
          </div>
          <div className="text-sm font-semibold tracking-tight min-w-0 ui-safe-inline">SimpAgent</div>
        </div>
        <div className="ml-auto flex items-center gap-1">
          {onToggleCollapse ? (
            <button
              onClick={onToggleCollapse}
              className="hidden md:block rounded-xl p-2 hover:bg-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:hover:bg-zinc-800"
              aria-label="Close sidebar"
            >
              <PanelLeftClose className="h-5 w-5" />
            </button>
          ) : null}
        </div>
      </div>

      <div className="px-3 pt-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search…"
            className="w-full rounded-full border border-zinc-200 bg-white py-2 pl-9 pr-3 text-sm outline-none ring-0 placeholder:text-zinc-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 dark:border-zinc-800 dark:bg-zinc-950/50"
          />
        </div>
      </div>

      <div className="px-3 pt-3">
        <button
          onClick={() => {
            onSelectView?.("chat");
            onNewChat();
          }}
          className="flex w-full items-center justify-center gap-2 rounded-full bg-zinc-900 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-zinc-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:bg-white dark:text-zinc-900"
        >
          <MessageSquarePlus className="h-4 w-4" /> Start New Chat
        </button>
      </div>

      <ScrollArea className="mt-4 flex min-h-0 flex-1 flex-col gap-4 px-2 pb-4">
        <div className="mb-4">
          <SectionHeader
            collapsed={chatSectionCollapsed}
            icon={<Clock3 className="h-3.5 w-3.5" />}
            onToggle={() => setChatSectionCollapsed((curr) => !curr)}
            title="RECENT"
          />
          {!chatSectionCollapsed ? (
            loading ? (
              <p className="text-sm text-center text-zinc-500 mt-4">Loading conversations...</p>
            ) : filteredGroups.length === 0 ? (
              <div className="mt-1 space-y-0.5">
                <EmptyConversationPanel title="No conversations yet" body="Start a new chat to begin." />
              </div>
            ) : (
              filteredGroups.map((group) => (
                <div key={group.label} className="mt-1 space-y-0.5">
                  <div className="px-2 py-1 text-[11px] font-medium text-zinc-400">{group.label.toUpperCase()}</div>
                  {group.items.map((conversation) => (
                    <div key={conversation.id} className="relative flex items-center">
                      <button
                        onClick={() => {
                          onSelectView?.("chat");
                          onSelectConversation(conversation.id);
                        }}
                        className={cn(
                          "group relative flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
                          activeConversationId === conversation.id && currentView === "chat"
                            ? "bg-blue-50 text-blue-900 dark:bg-blue-500/10 dark:text-blue-100"
                            : "text-zinc-700 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800/50",
                        )}
                      >
                        <span className="truncate flex-1 min-w-0 text-left">{conversation.title ?? "New chat"}</span>
                        <span className="sr-only">{conversation.state_label ?? `${conversation.message_count} messages`}</span>
                      </button>
                      <div className="absolute right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <ConversationMenu
                          conversationTitle={conversation.title}
                          open={openMenuId === conversation.id}
                          confirming={openMenuId === conversation.id}
                          deleting={deletingConversationId === conversation.id}
                          onOpenChange={(open) => setOpenMenuId(open ? conversation.id : null)}
                          onDelete={async () => {
                            await onDeleteConversation(conversation.id);
                            setOpenMenuId(null);
                          }}
                          onKeep={() => setOpenMenuId(null)}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              ))
            )
          ) : null}
        </div>

        {nextCursor ? (
          <button
            onClick={onLoadMore}
            disabled={loadingMore}
            className="w-full rounded-lg px-2 py-2 text-sm text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800"
          >
            {loadingMore ? "Loading..." : "Load more conversations"}
          </button>
        ) : null}

        {adminCanRead ? (
          <div className="mt-4">
            <SectionHeader
              collapsed={adminSectionCollapsed}
              icon={<ShieldCheck className="h-3.5 w-3.5" />}
              onToggle={() => setAdminSectionCollapsed((curr) => !curr)}
              title="ADMIN"
            />
            {!adminSectionCollapsed ? (
              <div className="mt-1 space-y-0.5">
                {ADMIN_ITEMS.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => onSelectView?.(item.id)}
                    className={cn(
                      "group relative flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
                      currentView === item.id
                        ? "bg-blue-50 text-blue-900 dark:bg-blue-500/10 dark:text-blue-100"
                        : "text-zinc-700 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800/50",
                    )}
                  >
                    <span className={cn("text-zinc-400", currentView === item.id && "text-blue-500")}>{item.icon}</span>
                    <span>{item.label}</span>
                  </button>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
      </ScrollArea>

      <div className="mt-auto border-t border-zinc-200/60 px-3 py-3 dark:border-zinc-800">
        {adminError ? (
          <p className="mb-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-900 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-100">
            {adminError}
          </p>
        ) : null}
        <div className="flex items-center gap-2">
          <button
            onClick={() => onSelectView?.("settings")}
            className={cn(
              "inline-flex items-center gap-2 rounded-lg px-2 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
              currentView === "settings"
                ? "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100 font-medium"
                : "text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-800 dark:hover:text-zinc-100",
            )}
          >
            <Settings2 className="h-4 w-4" /> Settings
          </button>
        </div>
        <div className="mt-2 flex items-center gap-2 rounded-xl bg-zinc-50 p-2 dark:bg-zinc-800/60">
          <div className="grid h-8 w-8 place-items-center rounded-full bg-zinc-900 text-xs font-bold text-white dark:bg-white dark:text-zinc-900">
            {currentUserEmail.charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium">{currentUserEmail}</div>
            <div className="truncate text-xs text-zinc-500 dark:text-zinc-400">Protected session</div>
          </div>
          <button
            onClick={() => void onSignOut()}
            className="text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 px-2"
          >
            Sign out
          </button>
        </div>
      </div>
    </aside>
  );
}
