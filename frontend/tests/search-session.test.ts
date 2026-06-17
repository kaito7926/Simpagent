import assert from "node:assert/strict";
import test from "node:test";

import {
  ChatSessionController,
  type ChatMode,
  type ChatRequestMode,
  type ChatResponseEnvelope,
} from "@/lib/chat-session";

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (error: unknown) => void;
};

function createDeferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });

  return { promise, resolve, reject };
}

function groundedEnvelope(): ChatResponseEnvelope {
  return {
    request_mode: "search",
    response_state: "grounded",
    turn_id: "assistant-1",
    answer_markdown: "The current situation has been verified.",
    citations: [
      { id: "citation-1", source_id: "source-1", marker: 1, label: "Source 1" },
      { id: "citation-2", source_id: "source-2", marker: 2, label: "Source 2" },
    ],
    sources: [
      {
        id: "source-1",
        title: "Source A",
        url: "https://news.example.com/a",
        domain: "news.example.com",
      },
      {
        id: "source-2",
        title: "Source B",
        url: "https://docs.example.com/b",
        domain: "docs.example.com",
      },
    ],
    suggestions: [
      { id: "suggestion-1", label: "Search for today’s latest update", query: "today latest update" },
    ],
  };
}

function timeoutEnvelope(turnId = "assistant-timeout"): ChatResponseEnvelope {
  return {
    request_mode: "search",
    response_state: "timeout",
    turn_id: turnId,
    answer_markdown: null,
    citations: [],
    sources: [],
    suggestions: [],
    correlation_id: "corr-timeout",
  };
}

void test("switching mode preserves draft and updates mode-specific submit labels", () => {
  const controller = new ChatSessionController();

  controller.setDraft("Draft question");
  controller.setMode("search");
  assert.equal(controller.snapshot.mode, "search");
  assert.equal(controller.snapshot.draft, "Draft question");
  assert.equal(controller.snapshot.submitLabel, "Search with Google");

  controller.setMode("direct");
  assert.equal(controller.snapshot.mode, "direct");
  assert.equal(controller.snapshot.draft, "Draft question");
  assert.equal(controller.snapshot.submitLabel, "Send message");
});

void test("pending requests lock mode switching until the request settles", async () => {
  const deferred = createDeferred<ChatResponseEnvelope>();
  const requestedModes: ChatRequestMode[] = [];

  const controller = new ChatSessionController({
    sendTurn: async (request) => {
      requestedModes.push(request.mode);
      return deferred.promise;
    },
  });

  controller.setMode("direct");
  controller.setDraft("Tell me the current status");
  const submitPromise = controller.submitTurn();

  assert.equal(controller.snapshot.isPending, true);
  assert.equal(controller.snapshot.submitLabel, "Sending...");

  controller.setMode("search");
  assert.equal(controller.snapshot.mode, "direct");

  deferred.resolve({
    request_mode: "direct",
    response_state: "direct",
    turn_id: "assistant-direct",
    answer_markdown: "This is a normal direct answer.",
    citations: [],
    sources: [],
    suggestions: [],
  });

  await submitPromise;
  assert.deepEqual(requestedModes, ["direct"]);
  assert.equal(controller.snapshot.mode, "direct");
  assert.equal(controller.snapshot.isPending, false);
});

void test("suggestion clicks prefill composer, switch to search mode, and never auto-submit", () => {
  const submitted: ChatMode[] = [];
  const controller = new ChatSessionController({
    sendTurn: async (request) => {
      submitted.push(request.mode);
      return groundedEnvelope();
    },
  });

  controller.prefillSuggestion("today update schedule");

  assert.equal(controller.snapshot.mode, "search");
  assert.equal(controller.snapshot.draft, "today update schedule");
  assert.equal(controller.snapshot.isPending, false);
  assert.equal(controller.snapshot.turns.length, 0);
  assert.equal(
    controller.snapshot.announcement,
    'The suggested search has been added to the composer. Click "Search with Google" to continue.',
  );
  assert.deepEqual(submitted, []);
});

void test("retry replaces the failed assistant slot instead of duplicating the user turn", async () => {
  let callCount = 0;
  const controller = new ChatSessionController({
    sendTurn: async () => {
      callCount += 1;
      return callCount === 1 ? timeoutEnvelope("assistant-slot") : groundedEnvelope();
    },
  });

  controller.setMode("search");
  controller.setDraft("Current weather update");
  await controller.submitTurn();

  assert.equal(controller.snapshot.turns.length, 2);
  const firstAssistantTurn = controller.snapshot.turns[1];
  assert.equal(firstAssistantTurn.role, "assistant");
  assert.equal(firstAssistantTurn.state, "timeout");
  assert.equal(firstAssistantTurn.id, "assistant-slot");

  await controller.retryTurn("assistant-slot");

  assert.equal(controller.snapshot.turns.length, 2);
  assert.equal(controller.snapshot.turns[0]?.role, "user");
  const retriedAssistantTurn = controller.snapshot.turns[1];
  assert.equal(retriedAssistantTurn.role, "assistant");
  assert.equal(retriedAssistantTurn.id, "assistant-slot");
  assert.equal(retriedAssistantTurn.state, "grounded");
});

void test("response mapping keeps grounded, missing-grounding, denied, unavailable, provider-failed, and timeout distinct", async () => {
  const states = [
    "grounded",
    "missing_grounding",
    "denied",
    "search_unavailable",
    "provider_failed",
    "timeout",
  ] as const;

  for (const state of states) {
    const controller = new ChatSessionController({
      sendTurn: async () => ({
        request_mode: "search",
        response_state: state,
        turn_id: `assistant-${state}`,
        answer_markdown: state === "denied" ? null : "Response content",
        citations: [],
        sources: [],
        suggestions: [],
      }),
    });

    controller.setMode("search");
    controller.setDraft(`Check state ${state}`);
    await controller.submitTurn();

    const assistantTurn = controller.snapshot.turns.at(-1);
    assert.equal(assistantTurn?.role, "assistant");
    assert.equal(assistantTurn?.state, state);
  }
});
