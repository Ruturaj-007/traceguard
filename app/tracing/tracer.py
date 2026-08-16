'''
    ARCHITECTURE BEFORE ADDING INFRA COMPLEXITY
    temporary mini DB after 1 req it might contain 
    {
        "abc123": {
            "trace_id": "abc123",
            "model": "llama-3.1-8b-instant",
            "prompt": "Explain RAG",
            "response": "RAG means...",
            "status": "success",
            "started_at": "...",
            "completed_at": "...",
            "latency_ms": 742.5
        }
    }
'''

from datetime import datetime, timezone

# Temporary in-memory store. Replaced by PostgreSQL in Feature 9.
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
    }


def complete_trace(
    trace_id: str,
    prompt: str,
    response: str,
    status: str,
    llm_latency_ms: float,
) -> None:
    trace = traces[trace_id]
    trace["prompt"] = prompt
    trace["response"] = response
    trace["status"] = status
    trace["completed_at"] = datetime.now(timezone.utc)
    trace["llm_latency_ms"] = llm_latency_ms

    delta = trace["completed_at"] - trace["started_at"]
    trace["latency_ms"] = round(delta.total_seconds() * 1000, 2)


def get_trace(trace_id: str) -> dict | None:
    return traces.get(trace_id)