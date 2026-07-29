from __future__ import annotations

import os
from typing import Any

from providers.base import ModelResponse
from providers.openai_provider import OpenAIProvider


class GroqProvider(OpenAIProvider):
    """Groq's OpenAI-compatible Chat Completions provider."""

    def __init__(self) -> None:
        super().__init__(
            api_key_env="GROQ_API_KEY",
            base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
            default_model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        )

    @staticmethod
    def _is_tool_generation_error(exc: Exception) -> bool:
        """Return true only for Groq's malformed generated function-call error."""
        if getattr(exc, "status_code", None) != 400:
            return False
        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            error = body.get("error", body)
            if isinstance(error, dict) and error.get("code") == "tool_use_failed":
                return True
        return "tool_use_failed" in str(exc)

    def complete(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        tool_choice: Any | None = None,
    ) -> ModelResponse:
        retry_messages = list(messages)
        max_attempts = 3

        for attempt in range(max_attempts):
            try:
                return super().complete(
                    retry_messages,
                    tools,
                    model=model,
                    temperature=temperature,
                    tool_choice=tool_choice,
                )
            except Exception as exc:
                if not self._is_tool_generation_error(exc) or attempt == max_attempts - 1:
                    raise
                retry_messages = [
                    {
                        "role": "system",
                        "content": (
                            "IMPORTANT: The previous function-call serialization was malformed. "
                            "Use the API's native structured tool calling only. Select an exact "
                            "declared function name and emit arguments that strictly match its JSON "
                            "Schema types. Do not write XML/function tags or tool-call syntax as text."
                        ),
                    },
                    *messages,
                ]

        raise RuntimeError("Groq completion retry loop ended unexpectedly")
