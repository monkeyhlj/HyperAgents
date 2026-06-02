class RuntimeExecutor:
    """Runtime skeleton for future model, MCP, tool, and workflow execution."""

    def run_chat(self, text: str, agent_id: str | None) -> str:
        if agent_id:
            return f"[agent:{agent_id}] Received: {text}"
        return f"[default-agent] Received: {text}"


runtime_executor = RuntimeExecutor()
