from fastapi import Request
from fastapi.responses import JSONResponse
from app.exceptions import (
    PromptInjectionDetectedError, PIIDetectedError, LLMProviderError,
    TraceNotFoundError, RateLimitExceededError, InvalidApiKeyError
)

async def prompt_injection_handler(req: Request, exc: PromptInjectionDetectedError):
    return JSONResponse(
        status_code=400,
        content={
            "error": "prompt_injection_detected",
            "message": "Potential Prompt injection detected",
            "trace_id": exc.trace_id,
        },
    )

async def pii_detected_handler(req: Request, exc: PIIDetectedError):
    return JSONResponse(
        status_code=400,
        content={
            "error": "pii_detected_error",
            "message": "PII detected in request",
            "trace_id": exc.trace_id,
        }
    )

async def llm_provider_error_handler(req: Request, exc: LLMProviderError):
    return JSONResponse(
        status_code=502,
        content={
            "error": "llm_provider_error",
            "message": f"LLM provider failed: {exc.reason}",
            "trace_id": exc.trace_id,
        },
    )


async def trace_not_found_handler(req: Request, exc: TraceNotFoundError):
    return JSONResponse(
        status_code=404,
        content={
            "error": "trace_not_found",
            "message": f"No trace found for id: {exc.trace_id}",
            "trace_id": exc.trace_id,
        },
    )

async def rate_limit_exceeded_handler(req: Request, exc: RateLimitExceededError):
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests",
            "trace_id": exc.trace_id
        },
    )

async def invalid_api_key_handler(req: Request, exc: InvalidApiKeyError):
    return JSONResponse(
        status_code=401,
        content={
            "error": "invalid_api_key",
            "message": exc.message,
        },
    )