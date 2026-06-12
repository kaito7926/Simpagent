import React, { useMemo, useState } from "react";
import { MessageSquarePlus } from "lucide-react";

import type { ConversationSummary } from "@/lib/chat-types";

import { ConversationMenu } from "./ConversationMenu";

export type ChatNavigationProps = {
  conversations: ConversationSummary[];
  activeConversationId: string | null;
  currentUserEmail: string;
  nextCursor: string | null;
  loading: boolean;
  loadingMore: boolean;
  deletingConversationId: string | null;
  onNewChat: () => void;
  onSelectConversation: (conversationId: string) => void;
  onLoadMore: () => void;
  onDeleteConversation: (conversationId: string) => void | Promise<void>;
  onSignOut: () => void | Promise<void>;
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
  if (diffDays <= 0) {
    return "Today";
  }
  if (diffDays === 1) {
    return "Yesterday";
  }
  if (diffDays <= 7) {
    return "Previous 7 Days";
  }
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

export function ChatSidebar({
  conversations,
  activeConversationId,
  currentUserEmail,
  nextCursor,
  loading,
  loadingMore,
  deletingConversationId,
  onNewChat,
  onSelectConversation,
  onLoadMore,
  onDeleteConversation,
  onSignOut,
}: ChatNavigationProps) {
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const groups = useMemo(() => groupConversations(conversations), [conversations]);

  return (
    <div className="conversation-navigation-inner">
      <div className="workspace-brand-row">
        <span className="workspace-brand-mark" aria-hidden="true">
          S
        </span>
        <span>SimpAgent</span>
      </div>
      <button className="new-chat-button" type="button" onClick={onNewChat}>
        <MessageSquarePlus aria-hidden="true" size={18} strokeWidth={1.75} />
        <span>New chat</span>
      </button>
      <div className="conversation-list-region">
        <p className="conversation-list-label">Conversations</p>
        {loading ? (
          <p className="conversation-empty" role="status">
            Loading conversations...
          </p>
        ) : conversations.length === 0 ? (
          <div className="conversation-empty">
            <p>No conversations yet</p>
            <span>Your first message will create a conversation here.</span>
          </div>
        ) : (
          <div className="conversation-groups">
            {groups.map((group) => (
              <section className="conversation-group" key={group.label} aria-label={group.label}>
                <h2>{group.label}</h2>
                <ul className="conversation-list">
                  {group.items.map((conversation) => (
                    <li className="conversation-list-item" key={conversation.id}>
                      <button
                        className={`conversation-row ${
                          activeConversationId === conversation.id ? "conversation-row-active" : ""
                        }`}
                        type="button"
                        onClick={() => onSelectConversation(conversation.id)}
                      >
                        <span>{conversation.title ?? "New chat"}</span>
                        <small>
                          {conversation.state_label ??
                            `${conversation.message_count} ${
                              conversation.message_count === 1 ? "message" : "messages"
                            }`}
                        </small>
                      </button>
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
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        )}
        {nextCursor ? (
          <button
            className="load-more-button"
            type="button"
            disabled={loadingMore}
            onClick={onLoadMore}
          >
            {loadingMore ? "Loading conversations..." : "Load more conversations"}
          </button>
        ) : null}
      </div>
      <div className="workspace-account">
        <div>
          <span className="account-email">{currentUserEmail}</span>
          <span className="account-state">Protected session</span>
        </div>
        <button type="button" onClick={() => void onSignOut()}>
          Sign out
        </button>
      </div>
    </div>
  );
}
