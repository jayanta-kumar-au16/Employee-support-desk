import json
from datetime import date
from pathlib import Path

import pytest

from app.models import PolicyStatus
from app.policy_repository import DEFAULT_POLICY_FILE, PolicyRepository
from app.policy_service import PolicyService


@pytest.fixture
def service() -> PolicyService:
    return PolicyService(PolicyRepository())


def test_atlas_employee_gets_current_certification_policy(service: PolicyService) -> None:
    result = service.answer("Atlas", "employee", date(2026, 9, 21), "certification")

    assert result.status == PolicyStatus.ANSWERED
    assert result.answer == "The annual certification reimbursement limit for employees is INR 25000."
    assert [citation.chunk_id for citation in result.citations] == ["atlas-cert-current"]


def test_historical_policy_applies_before_june(service: PolicyService) -> None:
    result = service.answer("Atlas", "employee", date(2026, 5, 31), "certification")

    assert result.status == PolicyStatus.ANSWERED
    assert result.citations[0].chunk_id == "atlas-cert-historical"


def test_effective_to_date_is_exclusive(service: PolicyService) -> None:
    result = service.answer("Atlas", "employee", date(2026, 6, 1), "certification")

    assert result.status == PolicyStatus.ANSWERED
    assert result.citations[0].chunk_id == "atlas-cert-current"


def test_contractor_receives_only_contractor_policy(service: PolicyService) -> None:
    result = service.answer("Atlas", "contractor", date(2026, 9, 21), "certification")

    assert result.status == PolicyStatus.ANSWERED
    assert result.citations[0].chunk_id == "atlas-cert-contractor"


def test_boreal_employee_cannot_receive_atlas_policy(service: PolicyService) -> None:
    result = service.answer("Boreal", "employee", date(2026, 9, 21), "certification")

    assert result.status == PolicyStatus.ANSWERED
    assert result.citations[0].chunk_id == "boreal-cert-current"


def test_simultaneously_applicable_home_office_policies_conflict(service: PolicyService) -> None:
    result = service.answer("Atlas", "employee", date(2026, 9, 21), "home-office")

    assert result.status == PolicyStatus.CONFLICT
    assert result.answer is None
    assert [citation.chunk_id for citation in result.citations] == [
        "atlas-home-office-a",
        "atlas-home-office-b",
    ]


def test_missing_wellness_policy_is_insufficient_evidence(service: PolicyService) -> None:
    result = service.answer("Atlas", "employee", date(2026, 9, 21), "wellness")

    assert result.status == PolicyStatus.INSUFFICIENT_EVIDENCE
    assert result.answer is None
    assert result.citations == []


def test_citation_quote_is_exact_source_text(service: PolicyService) -> None:
    result = service.answer("Atlas", "employee", date(2026, 9, 21), "training")

    assert result.citations[0].quote == "Manager approval is required before external training is booked."


def test_result_does_not_depend_on_record_order(tmp_path: Path) -> None:
    policies = json.loads(DEFAULT_POLICY_FILE.read_text(encoding="utf-8"))
    reordered_file = tmp_path / "reordered-policies.json"
    reordered_file.write_text(json.dumps(list(reversed(policies))), encoding="utf-8")
    reordered_service = PolicyService(PolicyRepository(reordered_file))

    result = reordered_service.answer("Atlas", "employee", date(2026, 9, 21), "home-office")

    assert result.status == PolicyStatus.CONFLICT
    assert [citation.chunk_id for citation in result.citations] == [
        "atlas-home-office-a",
        "atlas-home-office-b",
    ]


def test_exact_duplicate_policy_record_does_not_create_conflict(tmp_path: Path) -> None:
    policies = json.loads(DEFAULT_POLICY_FILE.read_text(encoding="utf-8"))
    policies.append(next(policy for policy in policies if policy["id"] == "atlas-cert-current"))
    duplicated_file = tmp_path / "duplicated-policies.json"
    duplicated_file.write_text(json.dumps(policies), encoding="utf-8")
    duplicated_service = PolicyService(PolicyRepository(duplicated_file))

    result = duplicated_service.answer("Atlas", "employee", date(2026, 9, 21), "certification")

    assert result.status == PolicyStatus.ANSWERED
    assert len(result.citations) == 1

