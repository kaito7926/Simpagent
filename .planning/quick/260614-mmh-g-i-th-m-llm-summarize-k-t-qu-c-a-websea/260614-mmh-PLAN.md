---
status: in_progress
created: 2026-06-14
---

# Quick Task 260614-mmh: Gọi thêm LLM để summarize kết quả của WebSearchAgent và Python Agent

## Scope

- Add a ReportWriter LLM summarization step after successful WebSearchAgent and Python agent results.
- Send only reviewed, user-visible agent outputs to the summarizer.
- Preserve existing raw tool metadata and fall back to raw content if summarization fails.
- Add focused tests for Python and search summarization behavior.

## Verification

- Run focused backend tests for Python flow, search-first flow, and chat adapter contracts.
