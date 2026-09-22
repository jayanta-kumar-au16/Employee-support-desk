from fastapi import FastAPI

from app.models import InternalAnswerRequest, PolicyAnswer
from app.policy_repository import PolicyRepository
from app.policy_service import PolicyService


app = FastAPI(title="Employee Support Desk - Python Service")
policy_service = PolicyService(PolicyRepository())


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
