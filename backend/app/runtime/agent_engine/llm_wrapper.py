"""LangChain LLM Wrapper: Adapt HyperAgents providers to LangChain interface."""

from typing import Any, Optional
import logging

from pydantic import ConfigDict
from langchain_core.language_models import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun

from app.runtime.providers import ProviderGenerationResponse
from app.runtime.llm_service import LLMService, LLMRequest

logger = logging.getLogger(__name__)


class LangChainLLMWrapper(LLM):
    """Wrapper adapting HyperAgents LLM providers to LangChain LLM interface.

    This class enables seamless integration between HyperAgents' multi-provider
    LLM abstraction and LangChain's agent framework.

    Attributes:
        llm_service: The LLMService instance to delegate calls to
        model_name: Model name to use (e.g., "gpt-4o", "glm-5.1")
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum tokens to generate
        provider: Provider name ("openai", "localhost", etc.)
        provider_profile: Optional provider configuration profile name
    """

    llm_service: Any = None  # LLMService instance
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    provider: str = "openai"
    provider_profile: Optional[str] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    @property
    def _llm_type(self) -> str:
        """Return type of LLM."""
        return "hyperagents"

    def _call(
        self,
        prompt: str,
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call the LLM (single string interface).

        Args:
            prompt: Input prompt
            stop: Stop sequences
            run_manager: Callback manager
            **kwargs: Additional arguments

        Returns:
            Generated text
        """
        try:
            response = self.llm_service.generate(
                request=LLMRequest(
                    text=prompt,
                    model_provider=self.provider,
                    model_name=self.model_name,
                    provider_profile=self.provider_profile,
                    system_prompt=None,
                )
            )

            return response.text or ""

        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}", exc_info=True)
            return f"Error: {str(e)}"

    def _generate_with_messages(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        **kwargs: Any,
    ) -> ProviderGenerationResponse:
        """Generate response from message list (used by ReAct agent).

        Args:
            messages: Conversation messages
            tools: Tool definitions in OpenAI format
            **kwargs: Additional arguments

        Returns:
            ProviderGenerationResponse
        """
        request = LLMRequest(
            text="",  # Text field required but will use messages instead
            model_provider=self.provider,
            model_name=self.model_name,
            provider_profile=self.provider_profile,
            messages=messages,
            tools=tools,
        )

        response = self.llm_service.generate(request)
        return response
