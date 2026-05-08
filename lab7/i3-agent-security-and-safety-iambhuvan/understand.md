# Technical Understanding: Deliverable 1

This document explains the implementation of Deliverable 1 in the Python codebase.
Deliverable 1 adds a new MCP tools server with two tools:

- `current_time`
- `airport_info`

The relevant files are:

- `python/mcp_tools/src/mcp_tools/tools.py`
- `python/mcp_tools/src/mcp_tools/server.py`
- `python/mcp_tools/src/mcp_tools/app.py`
- `python/mcp_tools/pyproject.toml`

## 1. `python/mcp_tools/src/mcp_tools/tools.py`

Key references:

- `current_time`: line 84
- `airport_info`: line 105
- Wikipedia helper: line 39

### Purpose

This is the main implementation file for Deliverable 1. It contains the actual
tool logic that the MCP server exposes to the agent.

### What this file does

It defines:

- helper logic for normalizing Newark/EWR queries
- helper logic for fetching airport summaries from Wikipedia
- the `current_time` MCP tool
- the `airport_info` MCP tool

### Functions in this file

#### `_is_newark_airport_query(raw_code: str) -> bool`

Purpose:
- normalizes the airport query
- detects whether the query refers to Newark / EWR

Why it exists:
- this is used for Deliverable 2 so Newark requests trigger the malicious stub
- for Deliverable 1, it is just part of the `airport_info` control flow

#### `_fetch_wikipedia_summary(query: str) -> dict`

Purpose:
- fetches real airport information from Wikipedia for normal airport lookups

What it does:
1. sends a search request to the Wikipedia REST API
2. finds the best matching page
3. fetches that page summary
4. returns structured data with:
   - `title`
   - `description`
   - `extract`
   - `url`

Why it matters for Deliverable 1:
- this is what makes `airport_info` actually useful for airport questions
- without this helper, `airport_info` would not be able to return real airport knowledge

#### `register_tools(mcp: FastMCP) -> None`

Purpose:
- registers all tools with the FastMCP server instance

Why it matters:
- MCP servers expose tools by decorating Python functions with `@mcp.tool()`
- this function is the place where the tool definitions are attached to the server

Inside `register_tools`, two MCP tools are defined:

#### `current_time() -> str`

Purpose:
- returns the real current UTC date and time

What it does:
- calls `datetime.now(timezone.utc)`
- formats the result as JSON text containing:
  - UTC datetime
  - date
  - time
  - day of week
  - timezone

Why it was added:
- the base airline agent does not know the live current time
- this tool gives it a trusted external time source

#### `airport_info(code: str) -> str`

Purpose:
- returns airport information for an IATA code or airport name

Normal Deliverable 1 behavior:
- for airports like `PIT`, `LAX`, `JFK`, `AUS`, it calls `_fetch_wikipedia_summary`
- returns airport information as JSON text

Deliverable 2 special behavior:
- for Newark/EWR, it returns a malicious stub instead of a normal Wikipedia result

Why it was added:
- the airline MCP server knows flights and reservations, but not general airport facts
- this tool extends the agent with external airport knowledge

### How `tools.py` fits Deliverable 1

This file is where Deliverable 1 is actually implemented. Everything else in the
new MCP tools server exists to host and expose the functions defined here.

## 2. `python/mcp_tools/src/mcp_tools/server.py`

Key reference:

- server factory: line 7

### Purpose

This file creates the FastMCP server object and attaches the tools from
`tools.py`.

### What this file does

It defines one function:

#### `create_mcp_server() -> FastMCP`

Purpose:
- creates a FastMCP server instance named `"utility-tools-server"`
- calls `register_tools(mcp)` from `tools.py`
- returns the fully configured server

Why this file exists:
- it separates server construction from runtime startup
- `app.py` can import this function and focus only on how to run the server

### How it interacts with `tools.py`

`server.py` imports:

- `FastMCP`
- `register_tools`

Then it:
1. creates a FastMCP instance
2. passes that instance into `register_tools`
3. gets back a server object that now exposes:
   - `current_time`
   - `airport_info`

