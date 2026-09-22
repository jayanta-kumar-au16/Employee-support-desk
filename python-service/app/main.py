import os
import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.models import InternalAnswerRequest, PolicyAnswer, InternalDocumentRequest, DocumentResult
from app.document_service import DocumentService
from app.provider import GenerationService, ProviderFailure
from app.policy_repository import PolicyRepository
from app.policy_service import PolicyService


app = FastAPI(title="Employee Support Desk - Python Service")
logging.basicConfig(level=logging.INFO)
policy_service = PolicyService(PolicyRepository(), GenerationService(timeout=float(os.getenv("MODEL_TIMEOUT_SECONDS", "1"))))
document_service = DocumentService(policy_service)


@app.exception_handler(ProviderFailure)
def provider_failure(request, exception: ProviderFailure):
    return JSONResponse(status_code=503, content={"code": exception.code, "message": str(exception)})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "UP", "service": "python-service"}


@app.post("/internal/answer", response_model=PolicyAnswer)
def answer(request: InternalAnswerRequest) -> PolicyAnswer:
    return policy_service.answer_question(
        tenant=request.tenant,
        role=request.role,
        as_of=request.as_of,
        question=request.question,
    )


@app.post("/internal/document", response_model=DocumentResult)
def document(request: InternalDocumentRequest) -> DocumentResult:
    return document_service.process(request)
