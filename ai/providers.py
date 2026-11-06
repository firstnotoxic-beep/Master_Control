# Provider contracts and safe stubs; live API clients are intentionally not implemented.
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


class ProviderError(RuntimeError):
    """A provider failed or cannot serve the request."""


class AIProvider(Protocol):
    name: str

    def is_available(self, environment: Mapping[str, str]) -> bool:
        """Return whether provider configuration is present."""

    def generate(self, prompt: str, context: Mapping[str, object]) -> str:
        """Return raw text from the provider."""


@dataclass(frozen=True)
class ProviderResult:
    provider: str
    content: str
    attempted: tuple[str, ...]


class EnvironmentStubProvider:
    """Configuration-only placeholder that never makes a network request."""

    def __init__(self, name: str, environment_key: str) -> None:
        self.name = name
        self.environment_key = environment_key

    def is_available(self, environment: Mapping[str, str]) -> bool:
        return bool(environment.get(self.environment_key, "").strip())

    def generate(self, prompt: str, context: Mapping[str, object]) -> str:
        raise ProviderError(
            f"{self.name} client is a disabled stub in this release; no API request was sent"
        )


class MockProvider:
    """Deterministic test provider. It has no network or external dependencies."""

    def __init__(
        self,
        name: str,
        response: str = "{}",
        *,
        error: str | None = None,
        available: bool = True,
    ) -> None:
        self.name = name
        self.response = response
        self.error = error
        self.available = available
        self.calls: list[tuple[str, dict[str, object]]] = []

    def is_available(self, environment: Mapping[str, str]) -> bool:
        return self.available

    def generate(self, prompt: str, context: Mapping[str, object]) -> str:
        self.calls.append((prompt, dict(context)))
        if self.error is not None:
            raise ProviderError(self.error)
        return self.response
