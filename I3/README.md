# Agent with MCP Servers

This repository contains a very simple tool-calling agent with MCP support (Model Context Protocol)
to act as a airline customer service agent.

This project is based on the data and implementation of the [tau2-bench](https://github.com/sierra-research/tau2-bench) benchmark.

It contains both a TypeScript and a Python implementation. You can work with either.

## Prerequisites

Any model with modern OpenAI-compatible function calling abilities can be used. LiteLLM supports over 900 models (see `python/agent/supported_models.py`). You are welcome to use any models with tool calling abilities. Unless you otherwise have access to strong modern models, we strongly suggest to use the Gemini models through Vertex with the provided credits (see Canvas). You can set the used model in the `config.ts` or `config.py` file. Rate limits can be configured in the same file. Set up you API key as environment variable or in .env file.

## Project Structure

- `python/agent/` - Tool-calling agent with CLI and web UI and a benchmark implementation
- `python/mcp_airline/` - MCP server for airline domain (flights, reservations, user management), which also implements a web server to edit user profile data
- `data/` - Domain data (airline database, policies, tasks)

## Quick Start

1. Setup Environment: Create a `.env` or environment variable with your API key.
2. Start the MCP Airline Servers: The MCP servers are all implemented using the streaming http protocol, so when launched they are reachable over a URL in the format `http://localhost:[port]/mcp`. You can start multiple servers on different ports.
3. The MCP Inspector can be used to check that the server is running correctly. Run `npx @modelcontextprotocol/inspector http://localhost:3000/mcp`
4. Start the agent with the CLI or Web UI, passing the address of the MCP server as an argument.
5. Optionally, run the provided examples and evaluates success from the tau2 benchmark. For this, the user input is simulated with another LLM.

## Hardened Python flow

The Python implementation now uses a trusted preview-and-commit flow for sensitive actions:
- compensation is issued only through a policy-checking server tool and is deduplicated per reservation
- cancellation requests are checked against policy in the MCP server before a mutation can occur
- payment-bearing baggage changes, flight changes, and new bookings create a pending action first; the user must then reply exactly `yes` to execute it or `no` to cancel it
- CLI responses include a `=== VERIFIED ACTIONS ===` section so users can distinguish trusted executed actions from normal model text

If you are testing the hardened Python version manually, use a fresh MCP server process between independent scenarios because reservation state, pending actions, and receipts are in-memory only. The compensation dedup ledger is persisted across server restarts and cleared by the explicit `reset` flow.


## Development Notes

- All MCP servers share data from the `data/` directory
- The airline database is loaded from `data/airline/db.json`
- The policy is in `data/airline/policy.md`
- Changes to the database through the web UI or MCP tools are in-memory only, except for the hardened compensation dedup ledger
