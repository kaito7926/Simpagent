export type ChatMessageRole = "system" | "user" | "assistant" | "tool";
export type ChatMessageStatus = "pending" | "completed" | "failed";

export type ChatMessage = {
  id: string;
  conversation_id: string;
  sequence_no: number;
  client_message_id: string | null;
  role: ChatMessageRole;
  status: ChatMessageStatus;
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type ConversationSummary = {
  id: string;
  owner_id: string;
  title: string | null;
  message_count: number;
  state_label: "Pending reply" | "Retry available" | null;
  created_at: string;
  updated_at: string;
};

export type ConversationDetail = ConversationSummary & {
  messages: ChatMessage[];
};

export type ConversationPage = {
  items: ConversationSummary[];
  next_cursor: string | null;
};

export type ChatMessageInput = {
  clientMessageId: string;
  content: string;
};
