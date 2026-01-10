import os
import requests
import json
from app.core.llm_base import LLMClient

class OpenAICompatLLMClient(LLMClient):
    def __init__(self):
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        self.api_key = os.getenv("LLM_API_KEY")
        self.model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        if not self.api_key:
            raise RuntimeError("LLM_API_KEY is required for OpenAI-compatible LLM provider.")

    def complete(self, prompt: str) -> dict:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"}
        }
        response = requests.post(url, headers=headers, json=payload)
        try:
            raw_text = response.json()["choices"][0]["message"]["content"]
        except Exception:
            raw_text = response.text
        try:
            parsed_json = json.loads(raw_text)
        except Exception:
            parsed_json = None
        return {"raw_text": raw_text, "parsed_json": parsed_json}
