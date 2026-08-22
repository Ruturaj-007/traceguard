from fastapi import FastAPI
from app.routes import chat
from app.exceptions import (
    PromptInjectionDetectedError, PIIDetectedError, 
    LLMProviderError, TraceNotFoundError, RateLimitExceededError
)
from app.exception_handlers import (
    prompt_injection_handler, pii_detected_handler, 
    llm_provider_error_handler, trace_not_found_handler, rate_limit_exceeded_handler
)
from app.database.database import engine
from app.models import Base

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TraceGuard",
    version="0.1.0"
)

app.include_router(chat.router)

app.add_exception_handler(PromptInjectionDetectedError, prompt_injection_handler)
app.add_exception_handler(PIIDetectedError, pii_detected_handler)
app.add_exception_handler(LLMProviderError, llm_provider_error_handler)
app.add_exception_handler(TraceNotFoundError, trace_not_found_handler)
app.add_exception_handler(RateLimitExceededError, rate_limit_exceeded_handler)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "TraceGuard"
    }