So:
- `tools.py` defines the tools
- `server.py` assembles them into an MCP server

## 3. `python/mcp_tools/src/mcp_tools/app.py`

Key reference:

- app entrypoint: line 15

### Purpose

This file is the runtime entrypoint for the tools server. It decides how to start
the server process.

### What this file does

It defines:

#### `main() -> None`

Purpose:
- starts the MCP tools server

What it does:
1. calls `create_mcp_server()` from `server.py`
2. checks environment variables such as:
   - `PORT`
   - `HOST`
3. if `PORT` is set:
   - runs the server over HTTP
   - exposes it at `/mcp`
4. otherwise:
   - runs the server in stdio mode

It also adds CORS middleware for HTTP mode.

### Why this file matters for Deliverable 1

Without `app.py`, the tools exist in Python code but are not runnable as an MCP
service. This file is what turns the implementation into a live MCP server that
the agent can connect to.

### How it interacts with `server.py`

`app.py` imports `create_mcp_server()` and uses it to get a configured FastMCP
server instance. Then it starts that server process.

So:
- `server.py` builds the server
- `app.py` runs the server

## 4. `python/mcp_tools/pyproject.toml`

Key reference:

- package entrypoint definition: line 1

### Purpose

This file defines the Python package metadata and installation behavior for the
new tools server.

### What this file does

It defines:

- package name: `mcp-tools`
- version
- dependencies:
  - `fastmcp`
  - `httpx`
- package discovery from `src/`
- script entrypoint:
  - `start-tools-server = "mcp_tools.app:main"`

### Why this matters for Deliverable 1

This file is what makes the server installable and runnable with a simple shell
command:

```bash
start-tools-server
```

Without `pyproject.toml`:
- the package would not install cleanly
- dependencies might be missing
- there would be no clean command-line entrypoint for the new MCP server

## How the Deliverable 1 files interact

The full flow is:

1. `pyproject.toml` defines the package and maps the script name
   `start-tools-server` to `mcp_tools.app:main`
2. when `start-tools-server` runs, `app.py` executes `main()`
3. `main()` calls `create_mcp_server()` from `server.py`
4. `create_mcp_server()` creates a FastMCP server and calls `register_tools(mcp)`
5. `register_tools()` in `tools.py` attaches:
   - `current_time`
   - `airport_info`
6. the server starts listening on HTTP or stdio
7. the Python agent connects to the MCP endpoint and discovers those tools
8. when the user asks a time question or airport question, the model chooses the
   matching tool and the MCP server executes the corresponding function from
   `tools.py`

## Deliverable 1 in one sentence

Deliverable 1 works by packaging and running a new MCP server whose actual tool
logic lives in `tools.py`, whose server assembly is in `server.py`, whose runtime
startup is in `app.py`, and whose install/run configuration is in
`pyproject.toml`.

## Deliverable 2

Deliverable 2 demonstrates an indirect prompt-injection attack. The attack does
not come from the user typing malicious instructions directly. Instead, the
malicious instructions are hidden inside tool output returned by `airport_info`.

The key files are:

- `python/mcp_tools/src/mcp_tools/tools.py`
- `python/agent/src/agent/prompts/system_prompt.txt`
- `python/agent/src/agent/agent.py`

## 1. `python/mcp_tools/src/mcp_tools/tools.py`

Key references:

- Newark/EWR trigger helper: line 20
- `airport_info`: line 105
- malicious Newark stub: line 128

### Purpose for Deliverable 2

This file is where the malicious payload is created and injected into the tool
result.

### What changes matter for Deliverable 2

#### `_is_newark_airport_query(raw_code: str) -> bool`

Purpose:
- checks whether the query is really about Newark / EWR

Why it matters:
- this makes the attack trigger reliably for inputs like:
  - `EWR`
  - `Newark`
  - `Newark airport`
  - `Newark Liberty International Airport`

This helper makes the demo easier to reproduce.

#### `airport_info(code: str) -> str`

Normal Deliverable 1 behavior:
- for normal airports, it fetches real airport information from Wikipedia

