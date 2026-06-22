---
status: resolved
trigger: "Tinh chỉnh Agent Orchestration và các System prompt để cải thiện khả năng gọi Agent Websearch và Agent Python Execution; ví dụ tính tổng từ 1 đến 3600 chỉ trả lời 'Reviewed Python execution completed successfully.' thay vì kết quả, và agent thường ưu tiên 'SimpAgent cannot do that in direct chat' thay vì chủ động websearch khi cần."
created: 2026-06-14
updated: 2026-06-14
---

## Symptoms

- Expected behavior: Agent chủ động route sang WebSearchAgent khi câu hỏi cần dữ liệu mới/không chắc sau knowledge cutoff 2025-08-31, và route sang Python execution khi cần tính toán; câu trả lời cuối phải nêu kết quả tool cho user.
- Actual behavior: Python execution có thể thành công nhưng assistant chỉ trả lời summary chung chung. Websearch đã có nhưng direct chat prompt làm model hay từ chối bằng "SimpAgent cannot do that in direct chat".
- Error messages: Không có exception; lỗi là orchestration/prompt trả lời sai hoặc thiếu kết quả.
- Timeline: Hiện tại trong prototype.
- Reproduction: Prompt "Tính tổng từ 1 đến 3600" hoặc câu hỏi cần thông tin mới/websearch.

## Current Focus

- hypothesis: Direct-chat system prompt đang cấm nhắc tới tool quá mạnh, Python answer path đang dùng supervisor summary thay vì stdout/result, và routing intent detection đang quá hẹp.
- test: Inspect prompt/coordinator/planner; add focused tests for Python result surfaced and websearch routing priority.
- expecting: Code path should expose Python stdout/result in assistant content and route freshness/current-info prompts to search when user has scope.
- next_action: resolved
- reasoning_checkpoint: Search intent now wins before Python; Python assistant content renders stdout/stderr excerpts instead of generic supervisor summary.
- tdd_checkpoint: Targeted Docker pytest passed: 15 tests.

## Evidence

- 2026-06-14: `DIRECT_CHAT_SYSTEM_PROMPT` no longer encourages blanket "cannot do that in direct chat" refusals for ordinary questions.
- 2026-06-14: `prompt_requests_search` covers current/latest/recent/post-cutoff year and Vietnamese freshness terms.
- 2026-06-14: `ChatCoordinator.complete` routes search before Python when external data is requested.
- 2026-06-14: `_python_assistant_content` surfaces reviewed stdout/stderr excerpts in assistant content.

## Eliminated

- hypothesis: Python supervisor failed to execute code. Evidence: existing result envelope can be `succeeded`; issue was response content selection.

## Resolution

- root_cause: Routing and prompt defaults favored direct/Python denial paths, and Python assistant content used generic `summary` instead of reviewed execution output.
- fix: Expanded routing policy, made search-first for external/current-data prompts, softened direct-chat refusal prompt, required Python planner stdout, and formatted Python stdout/stderr into assistant content.
- verification: `docker compose -f compose.test.yaml run --rm backend-test python -m pytest tests/unit/agent/test_policy_routing.py tests/unit/ai/test_chat_adapter.py tests/integration/python/test_python_authorization.py::test_vietnamese_sum_prompt_returns_python_stdout_in_assistant_message tests/integration/python/test_python_authorization.py::test_search_plus_python_prompt_routes_to_search_without_touching_planner_or_supervisor tests/integration/python/test_python_full_flow.py::test_successful_python_turn_persists_artifacts_reuses_state_and_extends_sliding_expiry` passed with 15 tests.
- files_changed: backend/app/ai/prompts.py; backend/app/agent/policy.py; backend/app/agent/coordinator.py; backend/app/agent/decisions.py; backend/app/ai/search_worker/agent.py; backend/tests/unit/agent/test_policy_routing.py; backend/tests/integration/python/test_python_authorization.py; backend/tests/integration/python/test_python_full_flow.py.
