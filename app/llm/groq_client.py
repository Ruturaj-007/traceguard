from groq import Groq 
from app.config import settings

client = Groq(api_key=settings.groq_api_key)

def call_groq(prompt: str) -> dict:
    completion = client.chat.completions.create(
        model = "llama-3.1-8b-instant",
        messages = [{
            "role": "user",
            "content": prompt
        }],
        temperature = 0.3
    )

    usage = completion.usage

    return {
        "text": completion.choices[0].message.content,
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None)
    }