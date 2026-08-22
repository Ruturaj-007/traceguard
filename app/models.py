from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class Trace(Base):
    __tablename__ = "traces"

    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(String, unique=True, index=True, nullable=False)
    model = Column(String, nullable=False)
    prompt = Column(Text, nullable=True)
    response = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="started")
    latency_ms = Column(Float, nullable=True)
    llm_latency_ms = Column(Float, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    