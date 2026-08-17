"""
LLM Agent Client.

Interactive CLI that receives natural language queries and orchestrates
tool calls to MCP servers (API and Database) through a local LLM.

The agent follows a cache-first pattern:
1. Check local DB first
2. If not found, query external API
3. Offer to save new data to local DB
"""

import asyncio
import json
import logging
import os

import requests
from fastmcp import Client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Agent] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:latest")
OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api")
MCP_DB_URL = os.getenv("MCP_DB_URL", "http://127.0.0.1:8001/mcp/")
MCP_API_URL = os.getenv("MCP_API_URL", "http://127.0.0.1:8002/mcp")

SYSTEM_PROMPT = (
    "You are an agent that works with a local database and an external API.\n"
    "NEVER use your own knowledge about Dragon Ball.\n"
    "ALWAYS obtain data using the available tools.\n"
    "First, query the local database.\n"
    "If the character is not found, query the external API.\n"
    "If the user wants to save it, call the insertion tools.\n"
    "Never respond with character data without calling a tool first."
)

# Tool routing: which MCP server handles each tool
DB_TOOLS = ["get_character_by_name", "insert_location_if_not_exists", "insert_character"]
API_TOOLS = ["get_character_from_api"]


def get_tool_definitions():
    """Returns the tool definitions for Ollama's function calling."""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_character_by_name",
                "description": "Look up a character by name in the local database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "nombre": {"type": "string", "description": "Character name"}
                    },
                    "required": ["nombre"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_character_from_api",
                "description": "Look up a character by name in the Dragon Ball API",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "nombre": {"type": "string", "description": "Character name"}
                    },
                    "required": ["nombre"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "insert_location_if_not_exists",
                "description": "Insert a planet into the local DB if it doesn't already exist",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "nombre_planeta": {"type": "string", "description": "Planet name"}
                    },
                    "required": ["nombre_planeta"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "insert_character",
                "description": "Insert a character into the local DB with a relationship to their origin planet",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "personaje": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "race": {"type": "string"},
                                "gender": {"type": "string"},
                                "ki": {"type": "string"},
                                "maxKi": {"type": "string"},
                                "affiliation": {"type": "string"}
                            }
                        },
                        "location": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "name": {"type": "string"}
                            }
                        }
                    },
                    "required": ["personaje", "location"]
                }
            }
        }
    ]


async def mcp_call(function_name: str, params: dict):
    """Routes a tool call to the correct MCP server and returns the result."""
    if function_name in DB_TOOLS:
        url = MCP_DB_URL
    elif function_name in API_TOOLS:
        url = MCP_API_URL
    else:
        return f"Error: unknown tool '{function_name}'"

    logger.info("Calling MCP tool: %s → %s", function_name, url)

    client = Client(url)
    async with client:
        return await client.call_tool(function_name, params)


def execute_tool_call(tool_call: dict) -> str:
    """Executes a single tool call from Ollama's response."""
    function_name = tool_call["function"]["name"]
    function_params = tool_call["function"]["arguments"]

    if isinstance(function_params, str):
        function_params = json.loads(function_params)

    logger.info("Tool: %s | Params: %s", function_name, function_params)

    result = asyncio.run(mcp_call(function_name, function_params))
    return json.dumps(result, default=str, ensure_ascii=False)


def chat(message: str, history: list = None, max_iterations: int = 10) -> str:
    """
    Sends a message to the LLM and processes any tool calls recursively.

    Args:
        message: User's input message.
        history: Conversation history (maintained across turns).
        max_iterations: Safety limit to prevent infinite tool call loops.

    Returns:
        The LLM's final text response.
    """
    if max_iterations <= 0:
        return "Error: too many tool calls, operation cancelled."

    if history is None:
        history = []

    # Inject system prompt on first call
    if not any(msg.get("role") == "system" for msg in history):
        history.insert(0, {"role": "system", "content": SYSTEM_PROMPT})

    if message:
        history.append({"role": "user", "content": message})

    payload = {
        "model": OLLAMA_MODEL,
        "messages": history,
        "stream": False,
        "tools": get_tool_definitions()
    }

    try:
        response = requests.post(f"{OLLAMA_BASE_URL}/chat", json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logger.error("Failed to connect to Ollama: %s", e)
        return "Error: could not connect to the LLM."

    assistant_message = data["message"]
    history.append(assistant_message)

    # If the LLM wants to call tools, execute them and recurse
    if assistant_message.get("tool_calls"):
        for tool in assistant_message["tool_calls"]:
            tool_result = execute_tool_call(tool)
            history.append({"role": "tool", "content": tool_result})

        return chat("", history, max_iterations - 1)

    return assistant_message.get("content", "")


def main():
    """Interactive CLI loop."""
    print("\n=== Dragon Ball LLM Agent ===")
    print("Ask about any character. Type 'exit' to quit.\n")

    history = []

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            print("Goodbye!")
            break

        reply = chat(user_input, history)
        print(f"Agent: {reply}\n")


if __name__ == "__main__":
    main()