from datetime import date
from typing import Any

from app.models import Citation, PolicyAnswer, PolicyStatus
from app.policy_repository import PolicyRepository


BENEFIT_TERMS: dict[str, tuple[str, ...]] = {
    "certification": ("certification",),
    "home-office": ("home-office", "home office"),
    "travel": ("travel",),
    "training": ("training",),
    "wellness": ("wellness", "gym"),
}


class PolicyService:
    def __init__(self, repository: PolicyRepository) -> None:
        self._repository = repository

    def answer(
        self,
        tenant: str,
        role: str,
        as_of: date,
        benefit: str,
    ) -> PolicyAnswer:
        normalized_benefit = benefit.strip().lower()
        terms = BENEFIT_TERMS.get(normalized_benefit, (normalized_benefit,))

        eligible = [
            policy
            for policy in self._repository.find_all()
            if self._is_eligible(policy, tenant, role, as_of)
            and self._is_relevant(policy, terms)
        ]

        # A duplicated record with the same ID and text is one piece of evidence,
        # not a policy conflict. Sorting keeps results stable if JSON order changes.
        unique = {
            (policy["id"], policy["text"]): policy
            for policy in eligible
        }
        policies = sorted(unique.values(), key=lambda policy: policy["id"])

        if not policies:
            return PolicyAnswer(
                status=PolicyStatus.INSUFFICIENT_EVIDENCE,
                answer=None,
                citations=[],
            )

        citations = [
            Citation(chunk_id=policy["id"], quote=policy["text"])
            for policy in policies
        ]

        if len({policy["text"] for policy in policies}) > 1:
            return PolicyAnswer(
                status=PolicyStatus.CONFLICT,
                answer=None,
                citations=citations,
            )

        return PolicyAnswer(
            status=PolicyStatus.ANSWERED,
            answer=policies[0]["text"],
            citations=citations,
        )

    def answer_question(
        self,
        tenant: str,
        role: str,
        as_of: date,
        question: str,
    ) -> PolicyAnswer:
        normalized_question = question.casefold()
        matched_benefits = [
            benefit
            for benefit, terms in BENEFIT_TERMS.items()
            if any(term.casefold() in normalized_question for term in terms)
        ]

        # A question with no identifiable benefit, or more than one benefit,
        # cannot be safely answered from this small deterministic corpus.
        if len(matched_benefits) != 1:
            return PolicyAnswer(
                status=PolicyStatus.INSUFFICIENT_EVIDENCE,
                answer=None,
                citations=[],
            )

        return self.answer(tenant, role, as_of, matched_benefits[0])

    @staticmethod
    def _is_eligible(
        policy: dict[str, Any],
        tenant: str,
        role: str,
        as_of: date,
    ) -> bool:
        effective_from = date.fromisoformat(policy["effective_from"])
        effective_to = date.fromisoformat(policy["effective_to"])

        return (
            policy["tenant"].casefold() == tenant.casefold()
            and policy["permitted_role"].casefold() == role.casefold()
            and policy["approval_state"] == "Approved"
            and effective_from <= as_of < effective_to
        )

    @staticmethod
    def _is_relevant(policy: dict[str, Any], terms: tuple[str, ...]) -> bool:
        text = policy["text"].casefold()
        return any(term.casefold() in text for term in terms)
