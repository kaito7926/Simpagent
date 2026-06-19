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
    answer: "Current verified summary",
    citations,
    sources,
    suggestions,
  });

  const badgeIndex = markup.indexOf("Google-grounded");
  const answerIndex = markup.indexOf("Current verified summary");
  const sourceHeadingIndex = markup.indexOf("Sources");
  const suggestionHeadingIndex = markup.indexOf("Suggested follow-up searches");

  assert.notEqual(badgeIndex, -1);
  assert.notEqual(markup.indexOf('aria-label="Source 1"'), -1);
  assert.notEqual(markup.indexOf('aria-label="Source 2"'), -1);
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

void test("missing-grounding turns show a tentative note without badge, citations, sources, or suggestions", () => {
  const markup = renderAssistantTurn({
    id: "assistant-missing-grounding",
    role: "assistant",
    state: "missing_grounding",
    mode: "search",
    answer: "This answer does not have fully verified sources yet.",
    citations,
    sources,
    suggestions,
  });

  assert.match(markup, /assistant-note/);
  assert.match(markup, /This answer does not have fully verified sources yet\./);
  assert.equal(markup.includes("Google-grounded"), false);
  assert.equal(markup.includes("Sources"), false);
  assert.equal(markup.includes("Suggested follow-up searches"), false);
  assert.equal(markup.includes('aria-label="Source 1"'), false);
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

  assert.match(markup, /Search was blocked/);
  assert.match(
    markup,
    /This request is not allowed to use Google Search\. No external search was executed\./,
  );
  assert.equal(markup.includes("Retry search"), false);
});

void test("unavailable, provider-failed, and timeout turns keep distinct copy and render an inline retry control", () => {
  const expected = new Map<AssistantTurn["state"], string>([
    ["search_unavailable", "Search is currently unavailable"],
    ["provider_failed", "Search failed"],
    ["timeout", "Search timed out"],
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
    assert.match(markup, /Retry search/);
    assert.match(markup, /Reference code: corr-123/);
  }
});
