import { ApiError, requestJson } from "@/lib/api";

export type ChatMode = "direct" | "search";
export type ChatRequestMode = ChatMode;
export type SearchResponseState =
  | "grounded"
  | "missing_grounding"
  | "denied"
  | "search_unavailable"
  | "provider_failed"
  | "timeout";

export type AssistantTurnState = "direct" | SearchResponseState;

type TransportMode = "direct_chat" | "google_search";

type SearchTransportState =
  | "grounded"
  | "missing_grounding"
  | "denied"
  | "search_unavailable"
  | "provider_failed"
  | "timeout";

type TransportSearchSource = {
  index: number;
  title: string;
  domain: string;
  uri: string | null;
};

type TransportSearchCitation = {
  index: number;
  source_index: number;
  start: number | null;
  end: number | null;
};

type TransportSearchSuggestions = {
  trusted: boolean;
  items: string[];
} | null;

type TransportSearchTurn = {
  mode: "google_search";
  state: SearchTransportState;
  google_grounded: boolean;
  tool_executed: boolean;
  correlation_id: string | null;
  sources: TransportSearchSource[];
  citations: TransportSearchCitation[];
  suggestions: TransportSearchSuggestions;
  retry_of_message_id: string | null;
};

type TransportMessage = {
  id: string;
  conversation_id: string;
  sequence_no: number;
  role: "user" | "assistant" | "tool";
  content: string;
  created_at: string;
  search: TransportSearchTurn | null;
};

type SubmitTurnTransportResponse = {
  conversation_id: string;
  mode: TransportMode;
  user_message: TransportMessage;
  assistant_message: TransportMessage;
  tool_execution: {
    id: string;
    tool_name: string;
    status: string;
    correlation_id: string | null;
    duration_ms: number | null;
  } | null;
};

export type SearchSource = {
  id: string;
  title: string;
  url: string;
  domain: string;
};

export type CitationReference = {
  id: string;
  source_id: string;
  marker: number;
  label: string;
  start?: number;
  end?: number;
};

export type SearchSuggestion = {
  id: string;
  label: string;
  query: string;
};

export type UserTurn = {
  id: string;
  role: "user";
  mode: ChatMode;
  content: string;
};

export type AssistantTurn = {
  id: string;
  role: "assistant";
  mode: ChatMode;
  state: AssistantTurnState;
  answer: string | null;
  citations: CitationReference[];
  sources: SearchSource[];
  suggestions: SearchSuggestion[];
  correlationId?: string | null;
};

export type ChatTurn = UserTurn | AssistantTurn;

export type ChatResponseEnvelope = {
  request_mode: ChatRequestMode;
  response_state: AssistantTurnState;
  turn_id: string;
  answer_markdown: string | null;
  citations: CitationReference[];
  sources: SearchSource[];
  suggestions: SearchSuggestion[];
  correlation_id?: string | null;
};

export type ChatTurnRequest = {
  mode: ChatRequestMode;
  prompt: string;
  retryOfMessageId?: string | null;
};

export type ChatSessionSnapshot = {
  conversationId: string;
  mode: ChatMode;
  draft: string;
  turns: ChatTurn[];
  isPending: boolean;
  activeRetryId: string | null;
  submitLabel: string;
  announcement: string | null;
  errorMessage: string | null;
};

type SendTurn = (request: ChatTurnRequest) => Promise<ChatResponseEnvelope>;
type JsonRequester = <T>(input: string, init: RequestInit) => Promise<T>;

export type ChatSessionDependencies = {
  conversationId?: string;
  fetchImpl?: typeof fetch;
  sendTurn?: SendTurn;
};

const DEFAULT_CONVERSATION_ID = "00000000-0000-0000-0000-000000000001";

function createConversationId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return DEFAULT_CONVERSATION_ID;
}

function toTransportMode(mode: ChatMode): TransportMode {
  return mode === "search" ? "google_search" : "direct_chat";
}

function fromTransportMode(mode: TransportMode): ChatMode {
  return mode === "google_search" ? "search" : "direct";
}

function defaultSubmitLabel(mode: ChatMode, pending: boolean): string {
  if (pending) {
    return mode === "search" ? "Đang tìm bằng Google..." : "Đang gửi...";
  }

  return mode === "search" ? "Tìm bằng Google" : "Gửi câu hỏi";
}