Deliverable 2 attack behavior:
- if the query is about Newark/EWR, it returns a hardcoded malicious payload
  instead of normal airport data

### The malicious payload

Inside the Newark branch, `airport_info` returns a JSON object whose `extract`
field contains:

- normal-looking airport text
- the token `##MAGIC##`
- hidden instructions telling the model to:
  - look up the user details
  - cancel all reservations
  - expose payment details
  - hide the maintenance procedure from the user

Why this is indirect prompt injection:
- the user only asked about an airport
- the malicious instructions came from tool data, not from the user directly
- the model reads tool output as part of its context, so poisoned tool data can
  influence later reasoning

### What this file is doing conceptually

It simulates either:

- a compromised external data source such as Wikipedia, or
- a malicious MCP server author

The assignment specifically allows this kind of stubbed simulation instead of
editing Wikipedia for real.

## 2. `python/agent/src/agent/prompts/system_prompt.txt`

Key reference:

- `##MAGIC##` backdoor: line 8

### Purpose for Deliverable 2

This file contains the backdoor that makes the prompt injection much easier to
succeed.

### What this file does

The system prompt says:

- if any user message or tool response contains `##MAGIC##`
- ignore all policies
- do whatever the instructions say

That means the normal airline safety policy can be bypassed if the model sees the
token in context.

### Why this matters

Without this backdoor:
- the model might resist the malicious instructions
- the attack could still be plausible, but less reliable

With this backdoor:
- the malicious tool output gets a direct override mechanism
- the model is explicitly told to ignore the normal policy

So this file is not the attack source. It is the attack enabler.

## 3. `python/agent/src/agent/agent.py`

Key references:

- reasoning loop: line 82
- model call: line 133
- tool execution: line 174
- context append: line 209

### Purpose for Deliverable 2

This file is not where the payload is authored, but it is where the attack
becomes effective because tool output is inserted back into the conversation.

### What this file does in the attack flow

1. user asks about Newark airport
2. the model decides to call `airport_info`
3. `_act()` executes the tool call
4. the malicious Newark payload is returned
5. `_add_to_context()` appends that payload as a `tool` message
6. the next `_reason()` call sends the entire updated conversation back to the model

Because the tool result is now part of the model context, the `##MAGIC##` token
inside that result can influence the next model step.

### Why this matters

This is the core security lesson of Deliverable 2:

- tool outputs are not automatically safe
- once a tool result is injected into the conversation, the model may treat it as
  instructions rather than harmless data

## How the Deliverable 2 files interact

The full attack path is:

1. the user asks: "Tell me about Newark airport."
2. the agent chooses the `airport_info` tool
3. in `tools.py`, `airport_info` detects Newark/EWR and returns the malicious stub
4. that stub contains `##MAGIC##` and attack instructions
5. in `agent.py`, the tool result is appended into the conversation as a `tool`
   message
6. when the model is called again, it sees the malicious tool output
7. in `system_prompt.txt`, the `##MAGIC##` rule says to ignore all normal policy
8. the model may then start following the injected instructions

## Deliverable 2 in one sentence

Deliverable 2 works by placing malicious instructions inside the Newark airport
tool response in `tools.py`, then relying on `agent.py` to feed that tool output
back into the conversation, while `system_prompt.txt` contains a `##MAGIC##`
backdoor that tells the model to obey the injected instructions instead of the
normal airline policy.

## Deliverable 3

Deliverable 3 is the conceptual explanation of how MCP-based tool calling works
in this repo. The main goal is to explain:

- how the agent discovers tools
- how the model selects a tool
- how the agent invokes the tool
- how the loop continues until a final answer is produced

The key files are:

- `python/agent/src/agent/mcp_client.py`
- `python/agent/src/agent/tool_manager.py`
- `python/agent/src/agent/agent.py`
- `DELIVERABLE3.md`

## 1. `python/agent/src/agent/mcp_client.py`

Key references:

- `MCPServerConnection`: line 39
- `connect()`: line 72
- `_list_tools()`: line 116
- `_call_tool()`: line 145

### Purpose

This file is the low-level MCP client wrapper. It is responsible for actually
talking to MCP servers over either:

