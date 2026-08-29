from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session 
from app.database.database import get_db
from app.tracing.tracer import get_trace
from app.exceptions import TraceNotFoundError

router = APIRouter()

@router.get("/traces/{trace_id}")
async def read_trace(trace_id: str, db: Session = Depends(get_db)):
    trace = get_trace(db, trace_id)

    if trace is None:
        raise TraceNotFoundError(trace_id)

    return {
        "trace_id": trace.trace_id,
        "model": trace.model,
        "status": trace.status,
        "latency_ms": trace.latency_ms,
        "llm_latency_ms": trace.llm_latency_ms,
        "prompt_tokens": trace.prompt_tokens,
        "completion_tokens": trace.completion_tokens,
        "total_tokens": trace.total_tokens,
        "prompt": trace.prompt,
        "response": trace.response,
        "started_at": trace.started_at,
        "completed_at": trace.completed_at,
    }