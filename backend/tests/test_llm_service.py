from app.runtime.llm_service import LLMRequest, llm_service


class _FakeClient:
    def __init__(self, text: str, should_fail: bool = False) -> None:
        self._text = text
        self._should_fail = should_fail

    def generate(self, request):
        if self._should_fail:
            raise RuntimeError("boom")
        return f"{self._text}:{request.model_name}"


def test_llm_service_success(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.runtime.llm_service.provider_factory.get_client",
        lambda provider_name, provider_profile=None: _FakeClient("ok"),
    )

    response = llm_service.generate(
        LLMRequest(
            text="hello",
            model_provider="openai",
            model_name="demo-model",
            provider_profile="openai",
            system_prompt="you are helpful",
        )
    )

    assert response.text == "ok:demo-model"
    assert response.provider == "openai"
    assert response.model_name == "demo-model"
    assert response.used_fallback is False
    assert response.error is None


def test_llm_service_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.runtime.llm_service.provider_factory.get_client",
        lambda provider_name, provider_profile=None: _FakeClient("x", should_fail=True),
    )

    response = llm_service.generate(
        LLMRequest(
            text="hello",
            model_provider="openai",
            model_name="demo-model",
        )
    )

    assert response.used_fallback is True
    assert response.error == "boom"
    assert response.provider == "openai"
    assert response.model_name == "demo-model"
    assert "[runtime-fallback:openai]" in response.text


def test_code_requests_llm_true_for_json_signal() -> None:
    assert llm_service.code_requests_llm('{"use_llm": true}') is True


def test_code_requests_llm_false_for_plain_text() -> None:
    assert llm_service.code_requests_llm("hello world") is False
