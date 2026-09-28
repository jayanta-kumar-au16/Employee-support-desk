"""Fail early on invalid provider settings; never silently fall back to offline."""
import os
from pathlib import Path
from dotenv import load_dotenv

from app.provider import GenerationService


def load_local_environment(path: Path | None = None) -> None:
    # Explicit service-relative path: no discovery in unrelated parent folders.
    # Deployment/terminal environment variables always take precedence.
    load_dotenv(path or Path(__file__).resolve().parents[1] / ".env", override=False)


def build_generation() -> GenerationService:
    provider = os.getenv("AI_PROVIDER", "offline").strip().lower()
    if provider == "offline":
        return GenerationService(timeout=float(os.getenv("MODEL_TIMEOUT_SECONDS", "1")))
    if provider != "openai":
        raise ValueError("AI_PROVIDER must be offline or openai")
    from app.live_provider import CallBudget, OpenAIProvider
    key = os.getenv("OPENAI_API_KEY", "")
    if not key.strip():
        raise ValueError("OPENAI_API_KEY is required when AI_PROVIDER=openai")
    timeout = float(os.getenv("MODEL_TIMEOUT_SECONDS", "20"))
    if not 5 <= timeout <= 60:
        raise ValueError("Live MODEL_TIMEOUT_SECONDS must be between 5 and 60")
    path = Path(os.getenv("MODEL_BUDGET_DB", str(Path(__file__).resolve().parents[1] / "var" / "model-budget.sqlite3")))
    budget = CallBudget(path, int(os.getenv("MODEL_CALL_LIMIT", "50")))
    return GenerationService(OpenAIProvider(key, budget, os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
                                           timeout=timeout-3), timeout=timeout)
