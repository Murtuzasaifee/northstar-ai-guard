# Northstar AI Guard

An experimental FastAPI project for exploring how a RAG chatbot can defend itself against common LLM security risks.

The app is framed as an internal assistant for the fictional company **Northstar Dynamics**, but the real purpose is the security pipeline around it: request validation, prompt-injection scanning, hardened system prompts, authentication, rate limiting, token budgeting, moderation, RAG spotlighting, PDF ingestion checks, and structured output validation.

This is not a production security product. It is a practical lab for testing ideas, breaking assumptions, and observing how layered controls behave in a working LLM application.

## What Makes This Project Useful

Most RAG chatbot examples stop at "retrieve documents and answer questions." This project focuses on the uncomfortable parts that appear once users, documents, and model outputs become untrusted.

It gives you:

- A complete authenticated chat API built with FastAPI.
- A RAG knowledge base backed by ChromaDB.
- Startup ingestion for bundled text documents.
- Secure PDF upload flow with validation before indexing.
- Redis-backed rate limiting and daily token budgets.
- Input and output moderation hooks through `llm-guard`.
- Prompt-injection and toxic-content scanning.
- XML-style RAG spotlighting to separate retrieved data from instructions.
- Pydantic output validation with retry handling.
- A focused pytest suite for the deterministic security layers.
- A separate curl-based API testing guide in `API_TESTING.md`.

## System At A Glance

```text
Client
  |
  v
FastAPI routes
  |
  +-- Auth and rate limiting
  +-- Input validation
  +-- Token budget checks
  +-- Input restructuring
  +-- LLM Guard scanners
  +-- Content moderation
  +-- RAG retrieval from ChromaDB
  +-- Spotlighted context wrapping
  +-- Hardened system prompt
  +-- OpenAI model call
  +-- Output moderation
  +-- Pydantic response validation
  |
  v
JSON response
```

The app deliberately keeps each layer small and easy to inspect. That makes it easier to disable, test, or replace a single control while experimenting.

## Security Layers

| Layer | Component | Main file | Purpose |
| --- | --- | --- | --- |
| 1 | Input validation | `app/models/request.py` | Reject empty messages, oversized payloads, and simple injection patterns before work begins. |
| 2 | LLM Guard scanners | `app/security/input_guard.py` | Detect semantic prompt injection, toxicity, banned topics, and token-limit abuse. |
| 3 | Hardened system prompt | `app/security/system_prompt.py` | Define trust boundaries, refusal rules, and the expected JSON contract. |
| 4 | Auth and rate limiting | `app/middleware/auth.py`, `app/middleware/rate_limiter.py` | Require JWT access and throttle request bursts through Redis. |
| 5 | Input restructuring | `app/security/input_restructuring.py` | Count tokens and truncate or summarize large inputs before model calls. |
| 6 | Token budgets | `app/security/token_budget.py` | Enforce a daily token allowance per user. |
| 7 | Content moderation | `app/security/content_moderation.py` | Moderate both incoming user text and outgoing model text. |
| 8 | RAG spotlighting | `app/rag/spotlighting.py` | Wrap retrieved chunks as data so document text is not treated as instructions. |
| 9 | Output validation | `app/security/output_validator.py` | Parse and validate model JSON responses, with retry support on malformed output. |

## Tech Stack

| Area | Choice |
| --- | --- |
| API framework | FastAPI + Uvicorn |
| Validation | Pydantic v2 |
| LLM provider | OpenAI API |
| Default model | `gpt-5.4-nano` |
| Vector store | ChromaDB |
| PDF parsing | pypdf |
| Guardrails | llm-guard |
| Rate limiting and budgets | Redis |
| Auth | JWT with PyJWT |
| Token counting | tiktoken |
| Tests | pytest |
| Package workflow | uv |

## Repository Layout

```text
northstar-ai-guard/
  app/
    main.py                    FastAPI app setup and router registration
    config.py                  Environment-driven settings
    models/request.py          Chat request and response schemas
    middleware/
      auth.py                  JWT helpers and in-memory user store
      rate_limiter.py          Redis sliding-window limiter
    routes/
      auth.py                  Register and login endpoints
      chat.py                  Chat endpoint entry point
      documents.py             PDF upload and listing endpoints
    services/
      llm_service.py           Main chat security pipeline
    security/
      input_guard.py           llm-guard input scanners
      content_moderation.py    Input and output moderation
      system_prompt.py         Assistant policy and trust boundaries
      input_restructuring.py   Token counting and input shrinking
      token_budget.py          Redis token accounting
      output_validator.py      LLM JSON parsing and validation
    rag/
      vectorstore.py           ChromaDB setup and retrieval
      spotlighting.py          Retrieved-context wrapping
      pdf_ingestion.py         PDF validation, extraction, and indexing
      documents/               Built-in fictional company documents
  tests/                       Unit tests for deterministic layers
  API_TESTING.md               End-to-end curl scenarios
  AGENTS.md                    Project context for AI coding assistants
  docker-compose.yml           Redis service
  pyproject.toml               Python package metadata
  uv.lock                      Locked dependency graph
```

## Requirements

- Python 3.12 or newer
- Docker, for Redis
- `uv`
- OpenAI API key

Install `uv` with your preferred system package method before continuing. This project uses `uv` for Python dependency operations.

## Setup

```bash
git clone https://github.com/Murtuzasaifee/northstar-ai-guard.git
cd northstar-ai-guard

python3.12 -m venv .venv
source .venv/bin/activate

uv pip install -e ".[dev]"
cp .env.example .env
```

