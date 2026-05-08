"""Entry point for the utility MCP tools server.

Supports two runtime modes:
* **stdio transport** (default) – for MCP clients and the inspector.
* **HTTP transport** – enabled when a ``PORT`` environment variable is set.
"""

import os
import sys
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from .server import create_mcp_server


def main() -> None:
    """Run the MCP tools server."""

    mcp = create_mcp_server()

    port = os.environ.get("PORT")
    host = os.environ.get("HOST", "127.0.0.1")

    if port:
        middleware = [
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                allow_headers=["*"],
                expose_headers=["mcp-session-id", "mcp-protocol-version"],
                max_age=86400,
            )
        ]

        port_num = int(port)
        print(f"MCP Tools Server running on http://{host}:{port_num}/mcp", file=sys.stderr)
        mcp.run(transport="http", host=host, port=port_num, middleware=middleware)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
