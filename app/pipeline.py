import time
from sqlalchemy.orm import Session
from groq import GroqError
from app.tracing.tracer import log_event, complete_trace
from app.security.prompt_guard import check_prompt_injection
from app.security.pii import mask_pii
from app.security.rate_limit import check_rate_limit
from app.llm.groq_client import call_groq
from app.exceptions import PromptInjectionDetectedError, RateLimitExceededError, LLMProviderError


def run_chat_pipeline(db: Session, trace_id: str, prompt: str, client_id: str) -> dict:
    """
    Runs the full request pipeline: rate limit -> injection check ->
    PII mask -> Groq call -> trace completion.
    Raises the appropriate custom exception on any failure.
    Returns the final ChatResponse-shaped dict on success.
    """
    log_event(db, trace_id, "SECURITY_CHECK")

    if not check_rate_limit(client_id):
        log_event(db, trace_id, "RATE_LIMIT_BLOCKED")
        raise RateLimitExceededError(trace_id)

    if check_prompt_injection(prompt):
        log_event(db, trace_id, "PROMPT_INJECTION_BLOCKED")
        raise PromptInjectionDetectedError(trace_id)

    safe_message = mask_pii(prompt)

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

    return {
        "response": result["text"],
        "trace_id": trace_id
    }