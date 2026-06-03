from app.core.config import settings
from app.runtime.providers import ChatGenerationRequest, provider_factory


class RuntimeExecutor:
    """Runtime that dispatches chat generation to configured model providers."""

    def run_chat(
        self,
        text: str,
        model_provider: str | None = None,
        model_name: str | None = None,
        system_prompt: str | None = None,
    ) -> str:
        provider_name = model_provider or settings.runtime_default_provider
        resolved_model = model_name or self._default_model(provider_name)

        try:
            client = provider_factory.get_client(provider_name)
            return client.generate(
                ChatGenerationRequest(
                    text=text,
                    model_name=resolved_model,
                    system_prompt=system_prompt,
                )
            )
        except Exception as exc:
            return f"[runtime-fallback:{provider_name}] {text} | error={exc}"

    def _default_model(self, provider_name: str) -> str:
        if provider_name.strip().lower() == "openai":
            return settings.openai_default_model
        return settings.localhost_default_model


runtime_executor = RuntimeExecutor()
