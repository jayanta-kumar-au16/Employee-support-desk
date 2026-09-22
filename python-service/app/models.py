from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class PolicyStatus(str, Enum):
    ANSWERED = "ANSWERED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICT = "CONFLICT"


class InternalAnswerRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    tenant: str = Field(min_length=1)
    role: str = Field(min_length=1)
    as_of: date
    question: str = Field(min_length=1)


class Citation(BaseModel):
    chunk_id: str
    quote: str


class PolicyAnswer(BaseModel):
    status: PolicyStatus
    answer: str | None
    citations: list[Citation]
