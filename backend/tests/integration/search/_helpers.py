from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.accounts import AccountsRepository
from app.models.account import User
from app.models.domain import Conversation
from app.schemas.search import SearchCitation, SearchSource, SearchSuggestions, SearchWorkerResult
from app.security.access_tokens import issue_access_token


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    scopes: list[str],
    role: str = "user",
) -> User:
    accounts = AccountsRepository(session)
    bundle = await accounts.create_user_with_local_credentials(
        email=email,
        password_hash="argon2-placeholder",
        role=role,
    )
    await accounts.replace_user_scopes(bundle.user.id, scopes)
    await session.flush()
    return bundle.user


async def create_conversation(session: AsyncSession, *, user_id: UUID, title: str = "Phase 3 search") -> Conversation:
    conversation = Conversation(user_id=user_id, title=title)
    session.add(conversation)
    await session.flush()
    return conversation


def issue_token(*, user: User, scopes: list[str], settings) -> str:
    return issue_access_token(
        user_id=user.id,
        role=user.role,
        scopes=scopes,
        settings=settings,
        now=datetime.now(UTC),
    )


def grounded_result() -> SearchWorkerResult:
    return SearchWorkerResult(
        state="grounded",
        answer_markdown="Kết quả tìm kiếm đã được xác thực [1].",
        google_grounded=True,
        tool_executed=True,
        sources=[
            SearchSource(
                index=1,
                title="Nguồn kiểm thử",
                domain="example.test",
                uri="https://example.test/search",
            )
        ],
        citations=[
            SearchCitation(
                index=1,
                source_index=1,
                start=30,
                end=33,
            )
        ],
        suggestions=SearchSuggestions(
            trusted=True,
            items=["Từ khóa tiếp theo"],
        ),
        web_search_queries=["tu khoa goc"],
        output_summary="grounded",
    )


def missing_grounding_result() -> SearchWorkerResult:
    return SearchWorkerResult(
        state="missing_grounding",
        answer_markdown="Đây là câu trả lời chưa có grounding.",
        google_grounded=False,
        tool_executed=True,
        output_summary="missing_grounding",
    )


def provider_failed_result() -> SearchWorkerResult:
    return SearchWorkerResult(
        state="provider_failed",
        answer_markdown="Không thể hoàn tất lượt tìm kiếm này từ dịch vụ tìm kiếm. Hãy thử lại tìm kiếm hoặc chuyển sang câu hỏi bình thường.",
        google_grounded=False,
        tool_executed=True,
        output_summary="provider_failed",
    )


def timeout_result() -> SearchWorkerResult:
    return SearchWorkerResult(
        state="timeout",
        answer_markdown="Không nhận được kết quả từ Google Search trong thời gian cho phép. Hãy thử lại tìm kiếm hoặc chuyển sang câu hỏi bình thường.",
        google_grounded=False,
        tool_executed=True,
        output_summary="timeout",
    )


class RecordingSearchWorker:
    def __init__(self, result: SearchWorkerResult) -> None:
        self.result = result
        self.calls = 0
        self.call_kwargs: list[dict] = []

    async def run(self, **kwargs) -> SearchWorkerResult:
        self.calls += 1
        self.call_kwargs.append(kwargs)
        return self.result
