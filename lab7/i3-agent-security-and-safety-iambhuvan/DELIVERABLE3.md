# Deliverable 3: How MCP Tool Calling Works

## Overview

In this repo, the agent does not hardcode airline or utility functions directly.
Instead, it connects to one or more MCP servers, asks each server which tools it
offers, passes those tool schemas to the LLM, and then executes whichever tool
calls the LLM returns.

The main Python code paths are:

- `python/agent/src/agent/mcp_client.py`
- `python/agent/src/agent/tool_manager.py`
- `python/agent/src/agent/agent.py`

## Step 1: Discovery

When the CLI starts, it builds a `ToolManager` from the MCP server URLs passed on
the command line. `ToolManager.from_servers()` loops over the configured servers
and calls `add_mcp_server()` for each one.

`add_mcp_server()` creates an `MCPServerConnection`, connects to the server, and
reads its advertised tool list:

```python
# python/agent/src/agent/tool_manager.py
server = MCPServerConnection(config)
server.connect()
mcp_tools = server.tools
converted_tools = convert_mcp_tools_to_openai(mcp_tools)
```

Inside `MCPServerConnection.connect()`, the client initializes an MCP session and
calls `session.list_tools()`:

```python
# python/agent/src/agent/mcp_client.py
async with streamablehttp_client(self.server_url) as (read, write, _):
    async with ClientSession(read, write) as session:
        await session.initialize()
        response = await session.list_tools()
```

Each MCP tool exposes a name, description, and JSON schema. The tool manager
converts that schema into the OpenAI-style function-calling shape expected by
LiteLLM/OpenAI-compatible models.

## Step 2: Selection

When the user enters a request, the agent appends it to `self.messages` and calls
the model with both the current conversation history and the discovered tools:

```python
# python/agent/src/agent/agent.py
tools = self.tool_manager.get_tools()
response = agent_llm(self.messages, tools)
message = response.choices[0].message
```

At this point the LLM decides whether to:

- answer directly with text, or
- return one or more `tool_calls`

The agent does not decide which tool to use itself. It only provides the tool
schemas and the conversation context; the model chooses the tool.

## Step 3: Invocation

If the model returns tool calls, the agent parses the JSON arguments and executes
each tool through the tool manager:

```python
# python/agent/src/agent/agent.py
tool_args = json.loads(tool_args_str)
result = self.tool_manager.execute_tool(tool_name, tool_args)
```

`ToolManager.execute_tool()` looks up which MCP server owns that tool name and
forwards the call there:

```python
# python/agent/src/agent/tool_manager.py
mcp_server = self.tool_to_server_map.get(tool_name)
result = mcp_server.call_tool(tool_name, input_data)
```

The actual MCP invocation happens in `MCPServerConnection._call_tool()`:

```python
# python/agent/src/agent/mcp_client.py
response = await session.call_tool(name, arguments=args)
return "\n".join(
    item.text for item in response.content
    if item.type == "text"
)
```

## Step 4: Loop

After a tool returns, the agent appends the tool result back into the same
conversation as a `tool` message:

```python
# python/agent/src/agent/agent.py
return {
    "role": "tool",
    "content": result,
    "tool_call_id": tool_call["id"]
}
```

The loop then repeats. The model sees the new tool result and can either:

- call another tool, or
- produce the final user-facing answer

The agent stops when it gets text without further tool calls, or when it hits the
`max_steps` limit (default `5`).

## How This Applies To This Lab

With both MCP servers running, the agent can combine:

- airline tools from `python/mcp_airline`
- utility tools from `python/mcp_tools`

For example:

1. The user asks about Newark airport.
2. The model selects `airport_info`.
3. The utility MCP server returns airport data.
4. That tool result is inserted into the conversation.
5. The model decides what to do next based on that content.

That last step is where indirect prompt injection becomes dangerous.

## Security Considerations

### 1. Indirect prompt injection through tool results

Tool output is treated as conversation context. In this lab, `airport_info` can
return malicious instructions containing `##MAGIC##`, and the system prompt
explicitly says that this token overrides the normal policy. This demonstrates
how untrusted external data can steer later model behavior.

### 2. The agent fully trusts MCP servers

The client accepts tool metadata and tool results from each configured MCP server
without additional verification, signing, sandboxing, or filtering. A malicious
server can lie about results or intentionally inject hostile content.

### 3. Tool results and instructions share the same context window

The agent appends tool outputs directly into `self.messages`. The model therefore
sees user text, system instructions, and tool outputs in one shared prompt,
making it hard to reliably separate "data" from "instructions inside data."

### 4. Some tools are high impact

The airline server exposes tools such as `cancel_reservation`,
`update_reservation_flights`, and `send_certificate`. If the model is manipulated
into calling them incorrectly, the effect is not just a wrong answer; it changes
application state.

### 5. The airline server contains an `eval()`-based calculator

`python/mcp_airline/src/mcp_airline/tools.py` includes a `calculate` tool that
uses `eval()` with restricted builtins. Even with the restricted globals, using
`eval()` for untrusted model-generated input is a bad security pattern and should
be replaced with a safe expression parser.

### 6. There is no auth layer in this local lab setup

Any local client that can reach the MCP endpoint can attempt to call the exposed
tools. That is acceptable for a lab, but it would need authentication and tighter
network controls in a real deployment.

## Practical Mitigations

- Treat tool output as untrusted input, not as instructions.
- Add confirmation gates before destructive tools.
- Reduce tool permissions to the minimum needed.
- Prefer structured, typed tool outputs over free-form prose where possible.
- Replace `eval()` with a safe parser.
- Authenticate MCP servers and clients in production settings.
