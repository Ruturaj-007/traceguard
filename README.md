# TraceGuard

**A real-time observability and security gateway for LLM requests.**

TraceGuard sits between an application and an LLM provider (Groq/Llama), tracing every request, blocking obvious prompt injection attempts, masking PII before it leaves your server, enforcing rate limits, and persisting a full queryable history of what happened — so a failed or malicious request can be debugged after the fact instead of disappearing into a log file.

**Live demo:** https://trace-guard-api.netlify.app
**API:** https://traceguard-api-n6pz.onrender.com
**Interactive API docs (Swagger):** https://traceguard-api-n6pz.onrender.com/docs

> The API runs on Render's free tier and spins down after inactivity — the first request after idle time can take 30–60 seconds to wake up. This is expected, not a bug.

---

## 1. Problem

Once an LLM feature reaches production, three things go wrong in practice:

1. Someone eventually tries to jailbreak it or extract the system prompt.
2. Users paste real personal data (emails, phone numbers) into a chat box that forwards straight to a third-party API.
3. When something breaks, there's no way to answer "what actually happened on this one request" without grepping raw logs.

## 2. Solution

TraceGuard is a lightweight FastAPI gateway that sits in front of the LLM call and handles all three:

- Blocks and masks risky input **before** it reaches the model
- Records a structured, queryable trace of every request — latency, tokens, status, and a full event timeline
- Lets you replay any historical request (including blocked ones) through the current pipeline
- Rate-limits per client using Redis, so it holds up correctly even behind multiple API instances

This is the same category of tool as Portkey, Helicone, or the request-gateway layer of LangSmith/Arize — built small, from scratch, to actually understand how each piece works rather than importing a platform.

## 3. Architecture

```
Client
  |
  | POST /v1/chat/completions  (X-API-Key required)
  v
FastAPI Gateway
  |
  +--- API Key Auth
  +--- Rate Limit (Redis, fixed window, 10 req/min/client)
  +--- Prompt Injection Check (rule-based)
  +--- PII Masking (regex: email, phone)
  |
  v
Groq (Llama 3 / gpt-oss-20b)
  |
  v
Response
  |
  +--- latency captured (perf_counter)
  +--- tokens captured (prompt/completion/total)
  +--- trace + event timeline written
  v
PostgreSQL (Neon)
  |
  v
GET /traces/{trace_id}   — full trace + event timeline, no auth required (read-only)
POST /traces/{trace_id}/replay — re-run the original prompt through the live pipeline
```

## 4. Request lifecycle

Every request that reaches `/v1/chat/completions` passes through the same pipeline, and every stage is logged as an event tied to that request's `trace_id`:

```
REQUEST_STARTED → SECURITY_CHECK → [RATE_LIMIT_BLOCKED | PROMPT_INJECTION_BLOCKED] → LLM_REQUEST → [LLM_ERROR | LLM_RESPONSE] → REQUEST_COMPLETED
```

If a request is blocked or fails, the event timeline simply stops at the point of failure — the trace record stays honest (`status: "started"`, no fabricated response) rather than pretending the request succeeded. This is what makes `GET /traces/{trace_id}` useful for debugging: you can tell exactly where and why a request died without reading a single line of code.

## 5. Tech stack

```
Python · FastAPI · SQLAlchemy
Groq API (gpt-oss-20b)
PostgreSQL (Neon, serverless)
Redis (Upstash, for rate limiting)
Docker + Docker Compose
pytest (guardrail eval suite)
Deployed: Render (API) + Netlify (static demo frontend)
```

## 6. Example trace

```json
{
  "trace_id": "e689abf8-21e4-4eb0-83ec-107b785f0d5b",
  "model": "openai/gpt-oss-20b",
  "status": "success",
  "latency_ms": 9593.67,
  "llm_latency_ms": 2672.2,
  "prompt_tokens": 76,
  "completion_tokens": 1740,
  "total_tokens": 1816,
  "events": [
    {"event": "REQUEST_STARTED", "timestamp": "2026-09-17T09:58:27Z"},
    {"event": "SECURITY_CHECK", "timestamp": "2026-09-17T09:58:27Z"},
    {"event": "LLM_REQUEST", "timestamp": "2026-09-17T09:58:29Z"},
    {"event": "LLM_RESPONSE", "timestamp": "2026-09-17T09:58:32Z"},
    {"event": "REQUEST_COMPLETED", "timestamp": "2026-09-17T09:58:34Z"}
  ]
}
```

`latency_ms` is the full request time; `llm_latency_ms` is just the Groq call — the gap between the two is TraceGuard's own overhead (security checks, tracing, DB writes), tracked separately so a slow request can be attributed to the right layer.

## 7. Security — and its measured limits

TraceGuard runs two MVP guardrails before any prompt reaches Groq:

