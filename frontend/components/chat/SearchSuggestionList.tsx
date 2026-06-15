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
    <section className="search-evidence-section" aria-label="Suggested follow-up searches">
      <h3 className="small-label">Suggested follow-up searches</h3>
      <div className="search-suggestion-list">
        {suggestions.map((suggestion) => (
          <ActionButton
            key={suggestion.id}
            type="button"
            variant="quiet"
            fullWidth={false}
            className="search-suggestion-button"
            aria-label={`${suggestion.label}. Fill the composer without auto-submitting.`}
            onClick={() => onPrefillSuggestion(suggestion.query)}
          >
            {suggestion.label}
          </ActionButton>
        ))}
      </div>
    </section>
  );
}
