# AGENTS.md — northstar-ai-guard Project Context

This file gives AI assistants context about the project so they can contribute effectively without re-exploring the codebase from scratch each session.

---

## What This Project Is

A **security experimentation application** demonstrating 9 LLM security layers in a realistic RAG chatbot. The fictional company is "Northstar Dynamics". Every security feature is intentionally isolated and testable — the goal is experimentation and validation, not production hardening.

- **GitHub:** https://github.com/murtuzasaifee/northstar-ai-guard
- **Owner:** Murtuza Saifee

---

## How to Run

```bash
# 1. Activate virtual environment (already created manually)
source .venv/bin/activate

# 2. Install deps
uv pip install -e .

# 3. Start Redis
docker compose up -d redis

# 4. Set env vars
cp .env.example .env   # then set OPENAI_API_KEY

# 5. Start server
uv run python main.py
# → http://localhost:8000
# → http://localhost:8000/docs (Swagger)
```

**Always use `uv` for package management** — never `pip install` directly.

---

## Key Architecture Decisions

| Decision | Reason |
|----------|--------|
| `gpt-5.4-nano` as LLM model | Cheapest current OpenAI model; good for repeated experiments |
| ChromaDB for vector store | Simple, file-based, no external service needed |
| `pypdf` for PDF parsing | Pure Python, no heavy dependencies (no LangChain/LlamaIndex) |
| Redis for rate limiting + token budgets | Persistent across requests, atomic operations |
| In-memory user store (`fake_users_db`) | Experimentation app — no real DB needed |
| RAG Spotlighting with XML tags | Mitigates indirect prompt injection from retrieved docs |

---

## Project Structure (Critical Files)

```
app/
├── config.py                    # All settings — pydantic-settings, loads .env
├── main.py                      # FastAPI app, router registration, startup event
│
├── models/request.py            # ChatRequest (input validation), ChatResponse (output schema)
│
├── middleware/
│   ├── auth.py                  # JWT auth, get_current_user, fake_users_db (in-memory)
│   └── rate_limiter.py          # Redis sliding-window rate limiter
│
├── security/
│   ├── input_guard.py           # llm-guard scanners: PromptInjection, Toxicity, BanTopics, TokenLimit
│   ├── content_moderation.py    # moderate_input(), moderate_output() — llm-guard
│   ├── system_prompt.py         # Hardened system prompt with trust boundaries
│   ├── input_restructuring.py   # Token counting (tiktoken), truncate/summarize large inputs
│   ├── token_budget.py          # Per-user daily token tracking in Redis
│   └── output_validator.py      # Validates LLM JSON output against ChatResponse schema, retries
│
├── rag/
│   ├── vectorstore.py           # ChromaDB singleton, ingest_documents(), retrieve_context(), _chunk_text()
│   ├── spotlighting.py          # build_spotlighted_context() — wraps chunks in <retrieved_context>
│   ├── pdf_ingestion.py         # ingest_pdf(), list_uploaded_pdfs(), sanitize_filename()
│   └── documents/               # Pre-loaded .txt files (hr_policy, it_handbook, product_specs, financial_report)
│
├── routes/
│   ├── auth.py                  # POST /auth/register, POST /auth/login
│   ├── chat.py                  # POST /chat/ — full 9-layer security pipeline
│   └── documents.py             # POST /documents/upload, GET /documents/
│
└── services/
    └── llm_service.py           # process_chat() — orchestrates the full pipeline
```

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check |
| GET | `/` | No | List 9 security features |
| POST | `/auth/register` | No | Create user, returns JWT |
| POST | `/auth/login` | No | Login, returns JWT |
| POST | `/chat/` | Yes | Full RAG + security pipeline |
| POST | `/documents/upload` | Yes | Upload PDF to RAG knowledge base |
| GET | `/documents/` | Yes | List uploaded PDFs |

---

## The 9 Security Layers

| # | Layer | File | Blocks |
|---|-------|------|--------|
| 1 | Input Validation | `models/request.py` | Oversized, empty, regex injection |
| 2 | LLM Guard | `security/input_guard.py` | Semantic prompt injection, toxicity |
| 3 | Hardened System Prompt | `security/system_prompt.py` | Role switching, prompt leakage |
| 4 | Auth + Rate Limiting | `middleware/auth.py`, `rate_limiter.py` | No token, request flood |
| 5 | Input Restructuring | `security/input_restructuring.py` | Token-bomb inputs |
| 6 | Token Budgets | `security/token_budget.py` | Daily cost runaway |
| 7 | Content Moderation | `security/content_moderation.py` | Harmful input AND output |
| 8 | RAG Spotlighting | `rag/spotlighting.py` | Indirect injection via documents |
| 9 | Output Validation | `security/output_validator.py` | Malformed LLM responses |

---

## Known Compatibility Fixes Applied

These were bugs caused by library version changes — already fixed in the codebase:

| File | Fix |
|------|-----|
| `security/input_guard.py` | `TokenLimit(limit=...)` not `max_tokens=` |
| `security/content_moderation.py` | `scan_output(scanners, prompt, output)` — arg order changed in llm-guard |
| `services/llm_service.py` | `max_completion_tokens=` not `max_tokens=`; removed `temperature` param |
| `security/input_restructuring.py` | tiktoken fallback to `cl100k_base` for unknown model names |
| `models/request.py` | `tokens_used` removed from `ChatResponse` (it's service-level, not LLM output) |

---

## PDF Upload Pipeline

**New in this session.** Files: `app/rag/pdf_ingestion.py`, `app/routes/documents.py`.

Security checks in order:
1. JWT auth
2. Rate limit (shared with `/chat/`)
3. MIME type check
4. File size ≤ 10 MB
5. Magic bytes `%PDF` (catches renamed files)
6. Filename sanitization (prevents path traversal)
7. pypdf text extraction (rejects encrypted/image PDFs)
8. Content moderation on first 5,000 chars

ChromaDB metadata flag `upload: True` distinguishes uploaded PDFs from startup `.txt` docs. IDs prefixed `pdf_` to avoid collisions. Uses `upsert()` so re-upload refreshes content.

---

## Dependencies (pyproject.toml)

Key packages and why they're there:

```
fastapi, uvicorn      — web framework
pydantic, pydantic-settings — validation + config
llm-guard             — ML-based prompt injection / toxicity scanners
openai                — LLM API (gpt-5.4-nano)
chromadb              — vector store for RAG
pypdf                 — PDF text extraction (no LangChain/LlamaIndex)
python-multipart      — required by FastAPI for file uploads
redis                 — rate limiting + token budgets
pyjwt                 — JWT auth
tiktoken              — token counting
```

---

## Testing

```bash
# All 50 unit tests
uv run python -m pytest tests/ -v

# Full integration test (server must be running)
# See API_TESTING.md for complete curl test suite
```

Tests do NOT cover Features 2 (LLM Guard) and 7 (Content Moderation) — those require ~80MB ML model downloads on first run.

---

## Environment Variables (.env)

```dotenv
OPENAI_API_KEY=sk-...          # Required
OPENAI_MODEL=gpt-5.4-nano      # Current model
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=<random-string>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
MAX_INPUT_LENGTH=2000
MAX_TOKENS_PER_USER_DAILY=100000
RATE_LIMIT_PER_MINUTE=20
CHROMA_PERSIST_DIR=./chroma_data
```

---

## Documentation Files

| File | Contents |
|------|----------|
| `README.md` | Full project overview, setup, all security experiment scenarios |
| `API_TESTING.md` | Complete curl test suite for every route and security layer |
| `AGENTS.md` | This file — project context for AI assistants |
