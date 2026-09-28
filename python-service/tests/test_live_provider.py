import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient

from app.live_provider import CallBudget, OpenAIProvider
from app.provider import GenerationService, ProviderFailure
from app.policy_service import PolicyService
from app.policy_repository import PolicyRepository
from app.settings import build_generation

QUOTE = "The annual certification reimbursement limit for employees is INR 25000."


def envelope(explanation="The annual certification limit is INR 25000.", quotes=None):
    return {"status": "completed", "output": [{"type": "message", "content": [
        {"type": "output_text", "text": json.dumps({"explanation": explanation,
         "evidence_quotes": quotes if quotes is not None else [QUOTE]})}]}]}


def provider(tmp_path, handler, limit=50):
    return OpenAIProvider("test-key-not-real", CallBudget(tmp_path / "budget.db", limit),
                          client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_live_contract_and_tenant_filtering(tmp_path):
    calls = []
    def handle(request):
        body = json.loads(request.content)
        calls.append(body)
        assert request.url == "https://api.openai.com/v1/responses"
        assert body["store"] is False and body["max_output_tokens"] == 800
        assert body["text"]["format"]["strict"] is True
        assert json.loads(body["input"])["evidence"] == [QUOTE]
        assert "80000" not in body["input"] and "999999" not in body["input"]
        return httpx.Response(200, json=envelope())
    live = provider(tmp_path, handle)
    service = PolicyService(PolicyRepository(), GenerationService(live))
    result = service.answer_question("Atlas", "employee", date(2026,9,21), "What is my certification limit?")
    assert result.answer == QUOTE and result.explanation == "The annual certification limit is INR 25000."
    assert len(calls) == live.budget.used() == 1
    for benefit in ("home-office", "wellness"):
        service.answer("Atlas", "employee", date(2026,9,21), benefit)
    assert len(calls) == 1


@pytest.mark.parametrize("payload", [
    envelope("The limit is INR 999999."), envelope(quotes=["Fabricated policy"]),
    envelope(" "), {"status": "incomplete", "output": []},
    {"status": "completed", "output": [{"type":"message", "content":[{"type":"refusal"}]}]},
    [],
])
def test_rejects_unsupported_or_incomplete_output(tmp_path, payload):
    live = provider(tmp_path, lambda r: httpx.Response(200, json=payload))
    with pytest.raises(ProviderFailure, match="unsupported output") as exc:
        GenerationService(live).compose("certification limit", (QUOTE,))
    assert exc.value.code == "MALFORMED_MODEL_OUTPUT"
    assert live.budget.used() == 1


@pytest.mark.parametrize("mode,code", [("timeout","PROVIDER_TIMEOUT"),("429","PROVIDER_UNAVAILABLE"),("500","PROVIDER_UNAVAILABLE")])
def test_no_retries_and_failed_calls_consume_budget(tmp_path, mode, code):
    calls = []
    def handle(request):
        calls.append(request)
        if mode == "timeout":
            raise httpx.ReadTimeout("private detail", request=request)
        return httpx.Response(int(mode), text="private detail")
    live = provider(tmp_path, handle)
    with pytest.raises(ProviderFailure) as exc:
        GenerationService(live).compose("certification limit", (QUOTE,))
    assert exc.value.code == code and "private" not in str(exc.value)
    assert len(calls) == live.budget.used() == 1


def test_budget_is_atomic_and_survives_restart(tmp_path):
    path = tmp_path / "budget.db"
    budget = CallBudget(path, 5)
    def reserve(_):
        try:
            budget.reserve()
            return True
        except ProviderFailure:
            return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(reserve, range(20))) == 5
    assert CallBudget(path, 5).used() == 5
    live = provider(tmp_path, lambda r: pytest.fail("Budget exhausted: must not send HTTP"), limit=5)
    with pytest.raises(ProviderFailure) as exc:
        live.generate_context("certification", (QUOTE,))
    assert exc.value.code == "MODEL_CALL_LIMIT"


def test_input_limit_prevents_spend(tmp_path):
    live = provider(tmp_path, lambda r: pytest.fail("Oversized input: must not send HTTP"))
    with pytest.raises(ProviderFailure):
        live.generate_context("q" * 4001, (QUOTE,))
    assert live.budget.used() == 0


def test_configuration_fails_closed(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "typo")
    with pytest.raises(ValueError):
        build_generation()
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        build_generation()


def test_internal_authentication(monkeypatch):
    from app.main import app
    monkeypatch.setattr(app.state, "internal_token", "x"*32)
    client = TestClient(app)
    body = {"tenant":"Atlas", "role":"employee", "as_of":"2026-09-21", "question":"certification limit"}
    assert client.post("/internal/answer", json=body).status_code == 401
    assert client.post("/internal/answer", json=body, headers={"X-Internal-Token":"wrong"}).status_code == 401
    assert client.post("/internal/answer", json=body, headers={"X-Internal-Token":"x"*32}).status_code == 200
    assert client.get("/health").status_code == 200
