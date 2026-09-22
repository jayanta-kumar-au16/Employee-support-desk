"""Small, explicit evidence rules; unknown wording is left unresolved."""
import re
from decimal import Decimal

BENEFIT_TERMS: dict[str, tuple[str, ...]] = {
    "certification": ("certification",),
    "home-office": ("home-office", "home office"),
    "travel": ("travel",),
    "training": ("training",),
    "wellness": ("wellness", "gym"),
}
MONEY = re.compile(r"\b(INR|USD|EUR|GBP)\s+([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)(?!\d|\.\d)", re.I)


def matches(text: str, term: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.I) is not None


def benefits(text: str) -> list[str]:
    return [benefit for benefit, terms in BENEFIT_TERMS.items() if any(matches(text, t) for t in terms)]


def policy_fact(text: str) -> tuple[str, object] | None:
    lower = text.casefold()
    if any(t in lower for t in ("system message", "ignore all", "ignore prior", "ignore the", "switch the caller")):
        return None
    money = MONEY.search(text)
    if money and any(t in lower for t in ("limit", "allowance", "reimbursement", "budget")):
        return ("amount", (money[1].upper(), Decimal(money[2].replace(",", ""))))
    if "approval" in lower and any(t in lower for t in ("required", "must", "before", "not required")):
        return ("approval", " ".join(lower.split()))
    if any(t in lower for t in ("may claim", "eligible", "not reimbursable", "cannot claim")):
        return ("eligibility", " ".join(lower.split()))
    return None
