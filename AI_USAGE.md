# AI Usage & Engineering Ownership Log

This project was built using an **AI-First, Human-Verified** workflow across four sessions tracked in `AI_SESSIONS.json`:
- **`S1` (Claude Web):** System architecture, security boundaries, and Phase 1–2 initial skeletons.
- **`S2` (Antigravity IDE Agent):** Test scaffolding, HTML/Jinja2 templates, CSS styling, and FastAPI route boilerplate.
- **`S3` (Gemini Web):** Live API debugging, TDD test specification, and orchestration logic.
- **`S4` (Claude Web):** Phase 4 admin security, signed session cookies, route guards, and review.

---

## Where AI Accelerated Development
1. **Boilerplate & UI Scaffolding (`S1`, `S2`):** Generated initial FastAPI lifespan setup, SQLAlchemy 2.0 `Entry` model, responsive editorial CSS (`app/static/style.css`), and Jinja2 templates (`base.html`, `index.html`, `result.html`, `admin_login.html`, `admin_dashboard.html`).
2. **Test-First Coverage (`S2`, `S3`):** Generated parametrized `pytest` suites across parsing, AI failure modes, input validation, and route integration.

---

## Where Human Review & Manual Engineering Were Critical
1. **Hand-Written Core Validation (`app/validation.py`):** Wrote `normalise_contact()` and `validate_submission()` by hand against a 69-test TDD suite to guarantee full ownership over input hygiene, multi-field error aggregation (`HTTP 422`), email lowercasing, Indian/E.164 phone normalisation, and explicit consent checks.
2. **Hand-Written Security Tests (`tests/test_security.py`):** Wrote all 9 unit tests covering constant-time credential verification, non-ASCII handling, per-IP rate limiting, injectable monotonic clock window expiry, and failure reset.
3. **Zero-Leak Privacy Guardrails:** Kept sequential `id` internal-only, exposing only `secrets.token_urlsafe(16)` (`public_id`) on `/result/{public_id}` and hiding user `contact`, `city`, full `story`, and internal `ai_error` / `ai_reason` fields from public templates.

---

## Specific AI Mistakes Caught & Rejected (`S1`–`S4`)
- **Exception Chain Text Leak (`S1` spec):** Initial parser/client spec did not strip exception chains (`raise ... from exc`), allowing raw user story text and headers to appear in tracebacks. Caught in review and enforced with `raise ... from None` + traceback assertions.
- **Deprecated Groq Model IDs (`S1` / `S3`):** Suggested Llama model IDs returned `http_404` against live Groq `/models`. Caught via live API test and replaced with `openai/gpt-oss-20b`.
- **Unsupported `response_format` (`S3`):** Passing `"response_format": {"type": "json_object"}` returned `http_400` on Groq. Caught on live request and removed in favour of strict prompt instructions + Pydantic parsing.
- **Reasoning Token JSON Truncation (`S3`):** `max_tokens=200` truncated JSON output mid-string because `openai/gpt-oss-20b` uses ~166 reasoning tokens first. Caught by parser tests and raised to `max_tokens=500`.
- **Story Max Length (`2000` vs `300`):** Initial validation and UI counter used 2,000 characters instead of the brief's 300-character maximum. Caught in Phase 4 review and fixed across `app/validation.py`, `index.html`, and tests.
- **Rejected Dependency (`httpx2`):** Starlette's `TestClient` emitted a deprecation warning suggesting `httpx2`; rejected installing an unapproved/unneeded package.

- **Imprecise Sabotage Prediction (S4):** Predicted that removing the CSRF check would fail both Test 9 and Test 13/14; only Test 9 failed (400 == 403) because Tests 13 and 14 send valid tokens.
