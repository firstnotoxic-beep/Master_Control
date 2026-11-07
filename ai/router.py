# Route prompts through configured providers in a fixed priority order with safe fallback.
from __future__ import annotations

import os
from collections.abc import Mapping, Sequence

from ai.privacy import redact_private_data
from ai.providers import (
    AIProvider,
    EnvironmentStubProvider,
    ProviderError,
    ProviderResult,
)

PROVIDER_ORDER = ("groq", "gemini", "github_models")
PROVIDER_ENV_KEYS = {
    "groq": "GROQ_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "github_models": "GITHUB_MODELS_API_KEY",
}


class NoProviderAvailable(RuntimeError):
    """No configured provider could generate a response."""


class ProviderRouter:
    def __init__(
        self,
        providers: Mapping[str, AIProvider] | None = None,
        *,
        environment: Mapping[str, str] | None = None,
        order: Sequence[str] = PROVIDER_ORDER,
    ) -> None:
        if any(name not in PROVIDER_ENV_KEYS for name in order):
            raise ValueError("unknown AI provider name in provider order")
        self.environment = os.environ if environment is None else environment
        self.order = tuple(order)
        self.providers: dict[str, AIProvider] = {
            name: EnvironmentStubProvider(name, PROVIDER_ENV_KEYS[name])
            for name in PROVIDER_ORDER
        }
        if providers is not None:
            self.providers.update(providers)

    def generate(
        self,
        prompt: str,
        context: Mapping[str, object] | None = None,
        *,
        consent_private_data: bool = False,
    ) -> ProviderResult:
        safe_context = redact_private_data(
            dict(context or {}),
            consent=consent_private_data,
        )
        attempted: list[str] = []
        for name in self.order:
            provider = self.providers.get(name)
            if provider is None or not provider.is_available(self.environment):
                continue
            attempted.append(name)
            try:
                response = provider.generate(prompt, safe_context)
            except (ProviderError, NotImplementedError, TimeoutError, OSError, ValueError):
                continue
            if not isinstance(response, str) or not response.strip():
                continue
            return ProviderResult(
                provider=name,
                content=response,
                attempted=tuple(attempted),
            )
        raise NoProviderAvailable(
            "No configured provider produced a response; no live API implementation is enabled"
        )
