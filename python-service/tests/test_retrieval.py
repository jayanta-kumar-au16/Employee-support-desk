from datetime import date
import json

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.policy_repository import DEFAULT_POLICY_FILE, PolicyRepository
from app.policy_service import PolicyService
from app.provider import GenerationService
from app.retrieval import PolicyRetriever


DAY = date(2026, 9, 21)


@pytest.mark.parametrize("question,status,quote", [
    ("What is my professional exam reimbursement limit?", "ANSWERED", "25000"),
    ("What allowance applies to working from home?", "CONFLICT", None),
    ("Explain the policy for business trips", "ANSWERED", "rail travel"),
    ("Do external courses require approval?", "ANSWERED", "Manager approval"),
    ("What is my fitness membership limit?", "INSUFFICIENT_EVIDENCE", None),
    ("What is my external course budget?", "INSUFFICIENT_EVIDENCE", None),
    ("What is my remaining professional exam balance?", "INSUFFICIENT_EVIDENCE", None),
    ("Explain professional exams and working from home", "INSUFFICIENT_EVIDENCE", None),
    ("What is my meal reimbursement limit?", "INSUFFICIENT_EVIDENCE", None),
])
def test_paraphrases_through_api(question, status, quote, monkeypatch):
    monkeypatch.setattr(main, "policy_service", PolicyService(PolicyRepository()))
    response = TestClient(main.app).post("/internal/answer", json={
        "tenant": "Atlas", "role": "employee", "as_of": DAY.isoformat(), "question": question,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == status
    if quote:
        assert quote in body["answer"]
    else:
        assert body["answer"] is None


@pytest.mark.parametrize("tenant,role,day,expected", [
    ("Atlas", "employee", DAY, ["atlas-cert-current"]),
    ("Atlas", "contractor", DAY, ["atlas-cert-contractor"]),
    ("Boreal", "employee", DAY, ["boreal-cert-current"]),
    ("Atlas", "employee", date(2026, 5, 31), ["atlas-cert-historical"]),
    ("Atlas", "employee", date(2026, 6, 1), ["atlas-cert-current"]),
    ("Atlas", "employee", date(2027, 1, 1), ["atlas-cert-future"]),
    ("Atlas", "employee", date(2028, 1, 1), []),
    ("Unknown", "employee", DAY, []),
])
def test_retrieval_filters_before_ranking(tenant, role, day, expected):
    hits = PolicyRetriever(PolicyRepository()).retrieve(
        tenant, role, day, "professional exam limit", "certification")
    assert [hit.policy["id"] for hit in hits] == expected
    assert all(hit.score > 0 for hit in hits)


def test_low_ranked_conflict_is_retained_and_never_generated(tmp_path):
    records = json.loads(DEFAULT_POLICY_FILE.read_text())
    record = dict(next(p for p in records if p["id"] == "atlas-cert-current"))
    record.update(id="additional-rule", text="Professional exam reimbursement limit is INR 50000. " + "Additional context. " * 100)
    records.append(record)
    path = tmp_path / "policies.json"
    path.write_text(json.dumps(records))

    class UnexpectedProvider:
        def generate(self, quotations):
            pytest.fail("Conflicting evidence must not reach generation")

    service = PolicyService(PolicyRepository(path), GenerationService(UnexpectedProvider()))
    result = service.answer_question("Atlas", "employee", DAY, "What is my certification limit?")
    assert result.status == "CONFLICT"
    assert {c.chunk_id for c in result.citations} == {"atlas-cert-current", "additional-rule"}


def test_only_retrieved_authorized_quotes_reach_contextual_generation():
    class RecordingProvider:
        def __init__(self):
            self.calls = []

        def generate_context(self, question, quotations):
            self.calls.append((question, quotations))
            return {"answer": " ".join(quotations), "explanation": "The annual limit is INR 25000."}

    provider = RecordingProvider()
    question = "What is my professional exam reimbursement limit?"
    result = PolicyService(PolicyRepository(), GenerationService(provider)).answer_question(
        "Atlas", "employee", DAY, question)
    assert provider.calls == [(question, ("The annual certification reimbursement limit for employees is INR 25000.",))]
    assert result.explanation == "The annual limit is INR 25000."


def test_ranking_and_policy_updates(tmp_path):
    records = json.loads(DEFAULT_POLICY_FILE.read_text())
    source = next(p for p in records if p["id"] == "atlas-cert-current")
    records.append(dict(source, id="approval", text="Manager approval is required before certification is booked."))
    path = tmp_path / "policies.json"
    path.write_text(json.dumps(records))
    retriever = PolicyRetriever(PolicyRepository(path))
    hits = retriever.retrieve("Atlas", "employee", DAY, "manager approval before certification booked", "certification")
    assert hits[0].policy["id"] == "approval"
    assert len(hits) == 2
    source["text"] = source["text"].replace("25000", "27000")
    path.write_text(json.dumps(records))
    updated = retriever.retrieve("Atlas", "employee", DAY, "professional exam limit", "certification", "amount")
    assert len(updated) == 1
    assert "27000" in updated[0].policy["text"]
