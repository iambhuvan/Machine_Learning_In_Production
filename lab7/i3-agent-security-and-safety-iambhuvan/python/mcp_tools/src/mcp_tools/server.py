"""Factory for the utility MCP tools server."""

from fastmcp import FastMCP
from .tools import register_tools


def create_mcp_server() -> FastMCP:
    """Create and configure the FastMCP server with utility tools.

    Returns:
        A ready-to-run FastMCP object with all tools registered.
    """

    mcp = FastMCP("utility-tools-server")
    register_tools(mcp)
    return mcp