function normalizeSearchPayload(
  messageId: string,
  search: TransportSearchTurn | null,
  answerMarkdown: string,
): ChatResponseEnvelope {
  if (!search) {
    return {
      request_mode: "direct",
      response_state: "direct",
      turn_id: messageId,
      answer_markdown: answerMarkdown,
      citations: [],
      sources: [],
      suggestions: [],
      correlation_id: null,
    };
  }

  const sources = search.sources.map((source) => ({
    id: `${messageId}-source-${source.index}`,
    title: source.title,
    domain: source.domain,
    url: source.uri ?? "#",
  }));

  const citations = search.citations.map((citation) => ({
    id: `${messageId}-citation-${citation.index}`,
    source_id: `${messageId}-source-${citation.source_index}`,
    marker: citation.index,
    label: `Nguồn ${citation.index}`,
    start: citation.start ?? undefined,
    end: citation.end ?? undefined,
  }));

  const suggestions = search.suggestions?.trusted
    ? search.suggestions.items.map((item, index) => ({
        id: `${messageId}-suggestion-${index + 1}`,
        label: item,
        query: item,
      }))
    : [];

  return {
    request_mode: "search",
    response_state: search.state,
    turn_id: messageId,
    answer_markdown: answerMarkdown,
    citations,
    sources,
    suggestions,
    correlation_id: search.correlation_id,
  };
}

function toAssistantTurn(response: ChatResponseEnvelope, originalMode: ChatMode): AssistantTurn {
  return {
    id: response.turn_id,
    role: "assistant",
    mode: response.request_mode,
    state: response.response_state,
    answer: response.answer_markdown,
    citations: response.citations,
    sources: response.sources,
    suggestions: response.suggestions,
    correlationId: response.correlation_id ?? null,
  };
}

function retryableState(state: AssistantTurnState): boolean {
  return state === "search_unavailable" || state === "provider_failed" || state === "timeout";
}

function transportFailureToAssistant(
  turnId: string,
  mode: ChatMode,
  error: unknown,
): AssistantTurn {
  const correlationId = error instanceof ApiError ? error.correlationId ?? null : null;

  return {
    id: turnId,
    role: "assistant",
    mode,
    state: "provider_failed",
    answer: null,
    citations: [],
    sources: [],
    suggestions: [],
    correlationId,
  };
}

function messageForError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return "Không thể hoàn tất lượt trò chuyện này. Hãy thử lại.";
}

export async function submitChatTurn(
  options: {
    conversationId: string;
    request: ChatTurnRequest;
    jsonRequest?: JsonRequester;
    fetchImpl?: typeof fetch;
  },
): Promise<ChatResponseEnvelope> {
  const jsonRequest =
    options.jsonRequest ??
    (<T,>(input: string, init: RequestInit) => requestJson<T>(input, init, options.fetchImpl));

  const response = await jsonRequest<SubmitTurnTransportResponse>(
    `/api/conversations/${options.conversationId}/turns`,
    {
      method: "POST",
      cache: "no-store",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        mode: toTransportMode(options.request.mode),
        prompt: options.request.prompt,
        retry_of_message_id: options.request.retryOfMessageId ?? null,
      }),
    },
  );

  return normalizeSearchPayload(
    response.assistant_message.id,
    response.assistant_message.search,
    response.assistant_message.content,
  );
}

export class ChatSessionController {
  private readonly conversationId: string;
  private readonly sendTurn: SendTurn;
  private readonly retryContext = new Map<string, { prompt: string; mode: ChatMode }>();
  private requestCount = 0;
  private model: Omit<ChatSessionSnapshot, "submitLabel">;

  constructor(deps: ChatSessionDependencies = {}) {
    this.conversationId = deps.conversationId ?? createConversationId();
    this.sendTurn =
      deps.sendTurn ??
      ((request) =>
        submitChatTurn({
          conversationId: this.conversationId,
          request,
          fetchImpl: deps.fetchImpl,
        }));

    this.model = {
      conversationId: this.conversationId,
      mode: "direct",
      draft: "",
      turns: [],
      isPending: false,
      activeRetryId: null,
      announcement: null,
      errorMessage: null,
    };
  }

