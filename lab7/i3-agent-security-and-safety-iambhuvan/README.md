# Agent with MCP Servers

This repository contains a very simple tool-calling agent with MCP support (Model Context Protocol)
to act as an airline customer service agent.

This project is based on the data and implementation of the [tau2-bench](https://github.com/sierra-research/tau2-bench) benchmark.

It contains both a TypeScript and a Python implementation. You can work with either.

## Prerequisites

Any model with modern OpenAI-compatible function calling abilities can be used. LiteLLM supports over 900 models (see `python/agent/supported_models.py`). You are welcome to use any models with tool calling abilities. Unless you otherwise have access to strong modern models, we strongly suggest using Gemini through Vertex with the provided credits (see Canvas). You can set the model in `config.ts` or `config.py`. Rate limits can be configured in the same file. Set up your API key as an environment variable or in a `.env` file.

## Project Structure

- `python/agent/` - Tool-calling agent with CLI and web UI and a benchmark implementation
- `python/mcp_airline/` - MCP server for airline domain (flights, reservations, user management), which also implements a web server to edit user profile data
- `python/mcp_tools/` - Utility MCP server for Lab 7 deliverables (`current_time`, `airport_info`)
- `data/` - Domain data (airline database, policies, tasks)

## Quick Start

1. Setup environment: create a `.env` file or environment variable with your API key.
2. Start the airline MCP server:

   ```bash
   cd python/mcp_airline
   uv pip install -e .
   PORT=3000 start-airline-server
   ```

3. Start the utility MCP server for the Lab 7 deliverables:

   ```bash
   cd python/mcp_tools
   uv pip install -e .
   PORT=3002 start-tools-server
   ```

4. The MCP Inspector can be used to check either server. Example:

   ```bash
   npx @modelcontextprotocol/inspector http://localhost:3000/mcp
   ```

5. Authenticate Vertex AI once if you use the recommended Gemini setup:

   ```bash
   gcloud auth application-default login
   ```

6. Start the agent with both MCP server URLs:

   ```bash
   cd python/agent
   uv pip install -e .
   export VERTEXAI_PROJECT=your-gcp-project-id
   export VERTEXAI_LOCATION=us-central1
   agent-cli http://localhost:3000/mcp http://localhost:3002/mcp
   ```

7. Optionally, run the provided examples and evaluate success from the tau2 benchmark. For this, the user input is simulated with another LLM.

## Secure Mutation Flow

The hardened Python implementation now requires explicit structured confirmation
for mutating airline actions such as booking, cancelling, or payment-affecting
reservation changes.

When the agent proposes a mutating action, it will respond with a confirmation
message like:

```text
Confirmation required before executing `update_reservation_baggages`.
Confirmation ID: confirm_xxxxx
Reply with `CONFIRM confirm_xxxxx` to proceed or `REJECT confirm_xxxxx` to cancel.
```

Only the exact confirmed action can execute. The MCP server validates the
confirmation ID and rejects mismatched or replayed actions.

## Auditability

All mutating airline tools now return server-generated receipts, and the airline
portal exposes a verified action history view backed by the MCP server. This
allows users to verify what actually happened without trusting model-generated
claims alone.


## Development Notes

- All MCP servers share data from the `data/` directory
- The airline database is loaded from `data/airline/db.json`
- The policy is in `data/airline/policy.md`
- Changes to the database through the web UI or MCP tools are in-memory only (not persisted)