Edit `.env` and set at least:

```dotenv
OPENAI_API_KEY=sk-your-real-key
JWT_SECRET=replace-this-with-a-random-secret
```

Start Redis:

```bash
docker compose up -d redis
```

Run the API:

```bash
uv run python main.py
```

Open:

- API root: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Configuration

The app reads settings from `.env` through `pydantic-settings`.

| Variable | Default | Notes |
| --- | --- | --- |
| `OPENAI_API_KEY` | `sk-placeholder` | Required for real model calls. |
| `OPENAI_MODEL` | `gpt-5.4-nano` | Model used by the chat service. |
| `REDIS_URL` | `redis://localhost:6379/0` | Used for rate limiting and token budgets. |
| `JWT_SECRET` | `change-this-to-a-secure-random-string` | Replace before running outside local experiments. |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm. |
| `JWT_EXPIRATION_MINUTES` | `60` | Access-token lifetime. |
| `MAX_INPUT_LENGTH` | `2000` | Character limit for user messages. |
| `MAX_TOKENS_PER_USER_DAILY` | `100000` | Daily per-user token budget. |
| `RATE_LIMIT_PER_MINUTE` | `20` | Per-user request limit. |
| `CHROMA_PERSIST_DIR` | `./chroma_data` | Local ChromaDB persistence path. |

## API Workflow

Register a user:

```bash
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"murtuza","password":"password123"}'
```

Login and capture a token:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"murtuza","password":"password123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

Send a chat request:

```bash
curl -s -X POST http://localhost:8000/chat/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"What products does Northstar Dynamics offer?"}' \
  | python3 -m json.tool
```

Upload a PDF into the RAG index:

```bash
curl -s -X POST http://localhost:8000/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample.pdf" \
  | python3 -m json.tool
```

List uploaded PDFs:

```bash
curl -s http://localhost:8000/documents/ \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
```

## Endpoints

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/` | No | App metadata and enabled security features. |
| `GET` | `/health` | No | Lightweight health check. |
| `POST` | `/auth/register` | No | Create an in-memory user and return a JWT. |
| `POST` | `/auth/login` | No | Authenticate and return a JWT. |
| `POST` | `/chat/` | Yes | Run a user message through the full security pipeline. |
| `POST` | `/documents/upload` | Yes | Validate, parse, and index a PDF. |
| `GET` | `/documents/` | Yes | List uploaded PDFs stored in ChromaDB. |

## RAG Behavior

At startup, the app indexes four fictional company documents:

| Document | Theme | Why it exists |
| --- | --- | --- |
| `hr_policy.txt` | HR policies and employee details | Tests sensitive-data handling and policy questions. |
| `it_handbook.txt` | IT support procedures | Tests operational Q&A and internal-system references. |
| `product_specs.txt` | Product catalog and roadmap | Tests product retrieval and unreleased-information handling. |
| `financial_report.txt` | Fictional financial data | Tests numeric retrieval and confidentiality boundaries. |

For each chat request, the service retrieves the most relevant chunks, wraps them in a `retrieved_context` block, and instructs the model to treat those chunks as data rather than commands. This is the project's main defense against indirect prompt injection through documents.

## PDF Upload Safety Checks

PDF upload is intentionally stricter than a typical demo endpoint. A file must pass:

1. JWT authentication.
2. Shared rate limit check.
3. MIME type validation.
4. Maximum size check, currently 10 MB.
5. `%PDF` magic-byte validation.
6. Filename sanitization.
7. Text extraction through `pypdf`.
8. Rejection of encrypted or image-only PDFs.
9. Content moderation on the extracted sample.

If the same sanitized filename is uploaded again, the vector-store records are refreshed with `upsert`.

## Running Tests

Run the full deterministic test suite:

```bash
uv run python -m pytest tests/ -v
```

Current coverage focuses on:

- Input validation
- Auth helpers
- System prompt constraints
- Input restructuring
- RAG spotlighting
- Output validation

The test suite currently avoids full `llm-guard` scanner and moderation tests because those can trigger larger model downloads on first run.

## Experiment Ideas

Try changing one control at a time and observe how behavior changes:

- Lower `MAX_INPUT_LENGTH` and send oversized messages.
- Lower `RATE_LIMIT_PER_MINUTE` and fire concurrent requests.
- Lower `MAX_TOKENS_PER_USER_DAILY` and exhaust a test account.
- Add an instruction-injection sentence inside a PDF and upload it.
- Temporarily remove RAG spotlighting and compare responses.
- Force malformed model output and watch `output_validator.py` retry.
- Adjust the system prompt and rerun the system-prompt tests.

For ready-made curl commands, use `API_TESTING.md`.

## Design Notes

- The user store is intentionally in memory. Restarting the app clears registered users.
- ChromaDB is file-backed and local, which keeps setup simple.
- Redis is used where atomic counters matter: rate limits and token budgets.
- PDF parsing uses `pypdf` directly instead of a larger framework.
- The security layers are explicit modules instead of a hidden framework abstraction.
- The sample company data is fictional and intentionally includes sensitive-looking values for testing.

## Limitations

This project is useful for experimentation, but it is not production-ready as-is.

Known gaps:

- No persistent user database.
- No password policy beyond basic hashing.
- No role-based access control.
- No real tenant isolation.
- No admin UI for uploaded documents.
- No streaming response support.
- No production observability stack.
- LLM security behavior can vary by model and prompt changes.

