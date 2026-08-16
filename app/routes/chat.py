import uuid
from fastapi import APIRouter
from app.schemas import ChatRequest, ChatResponse
from app.exceptions import PromptInjectionDetectedError
from app.llm.groq_client import call_groq

router = APIRouter()

@router.post("/v1/chat/completions", response_model=ChatResponse)
async def chat_completions(payload: ChatRequest):
    trace_id = str(uuid.uuid4())

    result = call_groq(payload.message)

    return ChatResponse(
        response=result["text"],
        trace_id=trace_id
    )
