import time
import uuid
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from groq import GroqError
from app.schemas import ChatRequest, ChatResponse
from app.llm.groq_client import call_groq, MODEL_NAME
from app.tracing.tracer import start_trace, complete_trace, log_event
from app.security.prompt_guard import check_prompt_injection
from app.security.pii import mask_pii
from app.security.rate_limit import check_rate_limit
from app.exceptions import PromptInjectionDetectedError, RateLimitExceededError, LLMProviderError
from app.database.database import get_db
from app.security.auth import verify_api_key

router = APIRouter()


def get_client_id(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


@router.post("/v1/chat/completions", response_model=ChatResponse)
async def chat_completions(payload: ChatRequest, request: Request, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    trace_id = str(uuid.uuid4())
    client_id = get_client_id(request)

    start_trace(db, trace_id, MODEL_NAME, payload.message)
    log_event(db, trace_id, "REQUEST_STARTED")

    log_event(db, trace_id, "SECURITY_CHECK")

    if not check_rate_limit(client_id):
        log_event(db, trace_id, "RATE_LIMIT_BLOCKED")
        raise RateLimitExceededError(trace_id)

    if check_prompt_injection(payload.message):
        log_event(db, trace_id, "PROMPT_INJECTION_BLOCKED")
        raise PromptInjectionDetectedError(trace_id)

    safe_message = mask_pii(payload.message)

    log_event(db, trace_id, "LLM_REQUEST")
    llm_start = time.perf_counter()
    try:
        result = call_groq(safe_message)
    except GroqError as e:
        log_event(db, trace_id, "LLM_ERROR")
        raise LLMProviderError(trace_id, reason=str(e))
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
        total_tokens=result["total_tokens"],
    )
    log_event(db, trace_id, "REQUEST_COMPLETED")

    return ChatResponse(
        response=result["text"],
        trace_id=trace_id
    )