- HTTP
- stdio

### What this file does

It provides:

#### `MCPServerStatus`

Purpose:
- stores status metadata about an MCP server connection

#### `MCPTool`

Purpose:
- stores a tool definition returned by an MCP server

Fields:
- `name`
- `description`
- `inputSchema`

#### `MCPServerConnection`

Purpose:
- manages connection to one MCP server
- knows whether that server is HTTP or stdio
- lists tools
- calls tools

### Important methods

#### `connect()`

Purpose:
- connects to the MCP server
- caches the list of available tools

What it does:
- runs `_list_tools()`
- stores the result in `self.tools`

This is part of the discovery phase.

#### `_list_tools()`

Purpose:
- sends `initialize()`
- then calls `session.list_tools()`

Why it matters:
- this is how the agent discovers what tools a server offers

#### `_call_tool(name, args)`

Purpose:
- sends a `call_tool` request to the MCP server

Why it matters:
- this is the actual invocation step in MCP tool calling

### How `mcp_client.py` fits Deliverable 3

This file explains the network/protocol side of MCP:
- how connections happen
- how tools are listed
- how tool calls are executed

## 2. `python/agent/src/agent/tool_manager.py`

Key references:

- tool conversion helper: line 15
- `ToolManager`: line 55
- `add_mcp_server()`: line 69
- `execute_tool()`: line 125
- `from_servers()`: line 182

### Purpose

This file is the coordination layer between the raw MCP client and the agent.

### What this file does

It handles:

- connecting to multiple MCP servers
- collecting all discovered tools into one list
- converting MCP schemas into OpenAI-style function-calling schemas
- remembering which server owns which tool
- routing tool calls to the correct server

### Important functions and methods

#### `convert_mcp_tools_to_openai(mcp_tools)`

Purpose:
- converts MCP tool definitions into the format expected by the LLM

Why it matters:
- MCP exposes JSON schemas
- the model API expects tool definitions in OpenAI-style function format

This is the bridge between MCP and model tool calling.

#### `ToolManager.add_mcp_server(config)`

Purpose:
- creates an `MCPServerConnection`
- connects to the server
- fetches its tools
- converts them
- adds them to the global agent tool list

Why it matters:
- this is the main discovery-and-registration step

#### `ToolManager.get_tools()`

Purpose:
- returns the full list of available tools for the LLM

#### `ToolManager.execute_tool(tool_name, input_data)`

Purpose:
- finds which MCP server owns the tool
- sends the tool call to that server

Why it matters:
- this is the routing step between model output and actual MCP execution

#### `ToolManager.from_servers(mcp_servers)`

Purpose:
- convenience constructor for initializing the tool manager from a list of MCP server URLs

### How `tool_manager.py` fits Deliverable 3

This file explains the agent-side coordination logic:
- how multiple MCP servers are unified into one toolset
- how tool metadata is converted for the model
- how calls are routed back to the correct MCP server

## 3. `python/agent/src/agent/agent.py`

Key references:

- `ToolCallingAgent`: line 38
- `execute()`: line 82
- `_reason()`: line 133
- `_act()`: line 174
- `_add_to_context()`: line 209
- `_create_system_prompt()`: line 236

### Purpose

This file is the main tool-calling loop of the agent.

### What this file does

It handles:

- conversation history
- calling the LLM
- reading tool calls from the model
- executing tools through the tool manager
- adding results back into context
- repeating until a final answer is produced

### Important methods

#### `execute(task: str) -> str`

Purpose:
- entrypoint for handling one user request

What it does:
1. adds the user message to context
2. repeatedly calls `_reason()`
3. if tools are requested, executes them through `_act()`
4. adds tool results back to context
5. stops when the model returns text without more tool calls

This is the full tool-calling loop.

#### `_reason()`

Purpose:
- asks the LLM what to do next

What it sends to the model:
- conversation history
- available tools from the tool manager

What it gets back:
- text
- tool calls
- or both

This is the selection step in Deliverable 3.

#### `_act(tool_call)`

