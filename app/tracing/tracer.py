from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import Trace


def start_trace(db: Session, trace_id: str, model: str) -> None:
    trace = Trace(
        trace_id=trace_id,
        model=model,
        status="started",
        started_at=datetime.now(timezone.utc),
    )
    db.add(trace)
    db.commit()


def complete_trace(
    db: Session,
    trace_id: str,
    prompt: str,
    response: str,
    status: str,
    llm_latency_ms: float,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    total_tokens: int | None,
) -> None:
    trace = db.query(Trace).filter(Trace.trace_id == trace_id).first()

    trace.prompt = prompt
    trace.response = response
    trace.status = status
    trace.completed_at = datetime.now(timezone.utc)
    trace.llm_latency_ms = llm_latency_ms
    trace.prompt_tokens = prompt_tokens
    trace.completion_tokens = completion_tokens
    trace.total_tokens = total_tokens

    delta = trace.completed_at - trace.started_at
    trace.latency_ms = round(delta.total_seconds() * 1000, 2)

    db.commit()


def get_trace(db: Session, trace_id: str) -> Trace | None:
    return db.query(Trace).filter(Trace.trace_id == trace_id).first()