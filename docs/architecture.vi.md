# Kiến trúc SimpAgent

Tài liệu này mô tả kiến trúc đang có trong repo, không mô tả một trạng thái “mong muốn” khác. Điểm cần giữ trung thực là search hiện chạy qua service logic trong backend, còn sandbox Python là boundary container riêng.

## Thành phần chính

```mermaid
flowchart LR
    Browser["Trình duyệt người dùng"] --> Kong["Kong OSS<br/>public ingress"]
    Kong --> Frontend["Next.js frontend"]
    Kong --> Backend["FastAPI backend"]
    Backend --> Postgres["PostgreSQL"]
    Backend --> Sandbox["Python sandbox supervisor"]
    Backend --> LLM["OpenAI-compatible LLM"]
    Backend --> GoogleSearch["Google Search provider"]
    Backend --> Logs["JSON logs"]
    Logs --> Promtail["Promtail"]
    Kong --> KongLogs["Kong access/error logs"]
    KongLogs --> Promtail
    Promtail --> Loki["Loki"]
    Loki --> Grafana["Grafana"]
```

## Ranh giới tin cậy

```mermaid
flowchart TD
    subgraph Public["Public boundary"]
        Browser["Browser"]
        Kong["Kong :8000"]
    end

    subgraph App["Application boundary"]
        Frontend["Frontend"]
        Backend["FastAPI"]
        Postgres["PostgreSQL"]
        Sandbox["Sandbox supervisor"]
        Loki["Loki / Promtail / Grafana"]
    end

    subgraph External["External dependencies"]
        LLM["OpenAI-compatible provider"]
        Google["Google Search / Gemini"]
        OAuth["Google OAuth / GitHub OAuth"]
    end

    Browser --> Kong
    Kong --> Frontend
    Kong --> Backend
    Backend --> Postgres
    Backend --> Sandbox
    Backend --> LLM
    Backend --> Google
    Backend --> OAuth
```

## Luồng request chính

```mermaid
sequenceDiagram
    participant U as User
    participant K as Kong
    participant F as Frontend
    participant B as Backend
    participant P as PostgreSQL
    participant S as Sandbox
    participant X as External provider

    U->>K: GET /
    K->>F: Proxy frontend route
    U->>K: POST /api/auth/login
    K->>B: Proxy auth route
    B->>P: Verify account / create refresh family
    B-->>U: access token + refresh cookie + CSRF cookie

    U->>K: POST /api/conversations
    K->>B: Conversation request
    B->>P: Persist user message / metadata
    alt direct chat
        B->>X: LLM call
    else google_search
        B->>X: Search worker/provider call
    else python
        B->>S: Capability-bound sandbox execution
        S-->>B: Reviewed result envelope
    end
    B->>P: Persist assistant message / tool execution
    B-->>U: Stable JSON response
```

## Luồng mạng Compose

```mermaid
flowchart LR
    subgraph public["public network"]
        KongP["kong"]
        FrontendP["frontend"]
        GrafanaP["grafana"]
    end

    subgraph private["private network (internal)"]
        KongI["kong"]
        FrontendI["frontend"]
        BackendI["backend"]
        PostgresI["postgres"]
        SandboxI["sandbox"]
        LokiI["loki/promtail"]
    end

    subgraph egress["egress network"]
        BackendE["backend"]
        Provider["LLM / Google APIs"]
    end

    KongP --- FrontendP
    KongI --- BackendI
    BackendI --- PostgresI
    BackendI --- SandboxI
    BackendI --- LokiI
    BackendE --> Provider
```

## Diễn giải topology hiện tại

- `kong` là entrypoint public duy nhất của ứng dụng local ở `http://localhost:8000`.
- `frontend` được publish qua Kong route `/`.
- `backend` nằm trên `private` để nói chuyện với `postgres`, `sandbox`, và observability; đồng thời có thêm `egress` để gọi provider bên ngoài khi được cấu hình.
- `postgres`, `sandbox`, `promtail`, `loki` không được expose ra public port ứng dụng.
- `grafana` có port public riêng `http://localhost:3001` cho mục đích local observability.

## Những điểm cần hiểu đúng

- Search không phải một container riêng trong `compose.yaml`; logic search hiện được backend gọi qua service boundary và provider boundary, rồi persist kết quả an toàn.
- Python tool không chạy trong process FastAPI. Backend chỉ điều phối, cấp capability token, nhận envelope kết quả, và lưu metadata đã review.
- Kong có thể chặn coarse-grained request như CORS, body quá lớn, rate limit; nhưng token, role, scope, ownership, guardrail, và tool policy vẫn do FastAPI quyết định.
- Tài liệu này không che đi planning debt của Phase 3: artifact planning cho search vẫn chưa được reconcile đẹp trong `.planning`, dù behavior hiện tại đã có trong code và test.
