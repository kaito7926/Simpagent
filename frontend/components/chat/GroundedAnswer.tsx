import type { ReactNode } from "react";
import React from "react";

import { StatusBadge } from "@/components/account-access/StatusBadge";
import type { CitationReference, SearchSource, SearchSuggestion, WebsearchProvider } from "@/lib/chat-session";

import { CitationMarker } from "./CitationMarker";
import { SearchSourceList } from "./SearchSourceList";
import { SearchSuggestionList } from "./SearchSuggestionList";

type GroundedAnswerProps = {
  answer: string;
  provider: WebsearchProvider;
  citations: CitationReference[];
  sources: SearchSource[];
  suggestions: SearchSuggestion[];
  onPrefillSuggestion: (query: string) => void;
};

function renderAnswerWithCitations(
  answer: string,
  citations: CitationReference[],
): ReactNode[] {
  if (citations.length === 0) {
    return [answer];
  }

  const positionedCitations = citations
    .filter((citation) => typeof citation.end === "number")
    .sort((left, right) => (left.end ?? 0) - (right.end ?? 0));

  if (positionedCitations.length === 0) {
    return [
      answer,
      ...citations.map((citation) => (
        <CitationMarker
          key={citation.id}
          marker={citation.marker}
          label={`Nguồn ${citation.marker}`}
          sourceId={citation.source_id}
        />
      )),
    ];
  }

  const nodes: ReactNode[] = [];
  let cursor = 0;

  for (const citation of positionedCitations) {
    const end = citation.end ?? cursor;
    nodes.push(answer.slice(cursor, end));
    nodes.push(
      <CitationMarker
        key={citation.id}
        marker={citation.marker}
        label={`Nguồn ${citation.marker}`}
        sourceId={citation.source_id}
      />,
    );
    cursor = end;
  }

  if (cursor < answer.length) {
    nodes.push(answer.slice(cursor));
  }

  return nodes;
}

export function GroundedAnswer({
  answer,
  provider,
  citations,
  sources,
  suggestions,
  onPrefillSuggestion,
}: GroundedAnswerProps) {
  const badgeLabel = provider === "firecrawl" ? "Nguồn web" : "Google-grounded";
  const trustedSuggestions = provider === "gemini" ? suggestions : [];

  return (
    <div className="grounded-answer">
      <div className="assistant-badge-row">
        <StatusBadge tone="success">{badgeLabel}</StatusBadge>
      </div>
      <div className="assistant-answer">
        <p className="body-copy">{renderAnswerWithCitations(answer, citations)}</p>
      </div>
      <SearchSourceList sources={sources} />
      <SearchSuggestionList
        suggestions={trustedSuggestions}
        onPrefillSuggestion={onPrefillSuggestion}
      />
    </div>
  );
}
