from __future__ import annotations

from collections.abc import Mapping
import json
from typing import Any

import requests


class LLMClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model_name: str,
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout

    def evaluate_job(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        prompt = self._build_prompt(payload)
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a strict job screening assistant. "
                            "Return only valid JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)

    def _build_prompt(self, payload: Mapping[str, Any]) -> str:
        return (
            "Classify whether this job should be kept.\n"
            "Rules:\n"
            "1. The role must be related to AI, LLM, RAG, or agents.\n"
            "2. Reject junior or entry-level roles.\n"
            "Return JSON with keys is_ai_related, is_seniority_allowed, passed, reason.\n\n"
            f"Job payload:\n{json.dumps(dict(payload), ensure_ascii=False, default=str)}"
        )