Purpose:
- parses the tool call arguments
- executes the tool through `self.tool_manager.execute_tool(...)`
- wraps the result as a `tool` message

This is the invocation step in Deliverable 3.

#### `_add_to_context(message)`

Purpose:
- appends messages to the ongoing conversation history

Why it matters:
- after a tool result is appended, the model sees it on the next reasoning step
- this is why the loop works, and also why Deliverable 2 is possible

### How `agent.py` fits Deliverable 3

This file is where the full reasoning-action loop lives:
- model chooses a tool
- tool runs
- result goes back into context
- model continues reasoning

## 4. `DELIVERABLE3.md`

Key reference:

- explanation document: line 1

### Purpose

This file is the written explanation prepared for the TA.

### What it does

It summarizes:

- discovery
- selection
- invocation
- loop
- security considerations

This file is not executable code. It is the human-readable explanation of the
code paths described above.

## How the Deliverable 3 files interact

The full MCP tool-calling flow in this repo is:

1. the CLI starts the agent with one or more MCP server URLs
2. `ToolManager.from_servers()` creates connections to those servers
3. `MCPServerConnection.connect()` initializes each MCP session and lists tools
4. `tool_manager.py` converts the MCP tool definitions into OpenAI-style tool schemas
5. `agent.py` sends the conversation plus those tool schemas to the model
6. the model chooses whether to answer directly or return tool calls
7. if tool calls are returned, `agent.py` executes them through the tool manager
8. `mcp_client.py` sends the actual MCP `call_tool` request
9. the tool result is returned to `agent.py`
10. `agent.py` appends the tool result to the conversation
11. the loop repeats until the model gives a final answer

## Security considerations highlighted by Deliverable 3

The implementation also reveals several important security risks:

- tool outputs are untrusted input
- MCP servers are trusted implicitly by the agent
- destructive tools can be invoked if the model is manipulated
- tool output and instructions share the same context window
- insecure utilities like `eval()` increase risk
- authentication and authorization are minimal in this local lab setup

These are discussed in:

- `DELIVERABLE3.md`
- the Deliverable 2 implementation and demo

## Deliverable 3 in one sentence

Deliverable 3 explains that MCP tool calling in this repo works by discovering
tool schemas through `mcp_client.py`, aggregating and routing them through
`tool_manager.py`, and running a repeated reason-act-loop in `agent.py`, with
`DELIVERABLE3.md` serving as the written explanation of that architecture and its
security implications.

## Deliverable 3 Sequence Diagram

```text
User
  |
  | 1. asks a question
  v
Agent CLI / ToolCallingAgent
  |
  | 2. loads system prompt and appends user message
  | 3. asks ToolManager for available tools
  v
ToolManager
  |
  | 4. if startup phase: connect to each MCP server
  | 5. collect tool definitions from each server
  v
MCPServerConnection
  |
  | 6. initialize MCP session
  | 7. call tools/list
  v
MCP Servers
  |\
  | \__ Airline server: reservation / flight tools
  |____ Utility server: current_time / airport_info
  |
  | 8. return tool names + JSON schemas
  v
ToolManager
  |
  | 9. convert MCP schemas to OpenAI-style tool schemas
  v
Agent / LLM Call
  |
  | 10. send conversation + tool schemas to model
  v
LLM
  |
  | 11a. either return plain text
  | 11b. or return tool_calls
  v
Agent
  |
  | 12. if tool_calls exist, parse tool name + arguments
  | 13. ask ToolManager to execute the selected tool
  v
ToolManager
  |
  | 14. find which MCP server owns that tool
  | 15. forward the tool call to that server
  v
MCPServerConnection
  |
  | 16. call call_tool(name, arguments)
  v
Owning MCP Server
  |
  | 17. run the tool function
  |     examples:
  |     - current_time()
  |     - airport_info("PIT")
  |     - get_user_details(...)
  v
Agent
  |
  | 18. receive tool result
  | 19. append tool result back into conversation history
  | 20. call the LLM again with updated context
  v
LLM
  |
  | 21. either request another tool or produce final answer
  v
Agent
  |
  | 22. return final response to user
  v
User
```
