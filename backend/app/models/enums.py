from enum import StrEnum


class Visibility(StrEnum):
    PRIVATE = "private"
    PROJECT = "project"
    PUBLIC = "public"


class ResourceKind(StrEnum):
    AGENT = "agent"
    WORKFLOW = "workflow"
    TOOL = "tool"
    SKILL = "skill"
    MCP = "mcp"
    KNOWLEDGE_BASE = "knowledge_base"
