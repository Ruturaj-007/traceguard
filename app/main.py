from fastapi import FastAPI
from app.routes import chat

app = FastAPI(
    title="TraceGuard",
    version="0.1.0"
)

app.include_router(chat.router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "TraceGuard"
    }