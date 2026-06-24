import React from "react";

import type { SearchSource } from "@/lib/chat-session";

type SearchSourceListProps = {
  sources: SearchSource[];
};

export function SearchSourceList({ sources }: SearchSourceListProps) {
  if (sources.length === 0) {
    return null;
  }

  return (
    <section className="search-evidence-section" aria-label="Nguồn tham khảo">
      <h3 className="small-label">Nguồn tham khảo</h3>
      <ol className="search-source-list">
        {sources.map((source) => (
          <li key={source.id}>
            <a
              id={source.id}
              className="search-source-link"
              href={source.url}
              target="_blank"
              rel="noreferrer noopener"
            >
              <span className="search-source-title">{source.title}</span>
              <span className="search-source-domain">{source.domain}</span>
            </a>
          </li>
        ))}
      </ol>
    </section>
  );
}
