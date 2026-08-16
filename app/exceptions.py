class PromptInjectionDetectedError(Exception):
    def __init__(self, trace_id: str):
        self.trace_id = trace_id

class PIIDetectedError(Exception):
    def __init__(self, trace_id: str):
        self.trace_id = trace_id

class LLMProviderError(Exception):
    def __init__(self, trace_id: str, reason: str):
        self.trace_id = trace_id
        self.reason = reason

class TraceNotFoundError(Exception):
    def __init__(self, trace_id: str):
        self.trace_id = trace_id

class RateLimitExceededError(Exception):
    def __init__(self, trace_id: str):
        self.trace_id = trace_id