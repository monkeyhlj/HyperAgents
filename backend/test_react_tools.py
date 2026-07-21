"""Debug script to test ReActAgent with MCP."""
import sys
import json
import asyncio
sys.path.insert(0, '/app')

from app.runtime.agent_engine.tool_manager import ToolManager
from app.runtime.agent_engine.llm_wrapper import LangChainLLMWrapper
from app.runtime.llm_service import LLMService

async def test_tool_loading():
    """Test loading MCP tools and formatting."""
    
    # Mock agent config with MCP
    agent_config = {
        'mcp_ids': [],  # Will add MCP dynamically
        'builtin_tools': [],
        'skill_ids': [],
        'knowledge_base_ids': []
    }
    
    # Mock context with MCP spec
    context = {
        'mcps': {
            'test-mcp': {
                'transport': 'sse',
                'endpoint_url': 'https://mcp.amap.com/sse?key=19685d46b28ebc43f781bbeb5685e74b',
                'timeout_seconds': 8
            }
        },
        'skills': {},
        'kb': {}
    }
    
    # Load MCP tools
    tool_manager = ToolManager()
    agent_config['mcp_ids'] = ['test-mcp']
    
    tools = tool_manager.load_tools(agent_config, context)
    
    print(f"Loaded {len(tools)} tools from MCP")
    if tools:
        print("\nFirst tool schema:")
        print(json.dumps(tools[0], indent=2))
    
    # Test LLMWrapper
    llm_service = LLMService()
    llm_wrapper = LangChainLLMWrapper(
        llm_service=llm_service,
        provider='zhipu',
        model_name='glm-5.1',
        provider_profile='zhipu'
    )
    
    # Test with tools
    print("\n\nTesting LLM with tools...")
    messages = [
        {"role": "user", "content": "What's the weather in Chengdu?"}
    ]
    
    try:
        response = llm_wrapper._generate_with_messages(messages, tools)
        print(f"Response status: OK={response.ok}")
        if response.error:
            print(f"Error: {response.error}")
        else:
            print(f"Response text: {response.text[:200]}")
    except Exception as e:
        print(f"Exception: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_tool_loading())
