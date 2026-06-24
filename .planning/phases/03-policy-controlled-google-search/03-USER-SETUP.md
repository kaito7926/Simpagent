# Phase 03: User Setup Required

**Generated:** 2026-06-23
**Phase:** 03-policy-controlled-google-search
**Status:** Incomplete

Complete these items for optional Firecrawl Cloud websearch to function. The backend code and tests are implemented; the API key must come from a human-controlled Firecrawl account.

## Environment Variables

| Status | Variable | Source | Add to |
|--------|----------|--------|--------|
| [ ] | `FIRECRAWL_API_KEY` | Firecrawl Dashboard -> API Keys | `.env` or deployment secret store |
| [ ] | `SIMPAGENT_WEBSEARCH_PROVIDER=firecrawl` | Operator choice | `.env` or deployment secret store |

## Dashboard Configuration

- [ ] **Create a Firecrawl Cloud API key**
  - Location: Firecrawl Dashboard -> API Keys
  - Notes: Store only in environment configuration. Do not commit or paste the key into prompts, logs, tests, or planning artifacts.

## Verification

After completing setup, verify with:

```bash
docker compose -f compose.test.yaml run --rm backend-test pytest -q tests/integration/search/test_search_capability_check.py
```

Expected results:
- Firecrawl provider readiness is `ready` when `SIMPAGENT_WEBSEARCH_PROVIDER=firecrawl` and `FIRECRAWL_API_KEY` are present.
- If the key is missing, search returns `search_unavailable` and does not fall back to Gemini.

---

**Once all items complete:** Mark status as "Complete" at top of file.