- **Prompt injection firewall** — a rule-based check against a short list of known jailbreak phrases (`ignore previous instructions`, `reveal system prompt`, etc.), case-insensitive.
- **PII masking** — regex-based detection of emails and 10-digit phone numbers, replaced with `[EMAIL_REDACTED]` / `[PHONE_REDACTED]` before the prompt is sent to Groq or stored.

Both are intentionally simple, and both were measured against a labeled eval set rather than assumed to work — see [`tests/eval_dataset.py`](./tests/eval_dataset.py) and [`tests/test_guardrails.py`](./tests/test_guardrails.py).

**Prompt injection — 7/10 exact catches:**
| Result | Case |
|---|---|
| ✅ Pass | Exact phrase + case-insensitive matches |
| ⚠️ Known gap | `"disregard everything you were told before"` — paraphrase, not caught |
| ⚠️ Known gap | `"pretend your guidelines don't apply"` — semantic bypass, not caught |
| ⚠️ Known gap | `"jailbroken"` vs `"jailbreak"` — word-form variant, not caught |

**PII masking — 3/5 correct redactions:**
| Result | Case |
|---|---|
| ✅ Pass | Standard email and 10-digit phone patterns |
| ⚠️ Known false positive | A 10-digit order ID gets masked as a phone number |

This is the honest finding: **rule-based, exact-match detection catches literal phrasing but misses paraphrases, word-form variants, and produces false positives on any numeric string that happens to match a phone-number shape.** A production system would need NER-based detection (e.g. Microsoft Presidio) and a semantic-similarity or classifier-based injection detector — documented here as a known next step, not silently ignored.

## 8. Failure handling

