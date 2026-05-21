"""Wire protocol: JSON-line request, response, and error envelopes."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

type ResponseReason = Literal["clean", "wordlist", "toxicity", "sentiment", "rewrite_failed"]


class RewriteRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    text: str


class RewriteResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    was_rewritten: bool
    reason: ResponseReason
    scores: dict[str, float]


class ErrorResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    error: str
