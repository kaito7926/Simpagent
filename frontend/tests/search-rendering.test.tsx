import assert from "node:assert/strict";
import test from "node:test";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { AssistantMessageCard } from "@/components/chat/AssistantMessageCard";
import {
  type AssistantTurn,
  type CitationReference,
  type SearchSource,
  type SearchSuggestion,
} from "@/lib/chat-session";

type ProviderAwareAssistantTurn = AssistantTurn & {
  provider?: "gemini" | "firecrawl" | null;
};

const citations: CitationReference[] = [
  { id: "citation-1", source_id: "source-1", marker: 1, label: "Source 1" },
  { id: "citation-2", source_id: "source-2", marker: 2, label: "Source 2" },
];

const sources: SearchSource[] = [
  {
    id: "source-1",
    title: "Reference portal A",
    url: "https://news.example.com/a",
    domain: "news.example.com",
  },
  {
    id: "source-2",
    title: "Reference portal B",
    url: "https://docs.example.com/b",
    domain: "docs.example.com",
  },
];

const suggestions: SearchSuggestion[] = [
  {
    id: "suggestion-1",
    label: "Search the topic again for today",
    query: "topic today",
  },
  {
    id: "suggestion-2",
    label: "<b>HTML must not render</b>",
    query: "safe html",
  },
];

function renderAssistantTurn(turn: ProviderAwareAssistantTurn): string {
  return renderToStaticMarkup(
    <AssistantMessageCard
      turn={turn}
      onPrefillSuggestion={() => undefined}
      onRetry={() => undefined}
    />,
  );
}

void test("Gemini grounded turns retain Google badge, citations, sources, and trusted suggestions", () => {
  const markup = renderAssistantTurn({
    id: "assistant-grounded",
    role: "assistant",
    state: "grounded",
    mode: "search",
    provider: "gemini",
    answer: "Current verified summary",
    citations,
    sources,
    suggestions,
  });

  const badgeIndex = markup.indexOf("Google-grounded");
  const answerIndex = markup.indexOf("Current verified summary");
  const sourceHeadingIndex = markup.indexOf("Nguồn tham khảo");
  const suggestionHeadingIndex = markup.indexOf("Gợi ý tìm kiếm tiếp theo");

  assert.notEqual(badgeIndex, -1);
  assert.notEqual(markup.indexOf('aria-label="Nguồn 1"'), -1);
  assert.notEqual(markup.indexOf('aria-label="Nguồn 2"'), -1);
  assert.notEqual(sourceHeadingIndex, -1);
  assert.notEqual(suggestionHeadingIndex, -1);
  assert.ok(badgeIndex < answerIndex);
  assert.ok(answerIndex < sourceHeadingIndex);
  assert.ok(sourceHeadingIndex < suggestionHeadingIndex);
  assert.match(markup, /Reference portal A/);
  assert.match(markup, /news\.example\.com/);
  assert.match(markup, /Search the topic again for today/);
  assert.match(markup, /&lt;b&gt;HTML must not render&lt;\/b&gt;/);
});

void test("Firecrawl grounded turns use provider-honest labels and omit Google-only suggestions", () => {
  const markup = renderAssistantTurn({
    id: "assistant-firecrawl",
    role: "assistant",
    state: "grounded",
    mode: "search",
    provider: "firecrawl",
    answer: "Firecrawl returned a sourced summary.",
    citations,
    sources,
    suggestions: [],
  });

  assert.match(markup, /Firecrawl-grounded/);
  assert.match(markup, /Firecrawl returned a sourced summary\./);
  assert.match(markup, /Nguồn tham khảo/);
  assert.doesNotMatch(markup, /Google-grounded|Google Search|Gợi ý tìm kiếm tiếp theo|Suggested follow-up searches/);
});

void test("missing-grounding turns show a tentative note without badge, citations, sources, or suggestions", () => {
  const markup = renderAssistantTurn({
    id: "assistant-missing-grounding",
    role: "assistant",
    state: "missing_grounding",
    mode: "search",
    provider: "firecrawl",
    answer: "This answer does not have fully verified sources yet.",
    citations,
    sources,
    suggestions,
  });

  assert.match(markup, /assistant-note/);
  assert.match(markup, /Kết quả này có thể tham khảo vì chưa có nguồn xác thực rõ ràng\./);
  assert.equal(markup.includes("Google-grounded"), false);
  assert.equal(markup.includes("Nguồn tham khảo"), false);
  assert.equal(markup.includes("Gợi ý tìm kiếm tiếp theo"), false);
  assert.equal(markup.includes('aria-label="Nguồn 1"'), false);
});

void test("denied turns use neutral Vietnamese copy and state that no search was executed", () => {
  const markup = renderAssistantTurn({
    id: "assistant-denied",
    role: "assistant",
    state: "denied",
    mode: "search",
    provider: "firecrawl",
    answer: null,
    citations: [],
    sources: [],
    suggestions: [],
    correlationId: null,
  });

  assert.match(markup, /Tìm kiếm đã bị chặn/);
  assert.match(
    markup,
    /Yêu cầu này không được phép dùng dịch vụ tìm kiếm\. Không có lượt tìm kiếm nào được thực hiện\./,
  );
  assert.equal(markup.includes("Thử lại tìm kiếm"), false);
  assert.doesNotMatch(markup, /Google Search/);
});

void test("unavailable, provider-failed, and timeout turns keep distinct Vietnamese copy and retry control", () => {
  const expected = new Map<AssistantTurn["state"], string>([
    ["search_unavailable", "Tìm kiếm hiện không khả dụng"],
    ["provider_failed", "Tìm kiếm đã thất bại"],
    ["timeout", "Tìm kiếm đã quá thời gian chờ"],
  ]);

  for (const [state, heading] of expected) {
    const markup = renderAssistantTurn({
      id: `assistant-${state}`,
      role: "assistant",
      state,
      mode: "search",
      provider: state === "timeout" ? "gemini" : "firecrawl",
      answer: null,
      citations: [],
      sources: [],
      suggestions: [],
      correlationId: "corr-123",
    });

    assert.match(markup, new RegExp(heading));
    assert.match(markup, /Thử lại tìm kiếm/);
    assert.match(markup, /Mã tham chiếu: corr-123/);
    if (state !== "timeout") {
      assert.doesNotMatch(markup, /Google Search/);
    }
  }
});
