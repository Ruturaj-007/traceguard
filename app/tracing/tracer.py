from datetime import datetime, timezone

# Temporary in-memory store. Replaced by PostgreSQL
traces: dict[str, dict] = {}


def start_trace(trace_id: str, model: str) -> None:
    traces[trace_id] = {
        "trace_id": trace_id,
        "model": model,
        "prompt": None,
        "response": None,
        "status": "started",
        "started_at": datetime.now(timezone.utc),
        "completed_at": None,
        "latency_ms": None,
        "llm_latency_ms": None,
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
    }


def complete_trace(
    trace_id: str,
    prompt: str,
    response: str,
    status: str,
    llm_latency_ms: float,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    total_tokens: int | None,
) -> None:
    trace = traces[trace_id]
    trace["prompt"] = prompt
    trace["response"] = response
    trace["status"] = status
    trace["completed_at"] = datetime.now(timezone.utc)
    trace["llm_latency_ms"] = llm_latency_ms
    trace["prompt_tokens"] = prompt_tokens
    trace["completion_tokens"] = completion_tokens
    trace["total_tokens"] = total_tokens

    delta = trace["completed_at"] - trace["started_at"]
    trace["latency_ms"] = round(delta.total_seconds() * 1000, 2)


def get_trace(trace_id: str) -> dict | None:
    return traces.get(trace_id)