"""Wrapper around the Ollama Python client for AI article processing."""

from __future__ import annotations

import importlib
from types import ModuleType
from typing import Any

from infra.configuration import OllamaSettings, get_ollama_settings


class OllamaClientError(RuntimeError):
    """Raised when Ollama returns an error response."""


class OllamaClient:
    """Thin wrapper that provides convenient helpers for Ollama interactions."""

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        """Configure the Ollama client with optional overrides."""
        settings = _resolve_settings(host=host, model=model, timeout=timeout)
        self._settings = settings
        ollama_module = _load_ollama()
        self._client = ollama_module.Client(host=settings.host)

    @property
    def model(self) -> str:
        """Return the Ollama model currently configured for requests."""
        return self._settings.model

    def summarize_article(
        self,
        title: str,
        raw_content: str,
        max_words: int = 180,
        temperature: float = 0.2,
    ) -> str:
        """Generate a concise summary for a crypto article."""
        prompt = _build_summary_prompt(title=title, content=raw_content, max_words=max_words)

        try:
            response = self._client.generate(
                model=self._settings.model,
                prompt=prompt,
                options={"temperature": temperature},
                timeout=self._settings.timeout,
            )
        except Exception as exc:
            raise OllamaClientError(str(exc)) from exc

        summary = _extract_response_text(response)
        if not summary:
            msg = "Ollama returned an empty summary response"
            raise OllamaClientError(msg)

        return summary


def _build_summary_prompt(*, title: str, content: str, max_words: int) -> str:
    sanitized_content = content.strip()

    return (
        "You are an expert crypto news editor. "
        "Summarize the following article focusing on trading-relevant insights, "
        "market drivers, and key metrics. "
        f"Limit the summary to approximately {max_words} words and keep it readable.\n\n"
        f"Title: {title.strip()}\n\n"
        "Article:\n"
        f"{sanitized_content}"
    )


def _extract_response_text(response: dict[str, Any]) -> str:
    text = response.get("response")
    if isinstance(text, str) and text.strip():
        return text.strip()

    message = response.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()

    return ""


def get_ollama_client() -> OllamaClient:
    """Return a lazily configured Ollama client instance."""
    return OllamaClient()


def _resolve_settings(
    *, host: str | None, model: str | None, timeout: float | None,
) -> OllamaSettings:
    base_settings = get_ollama_settings()

    resolved_host = host or base_settings.host
    resolved_model = model or base_settings.model
    resolved_timeout = timeout if timeout is not None else base_settings.timeout

    return OllamaSettings(
        host=resolved_host,
        model=resolved_model,
        timeout=resolved_timeout,
    )


__all__ = ["OllamaClient", "OllamaClientError", "get_ollama_client"]


def _load_ollama() -> ModuleType:
    try:
        return importlib.import_module("ollama")
    except ImportError as exc:  # pragma: no cover - handled at runtime
        message = (
            "Ollama package is not installed. "
            "Add 'ollama' to requirements.txt and install dependencies."
        )
        raise OllamaClientError(message) from exc

