from datetime import date
import re

from app.evidence import policy_fact
from app.models import Citation, PolicyAnswer, PolicyStatus
from app.policy_repository import PolicyRepository
from app.provider import GenerationService
from app.retrieval import PolicyRetriever, query_benefits


class PolicyService:
    def __init__(self, repository: PolicyRepository, generation: GenerationService | None = None) -> None:
        self._repository = repository
        self._retriever = PolicyRetriever(repository)
        self._generation = generation or GenerationService()

    @staticmethod
    def insufficient() -> PolicyAnswer:
        return PolicyAnswer(status=PolicyStatus.INSUFFICIENT_EVIDENCE, answer=None, citations=[])

    def answer(self, tenant: str, role: str, as_of: date, benefit: str,
               required_fact: str | None = None, question: str | None = None) -> PolicyAnswer:
        normalized = benefit.strip().lower()
        hits = self._retriever.retrieve(tenant, role, as_of, question or normalized, normalized, required_fact)
        # Keep the public citation/answer ordering stable, independent of ranking.
        policies = sorted((hit.policy for hit in hits), key=lambda p: (p["id"], p["text"]))
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
        answer, explanation = self._generation.compose(
            question or f"Explain the applicable {normalized} policy terms.", tuple(p["text"] for p in policies))
        return PolicyAnswer(status=PolicyStatus.ANSWERED, answer=answer, citations=citations, explanation=explanation)

    def answer_question(self, tenant: str, role: str, as_of: date, question: str) -> PolicyAnswer:
        matched = query_benefits(question)
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
        return self.answer(tenant, role, as_of, matched[0], kind, question)
