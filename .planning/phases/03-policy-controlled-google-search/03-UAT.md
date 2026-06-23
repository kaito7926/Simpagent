---
status: testing
phase: 03-policy-controlled-google-search
source: [03-VERIFICATION.md]
started: 2026-06-23T15:28:47+07:00
updated: 2026-06-23T15:28:47+07:00
---

## Current Test

number: 1
name: Search Suggestions UX
expected: |
  Suggestions remain separate from Markdown; clicking pre-fills the composer, switches/focuses search intent, and does not auto-submit.
awaiting: user response

## Tests

### 1. Search Suggestions UX

test: Run the chat UI, produce a Gemini grounded answer with suggestions, click a suggestion.
expected: Suggestions remain separate from Markdown; clicking pre-fills the composer, switches/focuses search intent, and does not auto-submit.
result: [pending]

### 2. Missing-Grounding Tone

test: Trigger a missing-grounding fallback.
expected: The assistant turn shows `có thể tham khảo`, has no grounded badge/citations/suggestions, and feels tentative rather than like a verified answer.
result: [pending]

### 3. Denied vs Unavailable Distinction

test: Compare a no-scope user search turn with a configured-but-unavailable search turn.
expected: The denied state says no search executed; unavailable says the selected provider is not ready and offers retry/switch guidance.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
