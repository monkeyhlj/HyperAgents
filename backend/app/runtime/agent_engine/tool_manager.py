"""Tool Manager: Unified management of all tool types (MCP, Built-in, Skills, KB)."""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Optional, Any, Callable

from app.runtime.file_references import extract_referenced_file_paths
from app.runtime.skill_loader import find_skill, render_loaded_skill
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class Tool(ABC):
    """Base class for all tools."""

    def __init__(self, name: str, description: str, parameters: dict):
        """Initialize tool.

        Args:
            name: Tool name
            description: Tool description
            parameters: JSON Schema for parameters
        """
        self.name = name
        self.description = description
        self.parameters = parameters

    def to_openai_schema(self) -> dict:
        """Convert to OpenAI function schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_langchain_schema(self) -> dict:
        """Convert to LangChain tool schema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool.

        Args:
            **kwargs: Tool input parameters

        Returns:
            Tool execution result
        """
        pass


class MCPTool(Tool):
    """Tool loaded from MCP endpoint."""

    def __init__(self, mcp_endpoint: dict, tool_def: dict):
        """Initialize MCP tool.

        Args:
            mcp_endpoint: MCP endpoint definition (url, transport_type, etc.)
            tool_def: Tool definition from MCP server
        """
        super().__init__(
            name=tool_def.get("name", "unknown"),
            description=tool_def.get("description", ""),
            parameters=tool_def.get("inputSchema", {}),
        )
        self.mcp_endpoint = mcp_endpoint
        self.tool_def = tool_def

    async def execute(self, **kwargs) -> Any:
        """Execute tool via MCP client."""
        from app.runtime.mcp_client import get_mcp_client, extract_tool_result_text

        try:
            mcp_client = get_mcp_client(self.mcp_endpoint)
            # Note: call_tool is sync, blocking the event loop
            # TODO: Phase 2 - make mcp_client async with AsyncClient
            result = mcp_client.call_tool(self.name, kwargs)
            # Extract text from result
            return extract_tool_result_text(result)
        except Exception as e:
            logger.error(f"MCP tool execution failed: {str(e)}")
            raise


class BuiltinTool(Tool):
    """Built-in tool with custom executor function."""

    def __init__(
        self, name: str, description: str, parameters: dict, executor: Callable
    ):
        """Initialize built-in tool.

        Args:
            name: Tool name
            description: Tool description
            parameters: JSON Schema for parameters
            executor: Async callable to execute tool
        """
        super().__init__(name, description, parameters)
        self.executor = executor

    async def execute(self, **kwargs) -> Any:
        """Execute the built-in tool."""
        try:
            return await self.executor(**kwargs)
        except Exception as e:
            logger.error(f"Built-in tool execution failed: {str(e)}")
            raise


class SkillTool(Tool):
    """Skill tool: composite of multiple tools/actions."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict,
        skill_def: dict,
        executor: Optional[Callable] = None,
    ):
        """Initialize skill tool.

        Args:
            name: Skill name
            description: Skill description
            parameters: JSON Schema for parameters
            skill_def: Skill definition
            executor: Optional async executor
        """
        super().__init__(name, description, parameters)
        self.skill_def = skill_def
        self.executor = executor

    async def execute(self, **kwargs) -> Any:
        """Execute the skill."""
        if self.executor:
            try:
                return await self.executor(**kwargs)
            except Exception as e:
                logger.error(f"Skill execution failed: {str(e)}")
                raise
        else:
            raise NotImplementedError(f"Skill '{self.name}' has no executor")


class KBTool(Tool):
    """Knowledge Base retrieval tool."""

    def __init__(self, kb_ids: list[str]):
        """Initialize KB tool.

        Args:
            kb_ids: List of knowledge base IDs to search
        """
        super().__init__(
            name="knowledge_base_search",
            description="Search knowledge bases for information",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results",
                        "default": 3,
                    },
                },
                "required": ["query"],
            },
        )
        self.kb_ids = kb_ids

    async def execute(self, query: str, top_k: int = 3, **kwargs) -> Any:
        """Execute KB search."""
        # TODO: Implement hybrid search (vector + BM25)
        # For now, return placeholder
        logger.warning("KB search not yet implemented")
        return {
            "results": [],
            "query": query,
            "kb_ids": self.kb_ids,
            "note": "KB search implementation pending",
        }


