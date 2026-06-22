import type { UserTurn } from "@/lib/chat-session";

type UserMessageCardProps = {
  turn: UserTurn;
};

export function UserMessageCard({ turn }: UserMessageCardProps) {
  return (
    <article className="message-card message-card-user user-message-card">
      <p className="message-role">You</p>
      <p className="body-copy">{turn.content}</p>
    </article>
  );
}
