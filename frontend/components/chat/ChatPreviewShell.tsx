import Image from "next/image";
import { FlaskConical, ShieldCheck, Sparkles } from "lucide-react";

import { ActionButton } from "@/components/account-access/ActionButton";
import { StatusBadge } from "@/components/account-access/StatusBadge";
import { Card } from "@/components/ui/card";
import { MessageBubble } from "@/components/chat/MessageBubble";
import type { ChatMessage } from "@/lib/chat/tool-results";

type ChatPreviewShellProps = {
  messages: ChatMessage[];
};

export function ChatPreviewShell({ messages }: ChatPreviewShellProps) {
  return (
    <main className="app-auth-shell" style={{ padding: "24px 16px" }}>
      <div className="auth-background-glow" aria-hidden="true" />
      <div className="auth-background-glow-secondary" aria-hidden="true" />
      <section className="admin-layout" style={{ maxWidth: 1400, paddingTop: 24 }}>
        <Card className="admin-card">
          <div className="topbar-row">
            <div className="brand-row">
              <span className="inline-flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-full border border-zinc-200 bg-white shadow-sm">
                <Image alt="SimpAgent logo" height={30} src="/brand/auroraguard-logo-mark-white.png" width={30} />
              </span>
              <div className="brand-copy">
                <p className="auth-eyebrow">Next.js preview</p>
                <h1 className="page-heading">Template-aligned chat with distinct assistant and Python surfaces</h1>
              </div>
            </div>
          </div>
          <p className="body-copy max-copy">
            This preview keeps natural-language input first, gives limited Python its own reviewed card treatment, and keeps raw output secondary instead of turning the workspace into a notebook.
          </p>
          <div className="inline-actions" aria-label="Interface signals">
            <StatusBadge tone="success">Distinct Python surface</StatusBadge>
            <StatusBadge tone="warning">No Python toggle</StatusBadge>
            <StatusBadge tone="neutral">CSV · JSON · TXT · PNG</StatusBadge>
          </div>
        </Card>

        <div style={{ display: "grid", gap: 24, gridTemplateColumns: "minmax(0,1fr) minmax(280px,360px)" }}>
          <Card className="workspace-card" style={{ minHeight: "auto", padding: 24 }}>
            <div className="thread-header-inner" style={{ width: "100%" }}>
              <div className="topbar-row" style={{ alignItems: "flex-start" }}>
                <div>
                  <p className="workspace-kicker">Preview thread</p>
                  <h2 className="section-heading">Conversation timeline</h2>
                </div>
                <div className="inline-actions">
                  <span className="status-badge tone-neutral"><Sparkles size={14} strokeWidth={1.75} /> Assistant</span>
                  <span className="status-badge tone-success"><FlaskConical size={14} strokeWidth={1.75} /> Python</span>
                </div>
              </div>
            </div>
            <div className="message-thread" aria-label="Preview timeline" style={{ width: "100%", paddingInline: 0 }}>
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
            </div>
            <div className="composer-dock" style={{ paddingInline: 0, paddingBottom: 0 }}>
              <div className="composer-dock-inner" style={{ width: "100%" }}>
                <label className="composer-label" htmlFor="chat-preview-input">
                  <span className="small-label">Natural-language request</span>
                  <textarea
                    className="composer-textarea"
                    disabled
                    id="chat-preview-input"
                    placeholder="Example: Group quarterly revenue and export a CSV."
                    rows={4}
                  />
                </label>
                <div className="composer-footer">
                  <div className="composer-footer-left">
                    <p className="composer-hint">
                      The coordinator still decides whether a turn stays direct or becomes a limited Python execution.
                    </p>
                  </div>
                  <ActionButton disabled fullWidth={false} icon={<ShieldCheck size={16} strokeWidth={1.75} />}>
                    Waiting for backend orchestration
                  </ActionButton>
                </div>
              </div>
            </div>
          </Card>

          <div className="auth-context-column">
            <Card className="admin-card">
              <p className="auth-eyebrow">Reviewed limits</p>
              <h2 className="section-heading">Safe output shapes for end users</h2>
              <ul className="scope-list" style={{ gridTemplateColumns: "1fr" }}>
                <li className="scope-list-item">
                  <span className="scope-label">Summaries stay primary</span>
                  <span className="scope-code">Raw execution details are secondary by default.</span>
                </li>
                <li className="scope-list-item">
                  <span className="scope-label">Artifacts stay reviewed</span>
                  <span className="scope-code">Only approved file types appear as downloads.</span>
                </li>
                <li className="scope-list-item">
                  <span className="scope-label">No notebook chrome</span>
                  <span className="scope-code">There is no shell, notebook, or file browser surface.</span>
                </li>
              </ul>
            </Card>
          </div>
        </div>
      </section>
    </main>
  );
}
