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

const citations: CitationReference[] = [
  { id: "citation-1", source_id: "source-1", marker: 1, label: "Nguồn 1" },
  { id: "citation-2", source_id: "source-2", marker: 2, label: "Nguồn 2" },
];

const sources: SearchSource[] = [
  {
    id: "source-1",
    title: "Cổng thông tin A",
    url: "https://news.example.com/a",
    domain: "news.example.com",
  },
  {
    id: "source-2",
    title: "Cổng thông tin B",
    url: "https://docs.example.com/b",
    domain: "docs.example.com",
  },
];

const suggestions: SearchSuggestion[] = [
  {
    id: "suggestion-1",
    label: "Tìm tiếp chủ đề hôm nay",
    query: "chủ đề hôm nay",
  },
  {
    id: "suggestion-2",
    label: "<b>Không được render HTML</b>",
    query: "an toàn html",
  },
];

function renderAssistantTurn(turn: AssistantTurn): string {
  return renderToStaticMarkup(
    <AssistantMessageCard
      turn={turn}
      onPrefillSuggestion={() => undefined}
      onRetry={() => undefined}
    />,
  );
}

void test("grounded turns render badge, inline citations, source list, and suggestions in separate trusted blocks", () => {
  const markup = renderAssistantTurn({
    id: "assistant-grounded",
    role: "assistant",
    state: "grounded",
    mode: "search",
    answer: "Bản tóm tắt hiện tại",
    citations,
    sources,
    suggestions,
  });

  const badgeIndex = markup.indexOf("Google-grounded");
  const answerIndex = markup.indexOf("Bản tóm tắt hiện tại");
  const sourceHeadingIndex = markup.indexOf("Nguồn tham khảo");
  const suggestionHeadingIndex = markup.indexOf("Gợi ý tìm kiếm tiếp theo");

  assert.notEqual(badgeIndex, -1);
  assert.notEqual(markup.indexOf("aria-label=\"Nguồn 1\""), -1);
  assert.notEqual(markup.indexOf("aria-label=\"Nguồn 2\""), -1);
  assert.notEqual(sourceHeadingIndex, -1);
  assert.notEqual(suggestionHeadingIndex, -1);
  assert.ok(badgeIndex < answerIndex);
  assert.ok(answerIndex < sourceHeadingIndex);
  assert.ok(sourceHeadingIndex < suggestionHeadingIndex);
  assert.match(markup, /Cổng thông tin A/);
  assert.match(markup, /news\.example\.com/);
  assert.match(markup, /Tìm tiếp chủ đề hôm nay/);
  assert.match(markup, /&lt;b&gt;Không được render HTML&lt;\/b&gt;/);
});

void test("missing-grounding turns show a tentative note without badge, citations, sources, or suggestions", () => {
  const markup = renderAssistantTurn({
    id: "assistant-missing-grounding",
    role: "assistant",
    state: "missing_grounding",
    mode: "search",
    answer: "Đây là câu trả lời chưa có nguồn xác thực rõ ràng.",
    citations,
    sources,
    suggestions,
  });

  assert.match(
    markup,
    /Kết quả này có thể tham khảo vì chưa có nguồn xác thực rõ ràng\./,
  );
  assert.equal(markup.includes("Google-grounded"), false);
  assert.equal(markup.includes("Nguồn tham khảo"), false);
  assert.equal(markup.includes("Gợi ý tìm kiếm tiếp theo"), false);
  assert.equal(markup.includes("aria-label=\"Nguồn 1\""), false);
});

void test("denied turns visibly state that search was blocked and no search was executed", () => {
  const markup = renderAssistantTurn({
    id: "assistant-denied",
    role: "assistant",
    state: "denied",
    mode: "search",
    answer: null,
    citations: [],
    sources: [],
    suggestions: [],
    correlationId: null,
  });

  assert.match(markup, /Tìm kiếm đã bị chặn/);
  assert.match(
    markup,
    /Yêu cầu này không được phép dùng Google Search\. Không có lượt tìm kiếm nào được thực hiện\./,
  );
  assert.equal(markup.includes("Thử lại tìm kiếm"), false);
});

void test("unavailable, provider-failed, and timeout turns keep distinct copy and render an inline retry control", () => {
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
      answer: null,
      citations: [],
      sources: [],
      suggestions: [],
      correlationId: "corr-123",
    });

    assert.match(markup, new RegExp(heading));
    assert.match(markup, /Thử lại tìm kiếm/);
    assert.match(markup, /Mã tham chiếu: corr-123/);
  }
});