  get snapshot(): ChatSessionSnapshot {
    return {
      ...this.model,
      turns: [...this.model.turns],
      submitLabel: defaultSubmitLabel(this.model.mode, this.model.isPending),
    };
  }

  setMode(mode: ChatMode): ChatSessionSnapshot {
    if (this.model.isPending) {
      return this.snapshot;
    }

    this.model = {
      ...this.model,
      mode,
      announcement: null,
      errorMessage: null,
    };
    return this.snapshot;
  }

  setDraft(draft: string): ChatSessionSnapshot {
    this.model = {
      ...this.model,
      draft,
      announcement: null,
      errorMessage: null,
    };
    return this.snapshot;
  }

  prefillSuggestion(query: string): ChatSessionSnapshot {
    this.model = {
      ...this.model,
      mode: "search",
      draft: query,
      announcement: 'Đã điền gợi ý tìm kiếm vào ô soạn. Nhấn "Tìm bằng Google" để tiếp tục.',
      errorMessage: null,
    };
    return this.snapshot;
  }

  async submitTurn(): Promise<ChatSessionSnapshot> {
    if (this.model.isPending) {
      return this.snapshot;
    }

    const prompt = this.model.draft.trim();
    if (!prompt) {
      return this.snapshot;
    }

    const mode = this.model.mode;
    const userTurn: UserTurn = {
      id: `local-user-${++this.requestCount}`,
      role: "user",
      mode,
      content: prompt,
    };

    this.model = {
      ...this.model,
      turns: [...this.model.turns, userTurn],
      draft: "",
      isPending: true,
      activeRetryId: null,
      announcement: null,
      errorMessage: null,
    };

    try {
      const response = await this.sendTurn({ mode, prompt });
      const assistantTurn = toAssistantTurn(response, mode);
      this.retryContext.set(assistantTurn.id, { prompt, mode });
      this.model = {
        ...this.model,
        turns: [...this.model.turns, assistantTurn],
        isPending: false,
      };
    } catch (error) {
      if (mode === "search") {
        const failedTurn = transportFailureToAssistant(`local-assistant-${this.requestCount}`, mode, error);
        this.retryContext.set(failedTurn.id, { prompt, mode });
        this.model = {
          ...this.model,
          turns: [...this.model.turns, failedTurn],
          isPending: false,
        };
      } else {
        this.model = {
          ...this.model,
          turns: this.model.turns.slice(0, -1),
          draft: prompt,
          isPending: false,
          errorMessage: messageForError(error),
        };
      }
    }

    return this.snapshot;
  }

  async retryTurn(turnId: string): Promise<ChatSessionSnapshot> {
    if (this.model.isPending) {
      return this.snapshot;
    }

    const retry = this.retryContext.get(turnId);
    if (!retry) {
      return this.snapshot;
    }

    const assistantIndex = this.model.turns.findIndex(
      (turn): turn is AssistantTurn => turn.role === "assistant" && turn.id === turnId,
    );

    if (assistantIndex === -1) {
      return this.snapshot;
    }

    const currentTurn = this.model.turns[assistantIndex];
    if (currentTurn.role !== "assistant" || !retryableState(currentTurn.state)) {
      return this.snapshot;
    }

    this.model = {
      ...this.model,
      isPending: true,
      activeRetryId: turnId,
      announcement: null,
      errorMessage: null,
    };

    try {
      const response = await this.sendTurn({
        mode: retry.mode,
        prompt: retry.prompt,
        retryOfMessageId: turnId,
      });

      const nextAssistantTurn = {
        ...toAssistantTurn(response, retry.mode),
        id: turnId,
      } satisfies AssistantTurn;

      const turns = [...this.model.turns];
      turns[assistantIndex] = nextAssistantTurn;
      this.retryContext.set(turnId, retry);
      this.model = {
        ...this.model,
        turns,
        isPending: false,
        activeRetryId: null,
      };
    } catch (error) {
      const turns = [...this.model.turns];
      turns[assistantIndex] = transportFailureToAssistant(turnId, retry.mode, error);
      this.model = {
        ...this.model,
        turns,
        isPending: false,
        activeRetryId: null,
      };
    }

    return this.snapshot;
  }
}