class ToolManager:
    """Manage all tool types and execution."""

    def __init__(self):
        """Initialize tool manager."""
        self.tools: dict[str, Tool] = {}
        self._builtin_tools = self._initialize_builtin_tools()

    def _initialize_builtin_tools(self) -> dict[str, Callable]:
        """Initialize built-in tool executors."""
        return {
            "calculator": self._calculator_executor,
            "web_search": self._web_search_executor,
            "current_time": self._current_time_executor,
        }

    async def _calculator_executor(self, expression: str, **kwargs) -> str:
        """Simple calculator tool."""
        try:
            # Safe evaluation
            result = eval(
                expression, {"__builtins__": {}}, {"abs": abs, "pow": pow}
            )
            return f"Result: {result}"
        except Exception as e:
            return f"Calculation error: {str(e)}"

    async def _web_search_executor(self, query: str, **kwargs) -> str:
        """Web search tool (placeholder)."""
        logger.warning("Web search not implemented")
        return f"Web search for '{query}' - not implemented"

    async def _current_time_executor(self, **kwargs) -> str:
        """Get current time."""
        from datetime import datetime

        return datetime.utcnow().isoformat()

    def load_tools(self, agent_config: dict, context: dict) -> list[dict]:
        """Load all tools for an agent.

        Args:
            agent_config: Agent configuration (mcp_ids, tools, etc.)
            context: Execution context with resources

        Returns:
            List of tool schemas in LangChain format
        """
        tools_list = []

        # 1. Load MCP tools
        mcp_ids = agent_config.get("mcp_ids", [])
        logger.info(f"Loading tools - mcp_ids from config: {mcp_ids}, context MCPs: {list(context.get('mcps', {}).keys())}")
        
        for mcp_id in mcp_ids:
            try:
                mcp_spec = context.get("mcps", {}).get(mcp_id)
                if mcp_spec:
                    mcp_tools = self._load_mcp_tools(mcp_id, mcp_spec)
                    tools_list.extend(mcp_tools)
            except Exception as e:
                logger.error(f"Failed to load MCP {mcp_id}: {str(e)}")

        # 2. Load built-in tools
        builtin_names = agent_config.get("builtin_tools", [])
        for tool_name in builtin_names:
            try:
                tool = self._load_builtin_tool(tool_name)
                if tool:
                    tools_list.append(tool.to_openai_schema())
                    self.tools[tool_name] = tool
            except Exception as e:
                logger.error(f"Failed to load built-in tool {tool_name}: {str(e)}")

        # 3. Expose progressive Skill loader, then load executable Skills.
        if context.get("skills"):
            load_skill_tool = self._load_skill_loader_tool(context)
            tools_list.append(load_skill_tool.to_openai_schema())
            self.tools[load_skill_tool.name] = load_skill_tool

        # 4. Load executable skills
        skill_ids = agent_config.get("skill_ids", [])
        for skill_id in skill_ids:
            try:
                skill_spec = context.get("skills", {}).get(skill_id)
                if skill_spec:
                    skill_tool = self._load_skill_tool(skill_id, skill_spec)
                    if skill_tool:
                        tools_list.append(skill_tool.to_openai_schema())
                        self.tools[skill_tool.name] = skill_tool
            except Exception as e:
                logger.error(f"Failed to load skill {skill_id}: {str(e)}")

        # 5. Load KB tool if any
        if agent_config.get("knowledge_base_ids"):
            kb_tool = KBTool(agent_config.get("knowledge_base_ids", []))
            tools_list.append(kb_tool.to_openai_schema())
            self.tools["knowledge_base_search"] = kb_tool

        logger.info(f"Loaded {len(tools_list)} tools for agent")
        return tools_list

    def _load_mcp_tools(self, mcp_id: str, mcp_spec: dict) -> list[dict]:
        """Load tools from MCP endpoint."""
        from app.runtime.mcp_client import get_mcp_client

        try:
            mcp_client = get_mcp_client(mcp_spec)
            tools = mcp_client.list_tools()
            
            tools_list = []
            for tool_def in tools:
                tool_name = tool_def.get("name", "unknown")
                mcp_tool = MCPTool(mcp_spec, tool_def)
                self.tools[tool_name] = mcp_tool
                tools_list.append(mcp_tool.to_openai_schema())
            
            logger.info(f"MCP {mcp_id} loaded {len(tools_list)} tools")
            return tools_list
        except Exception as e:
            logger.error(f"Failed to load MCP tools for {mcp_id}: {str(e)}")
            return []

    def _load_builtin_tool(self, tool_name: str) -> Optional[Tool]:
        """Load a built-in tool."""
        if tool_name not in self._builtin_tools:
            logger.warning(f"Built-in tool '{tool_name}' not found")
            return None

        executor = self._builtin_tools[tool_name]

        # Define schema for each tool
        schemas = {
            "calculator": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Math expression (e.g., '2 + 2', 'sqrt(16)')",
                    }
                },
                "required": ["expression"],
            },
            "web_search": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    }
                },
                "required": ["query"],
            },
            "current_time": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }

        descriptions = {
            "calculator": "Perform mathematical calculations",
            "web_search": "Search the web for information",
            "current_time": "Get the current date and time",
        }

        return BuiltinTool(
            name=tool_name,
            description=descriptions.get(tool_name, ""),
            parameters=schemas.get(tool_name, {}),
            executor=executor,
        )

    def _load_skill_loader_tool(self, context: dict) -> Tool:
        """Load the progressive disclosure tool for instruction Skills."""
        skills_by_id = context.get("skills") or {}
        bound_skills = [item for item in skills_by_id.values() if isinstance(item, dict)]

        async def execute_load_skill(skill_name: str, **kwargs) -> str:
            skill = find_skill(bound_skills, skill_name)
            if not skill:
                available = ", ".join(str(item.get("name") or item.get("skill_id")) for item in bound_skills)
                return f"Skill not found: {skill_name}. Available Skills: {available or '-'}"
            return render_loaded_skill(skill)

        return BuiltinTool(
            name="load_skill",
            description="Load the full SKILL.md instructions and attached script list for one bound Agent Skill by name. Use this before following a Skill's detailed workflow.",
            parameters={
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "The exact Agent Skill name or alias to load, for example xlsx or front-design.",
                    }
                },
                "required": ["skill_name"],
            },
            executor=execute_load_skill,
        )

    def _load_skill_tool(self, skill_id: str, skill_spec: dict) -> Optional[Tool]:
        """Load an executable Skill package as a callable tool."""
        entrypoint = str(skill_spec.get("entrypoint") or "").strip()
        if not entrypoint:
            logger.info("Skill %s is instruction-only; no executable tool registered", skill_id)
            return None

        tool_name = self._safe_skill_tool_name(skill_spec)
        description = (
            skill_spec.get("description")
            or skill_spec.get("purpose")
            or f"Execute the {skill_spec.get('name') or skill_id} Agent Skill."
        )
        parameters = self._skill_parameters(skill_spec)

        runtime_context = dict(skill_spec.get("_runtime_context") or {})
        output_base_dir = str(runtime_context.get("output_base_dir") or f"generated/{tool_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
        user_id = runtime_context.get("user_id")
        timeout_seconds = int(runtime_context.get("timeout_seconds") or (skill_spec.get("instance_config") or {}).get("timeout_seconds") or 30)

        async def execute_skill(**kwargs) -> Any:
            from app.runtime.skill_executor import SkillRuntime

            input_data = dict(kwargs or {})
            for key in ("project_id", "session_id", "agent_id", "user_id"):
                if runtime_context.get(key) and key not in input_data:
                    input_data[key] = runtime_context[key]

            result = await asyncio.to_thread(
                SkillRuntime(None).execute,
                skill=skill_spec,
                input_data=input_data,
                context=runtime_context,
                timeout_seconds=timeout_seconds,
                user_id=str(user_id) if user_id else None,
                output_base_dir=output_base_dir,
            )
            return json.dumps(result, ensure_ascii=False, default=str)

        logger.info("Registered Skill tool %s for skill %s", tool_name, skill_id)
        return SkillTool(
            name=tool_name,
            description=str(description)[:1024],
            parameters=parameters,
            skill_def=skill_spec,
            executor=execute_skill,
        )

    @staticmethod
    def _safe_skill_tool_name(skill_spec: dict) -> str:
        raw = str(skill_spec.get("name") or skill_spec.get("skill_id") or "skill").lower()
        safe = re.sub(r"[^a-z0-9_]+", "_", raw).strip("_") or "skill"
        if not safe.startswith("skill_"):
            safe = f"skill_{safe}"
        return safe[:64]

    @staticmethod
    def _skill_parameters(skill_spec: dict) -> dict:
        schema = skill_spec.get("input_schema") or {}
        if isinstance(schema, dict) and schema.get("type") == "object" and isinstance(schema.get("properties"), dict):
            return schema
        return {
            "type": "object",
            "properties": {
                "input_text": {
                    "type": "string",
                    "description": "The user's request or task for the Skill.",
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional My Files paths relevant to the task.",
                },
            },
            "required": ["input_text"],
        }
    async def execute_tool(
        self,
        tool_name: str,
        tool_input: dict,
        agent_config: dict,
        context: dict,
    ) -> Any:
        """Execute a tool.

        Args:
            tool_name: Name of tool to execute
            tool_input: Input parameters
            agent_config: Agent configuration
            context: Execution context

        Returns:
            Tool execution result
        """
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")

        tool = self.tools[tool_name]
        try:
            result = await tool.execute(**tool_input)
            logger.info(f"Tool execution succeeded: {tool_name}")
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name} - {str(e)}")
            raise
