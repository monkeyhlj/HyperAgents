"""Debug script to check tool schema format."""
import sys
import json

# Setup path
sys.path.insert(0, '/app')

from app.runtime.agent_engine.tool_manager import Tool, MCPTool

# Create a mock MCP tool
mcp_endpoint = {
    'transport': 'sse',
    'endpoint_url': 'https://mcp.amap.com/sse?key=19685d46b28ebc43f781bbeb5685e74b',
    'timeout_seconds': 8
}

tool_def = {
    "name": "get_weather",
    "description": "Get weather information for a location",
    "inputSchema": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "Location for weather info"
            }
        },
        "required": ["location"]
    }
}

# Create MCPTool
tool = MCPTool(mcp_endpoint, tool_def)

# Check schemas
print("to_openai_schema():")
print(json.dumps(tool.to_openai_schema(), indent=2))

print("\nto_langchain_schema():")
print(json.dumps(tool.to_langchain_schema(), indent=2))

# Also test basic Tool
print("\n\nBasic Tool test:")
basic_tool = Tool(
    name="test_tool",
    description="A test tool",
    parameters={
        "type": "object",
        "properties": {
            "param": {"type": "string"}
        }
    }
)
print("to_openai_schema():")
print(json.dumps(basic_tool.to_openai_schema(), indent=2))
