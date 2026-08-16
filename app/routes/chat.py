import uuid
from fastapi import APIRouter
from app.schemas import ChatRequest, ChatResponse
from app.llm.groq_client import call_groq
from app.tracing.tracer import start_trace, complete_trace, traces

router = APIRouter()

@router.post("/v1/chat/completions", response_model=ChatResponse)
async def chat_completions(payload: ChatRequest):
    trace_id = str(uuid.uuid4())
    model = "llama-3.1-8b-instant"

    start_trace(trace_id, model)

    result = call_groq(payload.message)

    complete_trace(
        trace_id=trace_id,
        prompt=payload.message,
        response=result["text"],
        status="success",
    )

    print(traces)

    return ChatResponse(
        response=result["text"],
        trace_id=trace_id
    )

