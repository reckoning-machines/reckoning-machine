import os
from app.core.stub_llm import stub_llm
from app.core.llm_openai_compat import OpenAICompatLLMClient
from app.core.llm_base import LLMClient

_llm_client = None

# Select and initialize LLM
provider = os.getenv("LLM_PROVIDER", "stub").lower()

if provider == "openai":
    try:
        _llm_client = OpenAICompatLLMClient()
    except Exception as e:
        _llm_client = None
        # Fallback will be stub_llm below

# Wrapper. Accepts prompt:str, returns dict as LLMClient.complete.
def llm_complete(prompt: str) -> dict:
    global _llm_client
    if _llm_client:
        return _llm_client.complete(prompt)
    # Default deterministic stub
    raw = stub_llm(prompt)
    # Compose into LLMClient interface output:
    return {
        "raw_text": str(raw),
        "parsed_json": raw
    }
