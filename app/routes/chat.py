import uuid
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from app.schemas import ChatRequest, ChatResponse
from app.tracing.tracer import start_trace, log_event
from app.llm.groq_client import MODEL_NAME
from app.database.database import get_db
from app.security.auth import verify_api_key
from app.pipeline import run_chat_pipeline

router = APIRouter()


def get_client_id(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


@router.post("/v1/chat/completions", response_model=ChatResponse)
async def chat_completions(
    payload: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    trace_id = str(uuid.uuid4())
    client_id = get_client_id(request)

    start_trace(db, trace_id, MODEL_NAME, payload.message)
    log_event(db, trace_id, "REQUEST_STARTED")

    result = run_chat_pipeline(db, trace_id, payload.message, client_id)

    return ChatResponse(**result)