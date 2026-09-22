from datetime import date
from enum import Enum
from decimal import Decimal
from typing import Literal

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


class InternalDocumentRequest(InternalAnswerRequest):
    question: str = "document"
    batch_id: str = Field(min_length=1, max_length=100)
    document_id: str = Field(min_length=1, max_length=100)
    filename: str = Field(min_length=1, max_length=200)
    content_base64: str = Field(max_length=7_000_000)


class ExtractedFields(BaseModel):
    benefit: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    reference: str | None = None


class FieldEvidence(BaseModel):
    benefit: list[str] = Field(default_factory=list)
    amount: list[str] = Field(default_factory=list)
    currency: list[str] = Field(default_factory=list)
    reference: list[str] = Field(default_factory=list)


class ItemError(BaseModel):
    code: str
    message: str


class DocumentResult(BaseModel):
    document_id: str
    processing_status: Literal["COMPLETED", "FAILED"]
    extracted: ExtractedFields | None = None
    field_evidence: FieldEvidence = Field(default_factory=FieldEvidence)
    policy: PolicyAnswer | None = None
    review_required: Literal[True] = True
    issues: list[str]
    duplicate_of: str | None = None
    error: ItemError | None = None
