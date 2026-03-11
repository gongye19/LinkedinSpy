from __future__ import annotations

from collections.abc import Mapping
import json
from typing import Any

import requests

DEFAULT_LLM_RULES = [
    "The role must be related to AI, LLM, RAG, or agents.",
    "Reject junior or entry-level roles.",
]


class LLMClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model_name: str,
        custom_rules: list[str] | None = None,
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.custom_rules = [rule.strip() for rule in (custom_rules or []) if rule and rule.strip()]
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
        effective_rules = self.custom_rules or DEFAULT_LLM_RULES
        rules_text = "\n".join(f"{idx}. {rule}" for idx, rule in enumerate(effective_rules, start=1))
        return (
            "Classify whether this job should be kept.\n"
            "Rules:\n"
            f"{rules_text}\n"
            "Return JSON with keys is_ai_related, is_seniority_allowed, passed, reason.\n\n"
            f"Job payload:\n{json.dumps(dict(payload), ensure_ascii=False, default=str)}"
        )
