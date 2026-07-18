"""Model Context Protocol (MCP) support.

Lets the system call tools exposed by external MCP servers (stdio subprocess
or HTTP endpoint) and use them as regular CrewAI tools, alongside our own.

Configuration: set `MCP_SERVERS` to a JSON array describing each server. See
`MCPRegistry.load_from_env` for the schema.

The `mcp` Python SDK is an optional dependency. If it is not installed,
`MCPRegistry.load_tools()` returns an empty list and the system runs as
before — no error.
"""

from .client import (
    MCPClient,
    MCPRegistry,
    MCPServerConfig,
    MCPToolDef,
    MCPUnavailableError,
)

__all__ = [
    "MCPClient",
    "MCPRegistry",
    "MCPServerConfig",
    "MCPToolDef",
    "MCPUnavailableError",
]
