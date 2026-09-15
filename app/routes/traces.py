'''
    Trace Replay lets you take an old request, run that exact request through the current system again, and compare the new execution
    with the original without destroying the original evidence.
    It allows us to reproduce historical requests through the current pipeline, which is useful for debugging incidents and validating whether changes to security, prompts, models, or other pipeline components actually changed the behavior.
'''

import time
import uuid
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from groq import GroqError
from app.database.database import get_db
from app.tracing.tracer import get_trace, get_events, start_trace, complete_trace, log_event
from app.exceptions import TraceNotFoundError, PromptInjectionDetectedError, RateLimitExceededError, LLMProviderError
from app.security.prompt_guard import check_prompt_injection
from app.security.pii import mask_pii
from app.security.rate_limit import check_rate_limit
from app.llm.groq_client import call_groq, MODEL_NAME
from app.schemas import ChatResponse
from app.routes.chat import get_client_id 
from app.security.auth import verify_api_key

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
async def replay_trace(trace_id: str, request: Request, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    original_trace = get_trace(db, trace_id)

    if original_trace is None:
        raise TraceNotFoundError(trace_id)

    new_trace_id = str(uuid.uuid4())
    client_id = get_client_id(request)

    start_trace(db, new_trace_id, MODEL_NAME, original_trace.prompt)
    log_event(db, new_trace_id, "REQUEST_STARTED")
    log_event(db, new_trace_id, "REPLAY_OF_" + trace_id)

    log_event(db, new_trace_id, "SECURITY_CHECK")

    if not check_rate_limit(client_id):
        log_event(db, new_trace_id, "RATE_LIMIT_BLOCKED")
        raise RateLimitExceededError(new_trace_id)

    if check_prompt_injection(original_trace.prompt):
        log_event(db, new_trace_id, "PROMPT_INJECTION_BLOCKED")
        raise PromptInjectionDetectedError(new_trace_id)

    safe_message = mask_pii(original_trace.prompt)

    log_event(db, new_trace_id, "LLM_REQUEST")
    llm_start = time.perf_counter()
    try:
        result = call_groq(safe_message)
    except GroqError as e:
        log_event(db, new_trace_id, "LLM_ERROR")
        raise LLMProviderError(new_trace_id, reason=str(e))
    llm_latency_ms = round((time.perf_counter() - llm_start) * 1000, 2)
    log_event(db, new_trace_id, "LLM_RESPONSE")

    complete_trace(
        db=db,
        trace_id=new_trace_id,
        prompt=safe_message,
        response=result["text"],
        status="success",
        llm_latency_ms=llm_latency_ms,
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
        total_tokens=result["total_tokens"],
    )
    log_event(db, new_trace_id, "REQUEST_COMPLETED")

    return ChatResponse(
        response=result["text"],
        trace_id=new_trace_id
    )