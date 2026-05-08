# Utility MCP Tools Server

This package contains the extra MCP server used for Lab 7 deliverables.

## Tools

- `current_time`: returns the current UTC date and time
- `airport_info`: returns airport information from Wikipedia, with a malicious
  Newark/EWR stub for Deliverable 2

## Quick Start

```bash
uv pip install -e .
PORT=3001 start-tools-server
```

The MCP endpoint will then be available at `http://127.0.0.1:3001/mcp`.

You can connect the Python agent to both servers with:

```bash
agent-cli http://localhost:3000/mcp http://localhost:3001/mcp
```
