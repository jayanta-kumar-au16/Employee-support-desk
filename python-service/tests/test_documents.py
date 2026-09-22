import base64
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.document_service import DocumentService, extract_fields
from app.main import app
from app.models import InternalDocumentRequest
from app.policy_repository import PolicyRepository
from app.policy_service import PolicyService

FIXTURES = Path(__file__).resolve().parents[2] / "examples" / "requests"


def request(filename, content):
    return InternalDocumentRequest(tenant="Atlas", role="employee", as_of=date(2026, 9, 21),
        batch_id="demo-01", document_id=Path(filename).stem, filename=filename,
        content_base64=base64.b64encode(content).decode())


@pytest.fixture
def service():
    return DocumentService(PolicyService(PolicyRepository()))


def test_supplied_mixed_documents(service):
    results = []
    for i in range(1, 9):
        name = f"request-{i:02d}.{'pdf' if i == 2 else 'txt'}"
        results.append(service.process(request(name, (FIXTURES / name).read_bytes())))
    assert [r.processing_status for r in results] == ["COMPLETED"] * 7 + ["FAILED"]
    assert all(r.review_required for r in results)
    assert results[0].extracted.amount == Decimal("18000")
    assert "25000" in results[0].policy.answer
    assert any("payable amount" in issue for issue in results[0].issues)
    assert results[1].extracted.reference == "HOME-202"
    assert results[1].policy.status == "CONFLICT"
    assert results[2].extracted.amount is None
    assert results[2].field_evidence.amount == []
    assert results[2].extracted.currency == "INR"
    assert results[2].policy.status == "ANSWERED"  # Ambiguous input is not a policy conflict.
    assert any("22000" in issue and "28000" in issue for issue in results[2].issues)
    assert results[3].policy.status == "INSUFFICIENT_EVIDENCE"
    assert results[4].policy.citations[0].chunk_id == "atlas-cert-current"
    assert "80000" not in results[4].model_dump_json()
    assert results[5].extracted == results[0].extracted
    assert (FIXTURES / "request-01.txt").read_bytes() == (FIXTURES / "request-06.txt").read_bytes()
    assert results[6].extracted.amount is None and results[6].extracted.currency is None
    assert any("approval preceded booking" in issue for issue in results[6].issues)
    assert results[7].error.code == "EMPTY_FILE"
    assert results[7].policy is None


def test_evidence_is_verbatim_source_substring(service):
    content = (FIXTURES / "request-01.txt").read_bytes()
    result = service.process(request("request-01.txt", content))
    for quotes in result.field_evidence.model_dump().values():
        assert quotes
        assert all(quote in content.decode() for quote in quotes)


@pytest.mark.parametrize("filename,content,code", [
    ("empty.txt", b"", "EMPTY_FILE"),
    ("spaces.txt", b" \n", "NO_EXTRACTABLE_TEXT"),
    ("bad.txt", b"\xff\xfe", "UNREADABLE_FILE"),
    ("binary.txt", b"abc\x00def", "UNREADABLE_FILE"),
    ("broken.pdf", b"%PDF-1.4 broken", "UNREADABLE_FILE"),
    ("renamed.pdf", b"certification", "UNREADABLE_FILE"),
    ("request.docx", b"content", "UNSUPPORTED_FILE_TYPE"),
])
def test_file_failures_are_explicit(service, filename, content, code):
    result = service.process(request(filename, content))
    assert result.processing_status == "FAILED"
    assert result.error.code == code
    assert result.policy is None


def test_multiple_topics_and_references_are_unresolved(service):
    result = service.process(request("ambiguous.txt", b"Reference: A-1\nReference: A-2\nI request training and certification reimbursement of INR 1200."))
    assert result.processing_status == "COMPLETED"
    assert result.extracted.benefit is None and result.extracted.reference is None
    assert result.policy is None


def test_same_amount_different_currencies_is_ambiguous():
    fields, evidence, issues = extract_fields("Certification request: INR 1000 or USD 1000.")
    assert fields.amount is None and fields.currency is None
    assert evidence.amount == evidence.currency == []


def test_internal_document_api():
    payload = request("request-01.txt", (FIXTURES / "request-01.txt").read_bytes()).model_dump(mode="json")
    response = TestClient(app).post("/internal/document", json=payload)
    assert response.status_code == 200
    assert response.json()["extracted"]["amount"] == "18000"
    assert response.json()["review_required"] is True
