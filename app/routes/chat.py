import time
import uuid
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from app.schemas import ChatRequest, ChatResponse
from app.llm.groq_client import call_groq
from app.tracing.tracer import start_trace, complete_trace, log_event
from app.security.prompt_guard import check_prompt_injection
from app.security.pii import mask_pii
from app.security.rate_limit import check_rate_limit
from app.exceptions import PromptInjectionDetectedError, RateLimitExceededError
from app.database.database import get_db

router = APIRouter()

@router.post("/v1/chat/completions", response_model=ChatResponse)
async def chat_completions(payload: ChatRequest, request: Request, db: Session = Depends(get_db)):
    trace_id = str(uuid.uuid4())
    model = "openai/gpt-oss-20b"

    client_id = request.client.host     # get callers IP adress

    start_trace(db, trace_id, model, payload.message)
    log_event(db, trace_id, "REQUEST_STARTED")

    log_event(db, trace_id, "SECURITY_CHECK")

    if not check_rate_limit(client_id):
        log_event(db, trace_id, "RATE_LIMITED_BLOCKED")
        raise RateLimitExceededError(trace_id)

    if check_prompt_injection(payload.message):
        log_event(db, trace_id, "PROMPT_INJECTION_BLOCKED")
        raise PromptInjectionDetectedError(trace_id)

    safe_message = mask_pii(payload.message)
    log_event(db, trace_id, "LLM_REQUEST")
    llm_start = time.perf_counter()
    result = call_groq(safe_message)
    llm_latency_ms = round((time.perf_counter() - llm_start) * 1000, 2)
    log_event(db, trace_id, "LLM_RESPONSE")

    complete_trace(
        db=db,
        trace_id=trace_id,
        prompt=safe_message,
        response=result["text"],
        status="success",
        llm_latency_ms=llm_latency_ms,
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
        total_tokens=result["total_tokens"]
    )
    log_event(db, trace_id, "REQUEST_COMPLETED")

    return ChatResponse(
        response=result["text"],
        trace_id=trace_id
    )

