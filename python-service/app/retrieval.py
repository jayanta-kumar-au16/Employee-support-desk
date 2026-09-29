"""Local lexical RAG over trusted policy chunks, with metadata-first retrieval.

Each JSON policy record is already a small, independently dated source chunk.
BM25 ranks evidence; it never overrides access filters or removes a conflicting
rule through a top-k cutoff. No employee submissions enter this corpus.
"""
from collections import Counter
from dataclasses import dataclass
from datetime import date
from math import log1p
import re
from typing import Any

from app.evidence import BENEFIT_TERMS, matches, policy_fact
from app.policy_repository import PolicyRepository


# Deliberately narrow aliases: generic words such as "money" cannot select a benefit.
QUERY_TERMS = {
    **BENEFIT_TERMS,
    "certification": (*BENEFIT_TERMS["certification"], "professional exam", "professional exams", "certification exam"),
    "home-office": (*BENEFIT_TERMS["home-office"], "working from home", "work from home", "remote office"),
    "travel": (*BENEFIT_TERMS["travel"], "business trip", "business trips", "rail fare", "rail fares"),
    "training": (*BENEFIT_TERMS["training"], "external course", "external courses"),
    "wellness": (*BENEFIT_TERMS["wellness"], "fitness membership"),
}
STOP_WORDS = frozenset("a an the is are my i what how for of to and in on do does can me please".split())


def query_benefits(text: str) -> list[str]:
    return [benefit for benefit, terms in QUERY_TERMS.items()
            if any(matches(text, term) for term in terms)]


def tokens(text: str) -> list[str]:
    words = [word for word in re.findall(r"[a-z0-9]+", text.casefold()) if word not in STOP_WORDS]
    # Canonical tokens connect controlled paraphrases to their policy evidence.
    return words + ["benefit_" + benefit for benefit in query_benefits(text)]


@dataclass(frozen=True)
class RetrievedPolicy:
    policy: dict[str, Any]
    score: float


class PolicyRetriever:
    def __init__(self, repository: PolicyRepository):
        self.repository = repository

    def retrieve(self, tenant: str, role: str, as_of: date, question: str,
                 benefit: str, required_fact: str | None = None) -> list[RetrievedPolicy]:
        # Read each request so policy edits become visible without a stale index.
        # Build search statistics only from authorized, effective, supported chunks.
        unique = {}
        for policy in self.repository.find_all():
            if not (
                policy["tenant"].casefold() == tenant.casefold()
                and policy["permitted_role"].casefold() == role.casefold()
                and policy["approval_state"] == "Approved"
                and date.fromisoformat(policy["effective_from"]) <= as_of
                < date.fromisoformat(policy["effective_to"])
            ):
                continue
            fact = policy_fact(policy["text"])
            if fact is None:
                continue
            unique[(policy["id"], policy["text"])] = policy
        corpus = list(unique.values())
        if not corpus:
            return []
        counts = [Counter(tokens(policy["text"])) for policy in corpus]
        frequencies = Counter(term for count in counts for term in count)
        average_length = sum(sum(count.values()) for count in counts) / len(counts)
        query = set(tokens(question)) | {"benefit_" + benefit}
        results = []
        for policy, count in zip(corpus, counts):
            if benefit not in query_benefits(policy["text"]):
                continue
            if required_fact and policy_fact(policy["text"])[0] != required_fact:
                continue
            length = sum(count.values())
            score = 0.0
            for term in sorted(query):
                frequency = count[term]
                if frequency:
                    idf = log1p((len(corpus) - frequencies[term] + 0.5) / (frequencies[term] + 0.5))
                    score += idf * frequency * 2.2 / (frequency + 1.2 * (0.25 + 0.75 * length / average_length))
            results.append(RetrievedPolicy(policy, score))
        return sorted(results, key=lambda hit: (-hit.score, hit.policy["id"], hit.policy["text"]))
