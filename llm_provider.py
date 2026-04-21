"""
theLitmus — LLM Provider Abstraction
=============================================
Provider-agnostic interface for LLM extraction and suppression.
Switch providers by changing one line in config.

Supported providers:
  - Claude (Anthropic API) — default, recommended
  - OpenAI (GPT-4o-mini or GPT-4o)
  - Ollama (local models, free, slower)
"""

from __future__ import annotations
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResponse:
    """Standardised response from any provider."""
    content: str
    model: str
    provider: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    raw_response: Optional[dict] = None


class LLMProvider(ABC):
    """Abstract base for all LLM providers."""

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Send a prompt and return a standardised response."""
        raise NotImplementedError

    def extract_json(self, system_prompt: str, user_prompt: str) -> dict:
        """
        Send a prompt expecting JSON output.
        Strips markdown fences and parses.
        """
        response = self.complete(system_prompt, user_prompt)
        text = response.content.strip()

        # Strip markdown JSON fences if present
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ExtractionError(
                f"LLM returned invalid JSON: {e}\n\nRaw output:\n{response.content[:500]}"
            ) from e


class ExtractionError(Exception):
    """Raised when LLM output cannot be parsed into valid schema JSON."""
    pass


# ─── Claude Provider ─────────────────────────────────────────────────

class ClaudeProvider(LLMProvider):
    """Anthropic Claude API provider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model
        self.max_tokens = max_tokens

        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY env var or pass api_key."
            )

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        try:
            import anthropic
        except ImportError:
            raise ImportError("Install anthropic SDK: pip install anthropic")

        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text

        return LLMResponse(
            content=content,
            model=self.model,
            provider="claude",
            input_tokens=getattr(response.usage, "input_tokens", None),
            output_tokens=getattr(response.usage, "output_tokens", None),
            raw_response=None,
        )


# ─── OpenAI Provider ─────────────────────────────────────────────────

class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        max_tokens: int = 4096,
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model
        self.max_tokens = max_tokens

        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY env var or pass api_key."
            )

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        try:
            import openai
        except ImportError:
            raise ImportError("Install openai SDK: pip install openai")

        client = openai.OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content or ""
        usage = response.usage

        return LLMResponse(
            content=content,
            model=self.model,
            provider="openai",
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            raw_response=None,
        )


# ─── Ollama Provider ─────────────────────────────────────────────────

class OllamaProvider(LLMProvider):
    """Local Ollama provider for offline development."""

    def __init__(
        self,
        model: str = "llama3.1",
        base_url: str = "http://localhost:11434",
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        import urllib.request
        import urllib.error

        payload = json.dumps({
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise ConnectionError(
                f"Cannot reach Ollama at {self.base_url}. Is it running? Error: {e}"
            ) from e

        content = data.get("message", {}).get("content", "")

        return LLMResponse(
            content=content,
            model=self.model,
            provider="ollama",
            input_tokens=data.get("prompt_eval_count"),
            output_tokens=data.get("eval_count"),
            raw_response=data,
        )


# ─── Factory ──────────────────────────────────────────────────────────

def get_provider(
    provider_name: str = "claude",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs,
) -> LLMProvider:
    """
    Factory function. Switch providers with one argument.

    Usage:
        provider = get_provider("claude")
        provider = get_provider("openai", model="gpt-4o")
        provider = get_provider("ollama", model="mistral")
    """
    provider_name = provider_name.lower().strip()

    if provider_name == "claude":
        return ClaudeProvider(
            api_key=api_key,
            model=model or "claude-sonnet-4-20250514",
            **kwargs,
        )
    elif provider_name == "openai":
        return OpenAIProvider(
            api_key=api_key,
            model=model or "gpt-4o-mini",
            **kwargs,
        )
    elif provider_name == "ollama":
        return OllamaProvider(
            model=model or "llama3.1",
            **kwargs,
        )
    else:
        raise ValueError(
            f"Unknown provider: '{provider_name}'. Supported: claude, openai, ollama"
        )
