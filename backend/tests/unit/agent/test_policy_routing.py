from __future__ import annotations

from app.agent.policy import prompt_requests_python, prompt_requests_search


def test_vietnamese_arithmetic_prompt_routes_to_python() -> None:
    assert prompt_requests_python("Tính tổng từ 1 đến 3600") is True
    assert prompt_requests_search("Tính tổng từ 1 đến 3600") is False


def test_current_or_post_cutoff_prompt_routes_to_search() -> None:
    assert prompt_requests_search("CEO hiện tại của OpenAI là ai?") is True
    assert prompt_requests_search("Tóm tắt thay đổi mới nhất của Next.js năm 2026") is True


def test_shell_hash_help_prompt_stays_out_of_python_and_search() -> None:
    prompt = "dạy tôi lệnh tính hash của file trong cmd"

    assert prompt_requests_python(prompt) is False
    assert prompt_requests_search(prompt) is False

