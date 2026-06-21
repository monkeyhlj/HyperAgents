from app.runtime.llm_service import LLMRequest, llm_service


class RuntimeExecutor:
    """Compatibility wrapper around the unified llm_service gateway."""

    def run_chat(
        self,
        text: str,
        model_provider: str | None = None,
        model_name: str | None = None,
        provider_profile: str | None = None,
        system_prompt: str | None = None,
    ) -> str:
        response = llm_service.generate(
            LLMRequest(
                text=text,
                model_provider=model_provider,
                model_name=model_name,
                provider_profile=provider_profile,
                system_prompt=system_prompt,
            )
        )
        return response.text


runtime_executor = RuntimeExecutor()
