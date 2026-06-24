import React from "react";

import { ActionButton } from "@/components/account-access/ActionButton";
import type { SearchSuggestion } from "@/lib/chat-session";

type SearchSuggestionListProps = {
  suggestions: SearchSuggestion[];
  onPrefillSuggestion: (query: string) => void;
};

export function SearchSuggestionList({
  suggestions,
  onPrefillSuggestion,
}: SearchSuggestionListProps) {
  if (suggestions.length === 0) {
    return null;
  }

  return (
    <section className="search-evidence-section" aria-label="Gợi ý tìm kiếm tiếp theo">
      <h3 className="small-label">Gợi ý tìm kiếm tiếp theo</h3>
      <div className="search-suggestion-list">
        {suggestions.map((suggestion) => (
          <ActionButton
            key={suggestion.id}
            type="button"
            variant="quiet"
            fullWidth={false}
            className="search-suggestion-button"
            aria-label={`${suggestion.label}. Điền vào ô soạn, không tự gửi.`}
            onClick={() => onPrefillSuggestion(suggestion.query)}
          >
            {suggestion.label}
          </ActionButton>
        ))}
      </div>
    </section>
  );
}
