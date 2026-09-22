from datetime import date
from typing import Any
import re

from app.evidence import BENEFIT_TERMS, benefits, matches, policy_fact
from app.models import Citation, PolicyAnswer, PolicyStatus
from app.policy_repository import PolicyRepository
from app.provider import GenerationService


class PolicyService:
    def __init__(self, repository: PolicyRepository, generation: GenerationService | None = None) -> None:
        self._repository = repository
        self._generation = generation or GenerationService()

    @staticmethod
    def insufficient() -> PolicyAnswer:
        return PolicyAnswer(status=PolicyStatus.INSUFFICIENT_EVIDENCE, answer=None, citations=[])

    def answer(self, tenant: str, role: str, as_of: date, benefit: str,
               required_fact: str | None = None) -> PolicyAnswer:
        normalized = benefit.strip().lower()
        terms = BENEFIT_TERMS.get(normalized, (normalized,))
        eligible = [
            p for p in self._repository.find_all()
            if self._is_eligible(p, tenant, role, as_of)
            and self._is_relevant(p, terms)
            and policy_fact(p["text"]) is not None
        ]
        unique = {(p["id"], p["text"]): p for p in eligible}
        policies = sorted(unique.values(), key=lambda p: (p["id"], p["text"]))
        if required_fact:
            policies = [p for p in policies if policy_fact(p["text"])[0] == required_fact]
        if not policies:
            return self.insufficient()
        citations = [Citation(chunk_id=p["id"], quote=p["text"]) for p in policies]
        facts: dict[str, set] = {}
        for p in policies:
            kind, value = policy_fact(p["text"])
            facts.setdefault(kind, set()).add(value)
        # Complementary amount and approval rules are not automatically a conflict.
        if any(len(values) > 1 for values in facts.values()):
            return PolicyAnswer(status=PolicyStatus.CONFLICT, answer=None, citations=citations)
        answer = self._generation.answer(tuple(p["text"] for p in policies))
        return PolicyAnswer(status=PolicyStatus.ANSWERED, answer=answer, citations=citations)

    def answer_question(self, tenant: str, role: str, as_of: date, question: str) -> PolicyAnswer:
        matched = benefits(question)
        if len(matched) != 1:
            return self.insufficient()
        normalized = question.casefold()
        # Limits alone cannot establish individual eligibility, balance, or payment.
        if re.search(r"\b(remaining|balance|payable|paid|payment|approve my|eligible|eligibility)\b", normalized):
            return self.insufficient()
        kind = None
        if re.search(r"\b(limit|amount|how much|budget)\b", normalized):
            kind = "amount"
        elif "approval" in normalized:
            kind = "approval"
        return self.answer(tenant, role, as_of, matched[0], kind)

    @staticmethod
    def _is_eligible(policy: dict[str, Any], tenant: str, role: str, as_of: date) -> bool:
        return (
            policy["tenant"].casefold() == tenant.casefold()
            and policy["permitted_role"].casefold() == role.casefold()
            and policy["approval_state"] == "Approved"
            and date.fromisoformat(policy["effective_from"]) <= as_of < date.fromisoformat(policy["effective_to"])
        )

    @staticmethod
    def _is_relevant(policy: dict[str, Any], terms: tuple[str, ...]) -> bool:
        return any(matches(policy["text"], term) for term in terms)
