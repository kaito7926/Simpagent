---
status: diagnosed
phase: 03-policy-controlled-google-search
source: [03-VERIFICATION.md]
started: 2026-06-23T15:28:47+07:00
updated: 2026-06-24T02:12:24+07:00
---

## Current Test

[testing complete]

## Tests

### 1. Search Suggestions UX

test: Run the chat UI, produce a Gemini grounded answer with suggestions, click a suggestion.
expected: Suggestions remain separate from Markdown; clicking pre-fills the composer, switches/focuses search intent, and does not auto-submit.
result: issue
reported: "Tính năng internet search hiện tại không hoạt động, đọc log để tìm ra nguyên nhân"
severity: major

### 2. Missing-Grounding Tone

test: Trigger a missing-grounding fallback.
expected: The assistant turn shows `có thể tham khảo`, has no grounded badge/citations/suggestions, and feels tentative rather than like a verified answer.
result: issue
reported: "[Image #2] Output của websearch firecrawl trông rất tệ , các nút [1] ,[2] , [3], [4] ,[5] không có tác dụng bấm được, đường link thì không đổi màu mà nhìn giống như text thường. Chữ \"firecrawl grounded\" không nên xuất hiện . Câu trả lời \"Hôm nay có ... đầy đủ cặp đấu\" hiển thị text bị nhạt . Tôi mong muốn response của AI nhìn đáng tin cậy và hợp lí hơn , các đường link nên để nhỏ lại và đổi màu link thành xanh nước biển (Cân nhắc đưa response của Firecrawl qua một lần gọi LLM nữa để làm đẹp response, hoặc có thể xử lí thủ công bằng code)"
severity: major

### 3. Denied vs Unavailable Distinction

test: Compare a no-scope user search turn with a configured-but-unavailable search turn.
expected: The denied state says no search executed; unavailable says the selected provider is not ready and offers retry/switch guidance.
result: pass

## Summary

total: 3
passed: 1
issues: 2
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "Suggestions remain separate from Markdown; clicking pre-fills the composer, switches/focuses search intent, and does not auto-submit."
  status: failed
  reason: "User reported: Tính năng internet search hiện tại không hoạt động, đọc log để tìm ra nguyên nhân"
  severity: major
  test: 1
  root_cause: "The backend was not configured as Firecrawl-by-default in the UAT environment. Firecrawl credentials were present, but SIMPAGENT_WEBSEARCH_PROVIDER was not set, so the app kept the code default of gemini. That left default search requests on Gemini/unconfigured, producing the logged gemini-2.5-flash 503 failures until a runtime override switched live requests to Firecrawl."
  artifacts:
    - path: "backend/app/core/config.py"
      issue: "websearch_provider defaults to gemini, so Firecrawl keys alone do not switch the effective provider."
    - path: "backend/app/core/provider_status.py"
      issue: "search readiness and effective provider resolve to Firecrawl only when env or runtime override explicitly selects firecrawl."
    - path: "backend/app/main.py"
      issue: "startup app state derives search provider/status from env defaults, so the service boots as Gemini when the provider variable is missing."
    - path: "compose.yaml"
      issue: "backend environment passes Firecrawl key/base variables but does not set SIMPAGENT_WEBSEARCH_PROVIDER=firecrawl."
    - path: ".planning/phases/03-policy-controlled-google-search/03-USER-SETUP.md"
      issue: "setup guidance already states that both FIRECRAWL_API_KEY and SIMPAGENT_WEBSEARCH_PROVIDER=firecrawl are required."
  missing:
    - "Set SIMPAGENT_WEBSEARCH_PROVIDER=firecrawl in the actual UAT/deployment environment instead of relying on Firecrawl credentials alone."
    - "Keep startup/default provider configuration aligned with any admin runtime override so readiness, admin evidence, and live execution all resolve to Firecrawl consistently."
    - "Re-verify the suggestions UX against a Firecrawl-default environment after provider alignment."
  debug_session: "D:\\ADMIN\\Documents\\matmahoc\\@DO_AN\\Simpagent\\.claude\\worktrees\\agent-a7d0c352f1292eb00\\.planning\\debug\\phase03-search-gemini-503.md"
- truth: "The assistant turn shows `có thể tham khảo`, has no grounded badge/citations/suggestions, and feels tentative rather than like a verified answer."
  status: failed
  reason: "User reported: [Image #2] Output của websearch firecrawl trông rất tệ , các nút [1] ,[2] , [3], [4] ,[5] không có tác dụng bấm được, đường link thì không đổi màu mà nhìn giống như text thường. Chữ \"firecrawl grounded\" không nên xuất hiện . Câu trả lời \"Hôm nay có ... đầy đủ cặp đấu\" hiển thị text bị nhạt . Tôi mong muốn response của AI nhìn đáng tin cậy và hợp lí hơn , các đường link nên để nhỏ lại và đổi màu link thành xanh nước biển (Cân nhắc đưa response của Firecrawl qua một lần gọi LLM nữa để làm đẹp response, hoặc có thể xử lí thủ công bằng code)"
  severity: major
  test: 2
  root_cause: "Firecrawl turns are being classified as grounded even though they are only synthesized result lists. The backend Firecrawl adapter builds answer_markdown as plain [n] title: description lines and marks the turn grounded whenever public sources exist. Frontend grounded rendering then shows a Firecrawl-grounded badge and muted body text, but only structured citation spans become interactive buttons, so the user sees dull text, raw-looking [1]-[5] references, and source links that do not read as trustworthy interactive citations."
  artifacts:
    - path: "backend/app/ai/search_worker/firecrawl_client.py"
      issue: "returns state=grounded for any sourced Firecrawl result and constructs plain [n] title: description answer text without true answer-to-source grounding spans."
    - path: "backend/app/services/chat_turns.py"
      issue: "normalization preserves Firecrawl grounded state unless sources/citations are missing, so this path never downgrades to the intended tentative missing_grounding UI."
    - path: "frontend/components/chat/GroundedAnswer.tsx"
      issue: "renders Firecrawl-grounded badge for any grounded Firecrawl turn and displays the answer inside muted body-copy styling."
    - path: "frontend/app/globals.css"
      issue: "grounded-answer body text inherits muted text color and no dedicated styling makes Firecrawl source links visually distinct or clearly interactive."
  missing:
    - "Tighten Firecrawl normalization so list-style Firecrawl results downgrade to missing_grounding unless they have a truly grounded answer contract."
    - "Or add a second shaping step that rewrites Firecrawl results into trustworthy prose plus structured clickable citations before the frontend renders them."
    - "Update grounded/source styling so source links are smaller, blue, and obviously interactive instead of looking like plain muted text."
    - "Remove or rename the Firecrawl-grounded label so Firecrawl results do not imply Gemini-style grounding trust."
  debug_session: "D:/ADMIN/Documents/matmahoc/@DO_AN/Simpagent/.claude/worktrees/agent-a20f7b58fce80fbd9/.planning/debug/firecrawl-websearch-uat-ui.md"
