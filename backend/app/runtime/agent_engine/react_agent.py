"""ReAct Agent: Reasoning + Acting pattern implementation."""

import json
import logging
import re
from typing import Optional, Any
from datetime import datetime

from app.runtime.agent_engine.llm_wrapper import LangChainLLMWrapper
from app.runtime.agent_engine.tool_manager import ToolManager

logger = logging.getLogger(__name__)


class AgentEvent:
    """Record of a single agent step (thought, action, or observation)."""

    def __init__(
        self,
        stage: str,  # "thought" | "action" | "observation" | "final_answer"
        iteration: int = 0,
        content: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_input: Optional[dict] = None,
        tool_result: Optional[Any] = None,
        error: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        self.stage = stage
        self.iteration = iteration
        self.content = content
        self.tool_name = tool_name
        self.tool_input = tool_input
        self.tool_result = tool_result
        self.error = error
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "stage": self.stage,
            "iteration": self.iteration,
            "content": self.content,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "tool_result": self.tool_result,
            "error": self.error,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class ReActAgent:
    """ReAct Agent: Reasoning + Acting pattern.

    Implements the ReAct loop:
    1. Thought: LLM reasons about next action
    2. Action: Extract tool to call from LLM response
    3. Observation: Execute tool and observe result
    4. Repeat until final answer

    Supports any OpenAI-compatible model, not limited by function calling support.
    """

    def __init__(
        self,
        llm: LangChainLLMWrapper,
        tool_manager: ToolManager,
        max_iterations: int = 10,
        iteration_timeout: int = 30,
    ):
        """Initialize ReAct agent.

        Args:
            llm: LangChainLLMWrapper instance
            tool_manager: ToolManager instance for loading tools
            max_iterations: Maximum thought-action-observation cycles
            iteration_timeout: Timeout per iteration in seconds
        """
        self.llm = llm
        self.tool_manager = tool_manager
        self.max_iterations = max_iterations
        self.iteration_timeout = iteration_timeout
        self.events: list[AgentEvent] = []

    async def run(
        self,
        user_input: str,
        agent_config: dict,
        context: dict,
        system_prompt: Optional[str] = None,
    ) -> tuple[str, list[dict]]:
        """Execute ReAct loop (async).

        Args:
            user_input: User's question or command
            agent_config: Agent configuration (mcp_ids, tools, etc.)
            context: Execution context with MCPs, tools, KB definitions
            system_prompt: Optional custom system prompt

        Returns:
            Tuple of (final_answer, events_list)
        """
        self.events = []

        try:
            # Load tools for this agent
            tools = self.tool_manager.load_tools(agent_config, context)
            
            # Build tool dict with proper schema handling
            tool_dict = {}
            for tool in tools:
                if "function" in tool:
                    # OpenAI schema format
                    name = tool["function"].get("name", "unknown")
                else:
                    # Flat format
                    name = tool.get("name", "unknown")
                tool_dict[name] = tool

            logger.info(
                f"ReAct Agent starting: user_input_len={len(user_input)}, "
                f"tools={len(tools)}, max_iterations={self.max_iterations}"
            )

            # Build system prompt
            if not system_prompt:
                system_prompt = self._build_system_prompt(tools)

            # Initialize conversation
            messages = [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_input,
                },
            ]

            # ReAct Loop
            for iteration in range(self.max_iterations):
                logger.debug(f"ReAct iteration {iteration + 1}/{self.max_iterations}")

                # Step 1: Thought - LLM reasons
                thought = self._get_thought(messages, tools)
                self.events.append(
                    AgentEvent(
                        stage="thought",
                        iteration=iteration,
                        content=thought,
                    )
                )

                # Step 2: Action - Parse action from thought
                action = self._parse_action(thought, tool_dict)

                if action is None or action.get("type") == "final_answer":
                    # Agent decided to finish
                    final_answer = self._extract_final_answer(thought)
                    self.events.append(
                        AgentEvent(
                            stage="final_answer",
                            iteration=iteration,
                            content=final_answer,
                        )
                    )
                    logger.info(
                        f"ReAct Agent finished: iterations={iteration + 1}, "
                        f"final_answer_len={len(final_answer)}"
                    )
                    return final_answer, [e.to_dict() for e in self.events]

                # Record action
                self.events.append(
                    AgentEvent(
                        stage="action",
                        iteration=iteration,
                        tool_name=action["tool"],
                        tool_input=action.get("input"),
                    )
                )

                # Step 3: Observation - Execute tool
                try:
                    tool_def = tool_dict.get(action["tool"])
                    if not tool_def:
                        observation = (
                            f"Error: Tool '{action['tool']}' not found. "
                            f"Available tools: {', '.join(tool_dict.keys())}"
                        )
                    else:
                        # Execute tool
                        try:
                            result = await self.tool_manager.execute_tool(
                                tool_name=action["tool"],
                                tool_input=action.get("input", {}),
                                agent_config=agent_config,
                                context=context,
                            )
                            observation = str(result)
                            logger.debug(f"Tool execution succeeded: {action['tool']}")
                        except Exception as tool_error:
                            observation = f"Tool error: {str(tool_error)}"
                            logger.warning(f"Tool execution error: {action['tool']} - {str(tool_error)}")

                    self.events.append(
                        AgentEvent(
                            stage="observation",
                            iteration=iteration,
                            tool_name=action["tool"],
                            tool_result=observation,
                        )
                    )

                    # Add to conversation
                    messages.append({"role": "assistant", "content": thought})
                    messages.append(
                        {"role": "user", "content": f"Tool result: {observation}"}
                    )

                except Exception as e:
                    error_msg = f"Tool execution failed: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    self.events.append(
                        AgentEvent(
                            stage="observation",
                            iteration=iteration,
                            tool_name=action["tool"],
                            error=error_msg,
                        )
                    )
                    # Add error to conversation
                    messages.append({"role": "assistant", "content": thought})
                    messages.append({"role": "user", "content": error_msg})

            # Max iterations reached
            final_answer = (
                "Unable to reach conclusion within maximum iterations. "
                "Please try a simpler question."
            )
            self.events.append(
                AgentEvent(
                    stage="final_answer",
                    iteration=self.max_iterations - 1,
                    content=final_answer,
                    metadata={"reason": "max_iterations_reached"},
                )
            )
            logger.warning(f"ReAct Agent reached max iterations without answer")
            return final_answer, [e.to_dict() for e in self.events]

        except Exception as e:
            logger.error(f"ReAct Agent error: {str(e)}", exc_info=True)
            error_response = f"Agent execution failed: {str(e)}"
            self.events.append(
                AgentEvent(
                    stage="final_answer",
                    content=error_response,
                    error=str(e),
                )
            )
            return error_response, [e.to_dict() for e in self.events]

    def _build_system_prompt(self, tools: list[dict]) -> str:
        """Build system prompt with available tools."""
        # Extract tool names from OpenAI schema format
        tool_list = []
        for t in tools:
            # Handle both OpenAI schema format (with type/function keys) 
            # and flat format (with name directly)
            if "function" in t:
                name = t["function"].get("name", "unknown")
                desc = t["function"].get("description", "No description")
            else:
                name = t.get("name", "unknown")
                desc = t.get("description", "No description")
            tool_list.append((name, desc))

        tool_names = ", ".join([f"'{name}'" for name, _ in tool_list])
        tool_descriptions = "\n".join([f"- {name}: {desc}" for name, desc in tool_list])

        return f"""You are a helpful AI assistant with access to the following tools:

{tool_descriptions if tool_descriptions else "(No tools available)"}

IMPORTANT: You MUST follow this exact format when responding:

Thought: <your reasoning about what to do>
Action: <choose ONE tool name from the list above>
Input: <JSON object with parameters>

EXAMPLE:
User: What is the weather in Beijing?
Thought: I need to check the weather for Beijing. I have a tool that can get weather information.
Action: get_weather
Input: {{"location": "Beijing"}}

When you have all the information needed to fully answer the user's question, respond with:
Thought: I now have enough information to answer
Final Answer: <your detailed final answer to the user, including all relevant details>

RULES:
- ALWAYS respond in the format: Thought, Action, Input OR Final Answer
- Action must be EXACTLY one of: {tool_names if tool_names else "(none)"}
- Input must be valid JSON
- Use tools first, only provide Final Answer when you have the information needed
- When providing Final Answer, include ALL relevant information from the tool results
- Be comprehensive and detailed in your final answer"""

    def _get_thought(self, messages: list[dict], tools: list[dict]) -> str:
        """Get LLM thought (reasoning)."""
        # Note: Don't pass tools to LLM if model doesn't support function calling
        # (e.g., Zhipu GLM models). Instead, tools are listed in system prompt.
        # LLM will specify tool usage in its thought output (Action: tool_name format).
        response = self.llm._generate_with_messages(
            messages=messages,
            tools=None,  # Don't pass tools - use system prompt instead
        )
        return response.text or "No response"

    def _parse_action(
        self, thought: str, tool_dict: dict
    ) -> Optional[dict]:
        """Parse action from LLM thought response.

        Tries to parse format:
        Thought: ...
        Action: tool_name
        Input: {...}

        Returns:
            Dict with 'tool' and 'input' keys, or None if final answer or parse error
        """
        try:
            # Check for final answer (high priority)
            if re.search(r"(Final Answer:|最终答案:)", thought, re.IGNORECASE):
                return {"type": "final_answer"}

            # Try to find Action field
            action_match = re.search(
                r"Action:\s*([^\n\r,]+?)(?:\s*[\r\n,]|$)", thought, re.IGNORECASE
            )

            if not action_match:
                # If strict format fails, try to find any tool name mentioned
                logger.debug(f"No Action: format found, trying loose matching...")
                for tool_name in tool_dict.keys():
                    if tool_name.lower() in thought.lower():
                        # Found tool name mentioned, assume that's the tool
                        input_match = re.search(
                            r"Input:\s*(\{[^}]+\}|\[.*?\])", thought, re.IGNORECASE | re.DOTALL
                        )
                        tool_input = {}
                        if input_match:
                            try:
                                tool_input = json.loads(input_match.group(1))
                            except json.JSONDecodeError:
                                pass
                        logger.info(f"Using loose match for tool: {tool_name}")
                        return {"tool": tool_name, "input": tool_input}
                
                logger.warning(f"Could not parse Action from thought: {thought[:100]}")
                return None

            tool_name = action_match.group(1).strip().strip("'\"").strip()

            # Validate tool exists (case-insensitive match)
            matched_tool = None
            for valid_name in tool_dict.keys():
                if valid_name.lower() == tool_name.lower():
                    matched_tool = valid_name
                    break

            if not matched_tool:
                logger.warning(f"Tool '{tool_name}' not found in available tools: {list(tool_dict.keys())}")
                return None

            # Parse input
            tool_input = {}
            input_match = re.search(
                r"Input:\s*(\{[^}]+\}|\[.*?\]|\"[^\"]*\"|[^\n,]+)", thought, re.IGNORECASE | re.DOTALL
            )
            if input_match:
                try:
                    input_str = input_match.group(1).strip()
                    # Try JSON first
                    tool_input = json.loads(input_str)
                except json.JSONDecodeError:
                    logger.debug(f"Could not parse input JSON: {input_str}")
                    # Try to extract as key-value pairs
                    tool_input = self._parse_key_value_input(input_str)

            return {"tool": matched_tool, "input": tool_input}

        except Exception as e:
            logger.error(f"Error parsing action: {str(e)}")
            return None

    def _parse_key_value_input(self, input_str: str) -> dict:
        """Parse input as key=value pairs when JSON parsing fails."""
        result = {}
        # Simple key=value parser
        pairs = re.findall(r'(\w+)\s*=\s*(["\']?)([^",\'"]+)\2', input_str)
        for key, _, value in pairs:
            result[key] = value
        return result

    def _extract_final_answer(self, thought: str) -> str:
        """Extract final answer from thought."""
        match = re.search(
            r"Final Answer:\s*(.+)$",
            thought,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            return match.group(1).strip()
        return thought  # Return full thought if no explicit final answer

    def _format_observation(self, result: Any) -> str:
        """Format tool result as observation."""
        if isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False, indent=2)
        elif isinstance(result, list):
            return json.dumps(result, ensure_ascii=False, indent=2)
        elif isinstance(result, str):
            return result
        else:
            return str(result)
