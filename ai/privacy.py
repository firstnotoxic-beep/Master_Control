# Remove marked private context fields unless the caller explicitly grants consent.
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

DEFAULT_PRIVATE_KEYS = frozenset(
    {
        "address",
        "api_key",
        "email",
        "password",
        "phone",
        "private",
        "secret",
        "sensitive",
        "token",
    }
)
REDACTED_VALUE = "[REDACTED]"


def redact_private_data(
    value: Any,
    *,
    consent: bool = False,
    private_keys: Sequence[str] | None = None,
) -> Any:
    """Recursively redact known private fields unless explicit consent is true."""
    if consent:
        return deepcopy(value)

    protected = {key.casefold() for key in (private_keys or DEFAULT_PRIVATE_KEYS)}
    if isinstance(value, Mapping):
        return {
            key: (
                REDACTED_VALUE
                if isinstance(key, str) and key.casefold() in protected
                else redact_private_data(
                    item,
                    consent=False,
                    private_keys=tuple(protected),
                )
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            redact_private_data(item, consent=False, private_keys=tuple(protected))
            for item in value
        ]
    if isinstance(value, tuple):
        return tuple(
            redact_private_data(item, consent=False, private_keys=tuple(protected))
            for item in value
        )
    return deepcopy(value)
