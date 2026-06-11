import type { UserTurn } from "@/lib/chat-session";

type UserMessageCardProps = {
  turn: UserTurn;
};

export function UserMessageCard({ turn }: UserMessageCardProps) {
  return (
    <article className="message-card user-message-card">
      <p className="body-copy">{turn.content}</p>
    </article>
  );
}