| Failure | Behavior |
|---|---|
| Groq API errors/timeouts | Caught, converted to `LLMProviderError`, returns clean `502` — trace timeline stops at `LLM_ERROR` |
| Redis unreachable | **Not yet handled** — `check_rate_limit()` will raise unhandled, currently a real gap (see Trade-offs) |
| Postgres/Neon connection drop | Neon's serverless Postgres silently closes idle connections; fixed with `pool_pre_ping=True` and `pool_recycle=300` on the SQLAlchemy engine so stale connections are detected and replaced before use, not after a query fails |
| Prompt injection detected | Request rejected before it reaches Groq (cost + safety — never pay for a request you're about to block) |
| PII detected | Not rejected — masked, then the masked version is sent onward |
| Rate limit exceeded | `429`, enforced via Redis `INCR` + `EXPIRE` (fixed 60s window, 10 req/client) |
| Invalid/missing trace_id | `404 trace_not_found` |

## 9. Trade-offs — what was intentionally not built, and why

- **Rule-based guardrails, not ML-based.** A regex/keyword firewall is transparent and fast to reason about for an MVP; it is not research-grade, as the eval results above show plainly.
- **Fixed-window rate limiting, not sliding window/token bucket.** Simpler to implement correctly; has a known boundary-burst edge case (a client can send up to ~2x the limit across a window boundary). Chosen deliberately over more complex alternatives given the project's scope.
- **Client identity via `X-Forwarded-For` with a direct-IP fallback**, not authenticated user IDs. Reasonable behind a real reverse proxy; still spoofable if the proxy isn't configured to overwrite the header, which is the correct fix in a real deployment.
- **Single hardcoded model/provider (Groq only).** A real gateway would abstract multiple providers; this was intentionally out of scope to keep the project buildable in the available time.
- **API key auth is a single static key, not per-user keys or OAuth.** Closes the "anyone can hit this and burn your Groq quota" gap cheaply; a real product needs proper multi-tenant auth.
- **`Redis` failures are unhandled.** If Redis is unreachable, `/v1/chat/completions` will 500 instead of failing open or closed gracefully — a known, undone item, not an oversight I'm unaware of.
- **CORS is fully open (`allow_origins=["*"]`)** on the deployed API, to let the static demo frontend call it from a different domain. Not appropriate for a product handling real user data.
- **Replay duplicates some routing logic** between `chat.py` and `traces.py` at the route layer (the shared pipeline itself was extracted into `app/pipeline.py` once the duplication became real, rather than abstracted upfront).

## 10. Two real bugs hit while building this

**1. Neon connection drops mid-session.** SQLAlchemy's default connection pool kept handing out connections that Neon's serverless Postgres had already silently closed after a period of idleness, producing `SSL connection has been closed unexpectedly` errors on requests that otherwise looked fine. Fixed with `pool_pre_ping=True` (ping before use) and `pool_recycle=300` (force-refresh connections older than 5 minutes).

**2. Replaying a blocked trace returned a false `trace_not_found`.** The original pipeline only saved a trace's `prompt` field inside `complete_trace()` — which never runs for a request blocked by rate-limiting or the injection firewall. So a blocked trace's `prompt` stayed `NULL`, and attempting to replay it looked identical to a genuinely missing trace. Fixed by saving the prompt immediately at `start_trace()` time, as soon as it's known — which also made replaying previously-blocked requests possible, a legitimately useful case (e.g. confirming a firewall fix still blocks an old attack).

## 11. Guardrail eval suite

```
pytest tests/test_guardrails.py -v -s
```

Runs the security functions directly (no server, no Groq calls, no DB — fast, free, deterministic) against the labeled dataset in `tests/eval_dataset.py`. Known limitations are asserted as expected outcomes, not silently passed — the suite is designed to catch **regressions** (something that used to work breaking), not to hide known gaps.

## 12. Running locally

```bash
git clone https://github.com/Ruturaj-007/traceguard
cd traceguard
cp .env.example .env   # fill in GROQ_API_KEY, DATABASE_URL, REDIS_URL, API_KEY
docker compose up --build
```

API available at `http://127.0.0.1:8000`, docs at `http://127.0.0.1:8000/docs`.

Frontend:
```bash
cd frontend
python -m http.server 5500
```
Open `http://127.0.0.1:5500` (update `API_BASE` in `index.html` to `http://127.0.0.1:8000` for local testing).

---

## Interview prep

**Explain this project in 60 seconds.**
TraceGuard is a FastAPI gateway that sits between an app and an LLM provider. It rate-limits per client via Redis, runs a prompt-injection check and PII masking before the request reaches Groq, and records a full trace — latency, token counts, and a step-by-step event timeline — into Postgres. Every trace is retrievable and replayable by ID, so a failed or blocked request can be debugged or re-tested later. I measured the guardrails against a labeled eval set rather than assuming they worked, and documented exactly where they fall short.

**Why FastAPI?** Async support where it matters (I/O-bound calls to Groq/Postgres/Redis), automatic request validation via Pydantic, and free interactive docs (Swagger) generated from the same type hints used for validation.

**Why Redis for rate limiting, not a Python dict?** `INCR` is atomic — no race condition under concurrent requests, which a plain dict can't guarantee. More importantly, a dict lives in one process's memory; behind multiple API instances (a load balancer, horizontal scaling), each instance would have its own separate counter and the rate limit would be meaningless. Redis is a single shared store every instance reads and writes.

**Why PostgreSQL?** Relational integrity (a foreign key ties `trace_events` to `traces`, so an event can't reference a trace that doesn't exist), and it needed to survive process restarts — an in-memory dict (my first version, before Feature 9) loses everything on redeploy.

**Why async, and why not everywhere?** Routes that call Groq/Postgres are `async def` because they're I/O-bound — the event loop can serve other requests while waiting on the network. The Groq SDK call itself is synchronous under the hood; FastAPI runs it in a threadpool automatically, which works but has a real limit — at high concurrency this threadpool becomes a bottleneck, and the honest fix is Groq's async client, not just marking more functions `async`.

**Why custom exceptions instead of `return JSONResponse` everywhere?** An exception can be raised from anywhere in the call stack — deep inside a security check three functions away from the route — without threading response-building logic through every layer. The place that detects a problem doesn't need to know how to format an HTTP response; it just raises and walks away.

**How does tracing work?** Every request gets a UUID `trace_id` at the start. Each pipeline stage logs an event row (`trace_events`, foreign-keyed to `traces`) with that ID and a timestamp. `GET /traces/{trace_id}` returns the trace plus its ordered event list — so you can see exactly which stage a request reached before it stopped, without reading logs.

**What happens if Groq goes down?** The call is wrapped in try/except catching `GroqError` (the Groq SDK's base exception class); on failure it's converted to my own `LLMProviderError` and returned as a clean `502`, with the trace timeline stopping at `LLM_ERROR` instead of the process crashing with an unhandled 500. I tested this by deliberately invalidating my API key.

**What happens if PostgreSQL goes down?** Currently an unhandled exception — a real, acknowledged gap (see Trade-offs). The one resilience measure in place is `pool_pre_ping`/`pool_recycle`, which handles Neon's specific behavior of silently closing idle connections, but a full Postgres outage isn't gracefully degraded yet.

**How would you make PII detection production-grade?** Move from regex to NER-based detection (e.g. Microsoft Presidio), which understands context rather than matching fixed shapes — regex can't tell a 10-digit order ID from a phone number, which is exactly the false positive my eval suite documents.

**How would you scale this?** Add a load balancer in front of multiple API instances — this already works correctly for rate limiting and DB writes since both are backed by shared external stores (Redis, Postgres), not local memory. Beyond that: move to async Groq calls to avoid threadpool contention, add structured logging correlated by `trace_id` for cross-instance debugging, and move rate-limit/security checks earlier if they become a bottleneck.

**What would you change if traffic increased 100x?** Sliding-window or token-bucket rate limiting instead of fixed-window (to close the boundary-burst gap), a proper eval/regression pipeline feeding back from real failures (per the incident-runbook pattern used by real observability teams), and multi-provider abstraction so a single provider outage doesn't take the whole gateway down.