import asyncio
import json
import sys
import httpx
from typing import Optional, Dict, List, Any
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self, ollama_url="http://localhost:11434"):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.ollama_url = ollama_url
    
    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()
        
        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])
        print("\nConnected to server with tools:", json.dumps([
            {
                "name": tool.name,
                "description": tool.description if hasattr(tool, "description") else "",
                "input_schema": tool.inputSchema if hasattr(tool, "inputSchema") else {}
            } for tool in tools
        ], indent=2))
        return tools
    
    async def test_tools(self):
        """Test the available tools on the server"""
        if not self.session:
            raise ValueError("Not connected to a server")
            
        # Test the search_arxiv tool
        print("--- Testing arxiv search ---")
        arxiv_query = "machine learning generative models"
        arxiv_response = await self.session.call_tool("search_arxiv", {"query": arxiv_query, "max_results": 3})
        print(f"ArXiv search results for '{arxiv_query}':")
        # The content is a list of content parts. We expect TextContent here.
        print(json.dumps([part.text for part in arxiv_response.content if hasattr(part, 'text')], indent=2))
        
        # Test the search_serp tool
        print("--- Testing SERP search ---")
        serp_query = "latest advancements in artificial intelligence"
        serp_response = await self.session.call_tool("search_serp", {"query": serp_query, "num_results": 3})
        print(f"SERP search results for '{serp_query}':")
        # The content is a list of content parts. We expect TextContent here.
        print(json.dumps([part.text for part in serp_response.content if hasattr(part, 'text')], indent=2))
        
        # Test the health check tool
        print("--- Testing health check ---")
        health_response = await self.session.call_tool("health_check", {})
        print("Health check status:", json.dumps([part.model_dump() for part in health_response.content if hasattr(part, 'json')], indent=2))
    
    async def process_query(self, query: str) -> str:
        """Process a query using Ollama and available tools"""
        if not self.session:
            raise ValueError("Not connected to a server")
            
        # Get available tools
        response = await self.session.list_tools()
        available_tools_info = [{
            "name": tool.name,
            "description": tool.description if hasattr(tool, "description") else "",
            "input_schema": tool.inputSchema if hasattr(tool, "inputSchema") else {}
        } for tool in response.tools]
        
        # Format tools information for Ollama prompt
        tools_description = "\n".join([
            f"Tool: {tool['name']}\nDescription: {tool['description']}\nSchema: {json.dumps(tool['input_schema'])}"
            for tool in available_tools_info
        ])
        
        # Create system prompt with tools information
        system_prompt = f"""You are an AI assistant with access to the following tools:
{tools_description}

When you need to use a tool, respond with a JSON object in the format:
{{
  "tool_calls": [
    {{
      "name": "tool_name",
      "args": {{
        "param1": "value1",
        "param2": "value2"
      }}
    }}
  ]
}}

Only include the tool_calls object when you need to use a tool. Otherwise, respond directly.
"""
        
        # Send request to Ollama
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": "llama3",  # Specify your model here
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ],
                    "stream": False
                }
            )
            response.raise_for_status()
            ollama_response = response.json()
        
        # Process response and check for tool calls
        final_text = []
        response_content = ollama_response["message"]["content"]
        
        # Try to extract tool calls from response
        try:
            # Check if response contains a JSON block with tool calls
            import re
            json_matches = re.findall(r'```json\n(.*?)\n```|({[\s\S]*"tool_calls"[\s\S]*})', response_content, re.DOTALL)
            
            tool_calls_json = None
            for match_tuple in json_matches:
                for match in match_tuple:
                    if match and '"tool_calls"' in match:
                        tool_calls_json = match
                        break
                if tool_calls_json:
                    break
                    
            if tool_calls_json:
                # Parse the JSON
                tool_calls_data = json.loads(tool_calls_json)
                
                if "tool_calls" in tool_calls_data and tool_calls_data["tool_calls"]:
                    # Extract non-JSON text from response
                    text_parts = response_content.split("```")
                    text_response = ""
                    for i, part in enumerate(text_parts):
                        if i % 2 == 0:  # Even parts are text, odd parts are code blocks
                            text_response += part
                    
                    final_text.append(text_response.strip())
                    
                    # Process each tool call
                    for tool_call in tool_calls_data["tool_calls"]:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["args"]
                        
                        # Execute tool call
                        result = await self.session.call_tool(tool_name, tool_args)
                        final_text.append(f"\n[Calling tool {tool_name} with args {json.dumps(tool_args)}]")
                        final_text.append(f"\n[Tool result: {json.dumps(result.content)}]\n")
                        
                        # Send follow-up with tool results to Ollama
                        follow_up_response = await client.post(
                            f"{self.ollama_url}/api/chat",
                            json={
                                "model": "llama3",
                                "messages": [
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": query},
                                    {"role": "assistant", "content": response_content},
                                    {"role": "user", "content": f"Tool '{tool_name}' returned: {json.dumps(result)}. Please provide your final answer."}
                                ],
                                "stream": False
                            }
                        )
                        follow_up_response.raise_for_status()
                        follow_up_result = follow_up_response.json()
                        final_text.append(follow_up_result["message"]["content"])
                else:
                    # No tool calls, just use the original response
                    final_text.append(response_content)
            else:
                # No JSON found, just use the original response
                final_text.append(response_content)
        except Exception as e:
            # If parsing fails, just return the original response
            final_text.append(f"Error parsing tool calls: {str(e)}")
            final_text.append(response_content)

        return "\n".join(final_text)
    
    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == 'quit':
                    break
                    
                if query.lower() == 'test':
                    await self.test_tools()
                    continue

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)
        
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.test_tools()
        # Uncomment the following line to enable interactive chat
        # await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())