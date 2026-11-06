# Pydantic schema for untrusted AI action proposals.
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ActionProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    action: str = Field(
        pattern=r"^skill\.[a-z][a-z0-9_]{0,47}\.[a-z][a-z0-9_]{0,47}$",
        max_length=120,
    )
    parameters: dict[str, Any] = Field(default_factory=dict)
    rationale: str = Field(min_length=1, max_length=1000)
