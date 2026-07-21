"""Tests for Agent Engine (Phase 1 basic framework).

Tests the core components:
- LangChainLLMWrapper: LLM provider adaptation
- ReActAgent: Agent orchestration
- ToolManager: Tool loading and management
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from app.runtime.agent_engine import LangChainLLMWrapper, ReActAgent, ToolManager


class TestLangChainLLMWrapper:
    """Test LangChain LLM Wrapper."""

    def test_wrapper_initialization(self):
        """Test LLM wrapper can be initialized."""
        mock_llm_service = Mock()
        wrapper = LangChainLLMWrapper(
            llm_service=mock_llm_service,
            model_name="gpt-4o-mini",
            temperature=0.7,
        )
        assert wrapper.model_name == "gpt-4o-mini"
        assert wrapper.temperature == 0.7
        assert wrapper._llm_type == "hyperagents"

    def test_wrapper_properties(self):
        """Test wrapper properties."""
        mock_llm_service = Mock()
        wrapper = LangChainLLMWrapper(llm_service=mock_llm_service)
        assert wrapper._llm_type == "hyperagents"


class TestReActAgent:
    """Test ReAct Agent."""

    def test_agent_initialization(self):
        """Test agent can be initialized."""
        mock_llm = Mock(spec=LangChainLLMWrapper)
        mock_tool_manager = Mock(spec=ToolManager)

        agent = ReActAgent(
            llm=mock_llm,
            tool_manager=mock_tool_manager,
            max_iterations=5,
        )

        assert agent.max_iterations == 5
        assert agent.llm == mock_llm
        assert agent.tool_manager == mock_tool_manager

    def test_system_prompt_generation(self):
        """Test system prompt is generated correctly."""
        mock_llm = Mock(spec=LangChainLLMWrapper)
        mock_tool_manager = Mock(spec=ToolManager)

        agent = ReActAgent(llm=mock_llm, tool_manager=mock_tool_manager)

        tools = [
            {
                "name": "weather",
                "description": "Get weather info",
            },
            {
                "name": "calculator",
                "description": "Do math",
            },
        ]

        prompt = agent._build_system_prompt(tools)

        assert "weather" in prompt
        assert "calculator" in prompt
        assert "Thought:" in prompt
        assert "Action:" in prompt

    def test_parse_action_with_valid_action(self):
        """Test parsing valid action from thought."""
        mock_llm = Mock(spec=LangChainLLMWrapper)
        mock_tool_manager = Mock(spec=ToolManager)

        agent = ReActAgent(llm=mock_llm, tool_manager=mock_tool_manager)

        thought = """Thought: I need to get the weather for Beijing.
Action: weather
Input: {"location": "Beijing"}"""

        tool_dict = {"weather": {"name": "weather"}}

        action = agent._parse_action(thought, tool_dict)

        assert action is not None
        assert action["tool"] == "weather"
        assert action["input"]["location"] == "Beijing"

    def test_parse_action_with_final_answer(self):
        """Test parsing when agent decides to provide final answer."""
        mock_llm = Mock(spec=LangChainLLMWrapper)
        mock_tool_manager = Mock(spec=ToolManager)

        agent = ReActAgent(llm=mock_llm, tool_manager=mock_tool_manager)

        thought = """Thought: I have all the information needed.
Final Answer: Beijing's weather is cloudy with 22°C."""

        action = agent._parse_action(thought, {})

        assert action is not None
        assert action.get("type") == "final_answer"

    def test_extract_final_answer(self):
        """Test extracting final answer from thought."""
        mock_llm = Mock(spec=LangChainLLMWrapper)
        mock_tool_manager = Mock(spec=ToolManager)

        agent = ReActAgent(llm=mock_llm, tool_manager=mock_tool_manager)

        thought = """Thought: I have enough information.
Final Answer: The answer is 42."""

        answer = agent._extract_final_answer(thought)

        assert "42" in answer


class TestToolManager:
    """Test Tool Manager."""

    def test_tool_manager_initialization(self):
        """Test tool manager can be initialized."""
        manager = ToolManager()
        assert manager.tools == {}
        assert manager._builtin_tools is not None

    def test_builtin_tools_exist(self):
        """Test built-in tools are registered."""
        manager = ToolManager()
        assert "calculator" in manager._builtin_tools
        assert "web_search" in manager._builtin_tools
        assert "current_time" in manager._builtin_tools

    def test_load_builtin_tool(self):
        """Test loading a built-in tool."""
        manager = ToolManager()
        tool = manager._load_builtin_tool("calculator")

        assert tool is not None
        assert tool.name == "calculator"
        assert "expression" in tool.parameters["properties"]

    def test_load_tools_empty_config(self):
        """Test loading tools with empty agent config."""
        manager = ToolManager()
        agent_config = {}
        context = {}

        tools = manager.load_tools(agent_config, context)

        assert isinstance(tools, list)


@pytest.mark.asyncio
async def test_calculator_tool():
    """Test calculator tool executor."""
    manager = ToolManager()
    result = await manager._calculator_executor(expression="2 + 2")
    assert "4" in result


@pytest.mark.asyncio
async def test_current_time_tool():
    """Test current time tool executor."""
    manager = ToolManager()
    result = await manager._current_time_executor()
    assert "20" in result or "19" in result  # Should contain year


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
