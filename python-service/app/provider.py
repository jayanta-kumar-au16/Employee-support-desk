"""One bounded generation attempt, using an offline model double by default."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from threading import BoundedSemaphore
from typing import Protocol


class ProviderFailure(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class AnswerProvider(Protocol):
    def generate(self, quotations: tuple[str, ...]) -> object: ...


class OfflineProvider:
    """Extractive model double: no network, instructions, or invented facts."""
    def generate(self, quotations: tuple[str, ...]) -> object:
        return {"answer": " ".join(dict.fromkeys(quotations))}


_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="answer-provider")
_slots = BoundedSemaphore(4)


class GenerationService:
    def __init__(self, provider: AnswerProvider | None = None, timeout: float = 1.0):
        if timeout <= 0:
            raise ValueError("Provider timeout must be positive")
        self.provider = provider or OfflineProvider()
        self.timeout = timeout

    def answer(self, quotations: tuple[str, ...]) -> str:
        if not _slots.acquire(blocking=False):
            raise ProviderFailure("PROVIDER_UNAVAILABLE", "Answer provider is busy")
        try:
            future = _pool.submit(self.provider.generate, quotations)
        except Exception:
            _slots.release()
            raise ProviderFailure("PROVIDER_UNAVAILABLE", "Answer provider is unavailable") from None
        future.add_done_callback(lambda _: _slots.release())
        try:
            output = future.result(timeout=self.timeout)
        except FutureTimeout:
            future.cancel()
            raise ProviderFailure("PROVIDER_TIMEOUT", "Answer provider timed out") from None
        except Exception:
            raise ProviderFailure("PROVIDER_UNAVAILABLE", "Answer provider is unavailable") from None
        expected = " ".join(dict.fromkeys(quotations))
        if not isinstance(output, dict) or set(output) != {"answer"} or output["answer"] != expected:
            raise ProviderFailure("MALFORMED_MODEL_OUTPUT", "Answer provider returned unsupported output")
        return expected
