import type { AuthSessionController } from "@/lib/auth-session";
import type {
  ChatMessageInput,
  ConversationDetail,
  ConversationPage,
} from "@/lib/chat-types";

const JSON_HEADERS = {
  "Content-Type": "application/json",
};

export function listConversations(
  controller: AuthSessionController,
  options: { limit?: number; cursor?: string | null } = {},
): Promise<ConversationPage> {
  const limit = options.limit ?? 20;
  const params = new URLSearchParams({ limit: String(limit) });
  if (options.cursor) {
    params.set("cursor", options.cursor);
  }

  return controller.authorizedJson<ConversationPage>(`/api/conversations?${params.toString()}`, {
    method: "GET",
  });
}

export function getConversation(
  controller: AuthSessionController,
  conversationId: string,
): Promise<ConversationDetail> {
  return controller.authorizedJson<ConversationDetail>(
    `/api/conversations/${encodeURIComponent(conversationId)}`,
    { method: "GET" },
  );
}

export function createConversationWithMessage(
  controller: AuthSessionController,
  input: ChatMessageInput,
): Promise<ConversationDetail> {
  return controller.authorizedJson<ConversationDetail>("/api/conversations", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({
      initial_message: {
        client_message_id: input.clientMessageId,
        content: input.content,
      },
    }),
  });
}

export function sendMessage(
  controller: AuthSessionController,
  conversationId: string,
  input: ChatMessageInput,
): Promise<ConversationDetail> {
  return controller.authorizedJson<ConversationDetail>(
    `/api/conversations/${encodeURIComponent(conversationId)}/messages`,
    {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify({
        client_message_id: input.clientMessageId,
        content: input.content,
      }),
    },
  );
}

export function retryMessage(
  controller: AuthSessionController,
  conversationId: string,
  clientMessageId: string,
): Promise<ConversationDetail> {
  return controller.authorizedJson<ConversationDetail>(
    `/api/conversations/${encodeURIComponent(conversationId)}/messages/${encodeURIComponent(clientMessageId)}/retry`,
    { method: "POST" },
  );
}
