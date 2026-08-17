import time
import uuid
from fastapi import APIRouter
from app.schemas import ChatRequest, ChatResponse
from app.llm.groq_client import call_groq
from app.tracing.tracer import start_trace, complete_trace, traces
from app.security.prompt_guard import check_prompt_injection
from app.exceptions import PromptInjectionDetectedError
from app.security.pii import mask_pii

router = APIRouter()

@router.post("/v1/chat/completions", response_model=ChatResponse)
async def chat_completions(payload: ChatRequest):
    trace_id = str(uuid.uuid4())
    model = "llama-3.1-8b-instant"

    start_trace(trace_id, model)

    if check_prompt_injection(payload.message):
        raise PromptInjectionDetectedError(trace_id)

    safe_message = mask_pii(payload.message)

    llm_start = time.perf_counter()
    result = call_groq(safe_message)
    llm_latency_ms = round((time.perf_counter() - llm_start) * 1000, 2)

    complete_trace(
        trace_id=trace_id,
        prompt=payload.message,
        response=result["text"],
        status="success",
        llm_latency_ms=llm_latency_ms,
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
        total_tokens=result["total_tokens"]
    )

    print(traces)

    return ChatResponse(
        response=result["text"],
        trace_id=trace_id
    )

