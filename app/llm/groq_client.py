from groq import Groq, GroqError
from app.config import settings

client = Groq(api_key=settings.groq_api_key)

MODEL_NAME = "openai/gpt-oss-20b"


def call_groq(prompt: str) -> dict:
    try:
        completion = client.chat.completions.create(
            model = MODEL_NAME,
            messages = [{
                "role": "user",
                "content": prompt
            }],
            temperature = 0.3
        )
    except GroqError as e:
        raise e

    usage = completion.usage

    return {
        "text": completion.choices[0].message.content,
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None)
    }