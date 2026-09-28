import os
import logging
import secrets
from contextlib import asynccontextmanager
from app.settings import build_generation, load_local_environment
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.models import InternalAnswerRequest, PolicyAnswer, InternalDocumentRequest, DocumentResult
from app.document_service import DocumentService
from app.provider import ProviderFailure
from app.policy_repository import PolicyRepository
from app.policy_service import PolicyService


@asynccontextmanager
async def lifespan(app):
    yield
    close = getattr(policy_service._generation.provider, "close", None)
    if close:
        close()


load_local_environment()
app = FastAPI(title="Employee Support Desk - Python Service", lifespan=lifespan)
app.state.internal_token = os.getenv("INTERNAL_SERVICE_TOKEN", "")
if app.state.internal_token and len(app.state.internal_token) < 32:
    raise ValueError("INTERNAL_SERVICE_TOKEN must contain at least 32 characters")


@app.middleware("http")
async def authenticate_internal(request, call_next):
    token = app.state.internal_token
    if request.url.path.startswith("/internal/") and token:
        supplied = request.headers.get("X-Internal-Token", "")
        if not secrets.compare_digest(supplied.encode(), token.encode()):
            return JSONResponse(status_code=401, content={"code": "UNAUTHORIZED", "message": "Internal authentication required"})
    return await call_next(request)
logging.basicConfig(level=logging.INFO)
policy_service = PolicyService(PolicyRepository(), build_generation())
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
