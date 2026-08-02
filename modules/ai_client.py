from openai import OpenAI

from config import (
    OLLAMA_API_KEY,
    OLLAMA_BASE_URL,
)


def create_ai_client() -> OpenAI:
    return OpenAI(
        base_url=OLLAMA_BASE_URL,
        api_key=OLLAMA_API_KEY,
    )