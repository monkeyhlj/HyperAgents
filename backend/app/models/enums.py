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


class MemoryType(StrEnum):
    CONVERSATION = "conversation"
    PROJECT = "project"
    AGENT = "agent"
    EXECUTION = "execution"
    GLOBAL = "global"


class MemoryScope(StrEnum):
    CONVERSATION = "conversation"
    PROJECT = "project"
    AGENT = "agent"
    EXECUTION = "execution"
    GLOBAL = "global"


class EmbeddingStatus(StrEnum):
    SKIPPED = "skipped"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
