# Kadak Chai Co. — `#MyChaiBreak` Campaign Web App

A full-stack campaign web application for **Kadak Chai Co. (`#MyChaiBreak`)**. Visitors share a 300-character chai memory, an AI moderation pipeline screens the entry and generates a short editorial caption, and approved stories publish immediately to the public campaign wall while keeping all personal details private.

---

## Key Features & Architecture

- **Public Submission & Campaign Wall (`GET /`, `POST /submit`, `GET /result/{public_id}`):**
  - Post/Redirect/Get (`303`) submission flow with server-side validation (`app/validation.py`) and a live 300-character counter.
  - Public wall and result pages expose **only the contributor's first name and AI-generated caption**—never email/phone contact details, city, full story text, or internal moderation metadata.
  - Public result links use random 22-character URL-safe tokens (`secrets.token_urlsafe(16)`), keeping sequential database IDs internal.
- **AI Moderation with Graceful Fallback (`app/ai/`):**
  - Supports `AI_PROVIDER=mock` (deterministic offline testing) and `AI_PROVIDER=real` (OpenAI-compatible Groq Chat Completions API using `openai/gpt-oss-20b`).
  - Strict Pydantic v2 schema validation (`AIResult`: `decision`, `category` in `{funny, nostalgic, wholesome, other}`, `caption` of 1–12 words, `reason`).
  - Any API timeout, `429` rate limit, network error, or malformed JSON automatically routes the submission to `status="pending_review"` with a short sanitized error code (`ai_error`)—never crashing the user request or leaking story text into logs.
- **Admin Moderation Dashboard (`GET /admin`, `POST /admin/entries/{id}/override`):**
  - Protected by signed `HttpOnly`, `SameSite=Lax` session cookies (`itsdangerous.URLSafeTimedSerializer`), a router-level `require_admin` dependency guard, and an in-memory per-IP `LoginLimiter` (5 failed attempts trigger a 15-minute `429` lockout).
  - Filterable queue (`all`, `pending_review`, `approved`, `rejected`) with CSRF-protected manual overrides (`secrets.compare_digest`), open-redirect protection on `back` URLs, and a rule requiring a fresh 1–12 word caption whenever an admin overrides an AI-rejected or caption-less entry to `approved`.

---

## Local Setup (Under 5 Minutes)

### 1. Clone & Create Virtual Environment

```bash
git clone <your-repo-url>
cd kadak_chai
python -m venv .venv
