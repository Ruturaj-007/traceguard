import uuid
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.tracing.tracer import get_trace, get_events, start_trace, log_event
from app.exceptions import TraceNotFoundError
from app.llm.groq_client import MODEL_NAME
from app.schemas import ChatResponse
from app.security.auth import verify_api_key
from app.routes.chat import get_client_id
from app.pipeline import run_chat_pipeline

router = APIRouter()


@router.get("/traces/{trace_id}")
async def read_trace(trace_id: str, db: Session = Depends(get_db)):
    trace = get_trace(db, trace_id)

    if trace is None:
        raise TraceNotFoundError(trace_id)

    events = get_events(db, trace_id)

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
        "events": [
            {"event": e.event_name, "timestamp": e.created_at}
            for e in events
        ],
    }


@router.post("/traces/{trace_id}/replay", response_model=ChatResponse)
async def replay_trace(
    trace_id: str,
    request: Request,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    original_trace = get_trace(db, trace_id)

    if original_trace is None:
        raise TraceNotFoundError(trace_id)

    new_trace_id = str(uuid.uuid4())
    client_id = get_client_id(request)

    start_trace(db, new_trace_id, MODEL_NAME, original_trace.prompt)
    log_event(db, new_trace_id, "REQUEST_STARTED")
    log_event(db, new_trace_id, "REPLAY_OF_" + trace_id)

    result = run_chat_pipeline(db, new_trace_id, original_trace.prompt, client_id)

    return ChatResponse(**result)