"""Model Context Protocol (MCP) client + registry.

Connects to external MCP servers (stdio subprocess or HTTP endpoint) and
exposes their tools as regular Python callables that the rest of the system
(agents, tool mappings) can use.

MCP is an optional capability. The official Python SDK is `mcp` — install
with `pip install mcp`. If the SDK is missing, `MCPRegistry.load_tools()`
returns an empty list and the system keeps working without MCP.

Transports supported:
- `stdio` — spawn a command, talk to it over stdin/stdout. Use for local
  tool servers (`uvx mcp-server-filesystem`, `npx @modelcontextprotocol/...`).
- `http` — connect to a streamable HTTP endpoint. Use for hosted MCP servers.

Configuration is read from the `MCP_SERVERS` env var as a JSON document:
  MCP_SERVERS='[{"name":"fs","transport":"stdio","command":["uvx","mcp-server-filesystem","/data"]}]'
"""

import asyncio
import json
import os
import threading
from dataclasses import dataclass, field
from typing import Any, Callable

from src.core.config import logger


@dataclass
class MCPServerConfig:
    name: str
    transport: str  # "stdio" | "http"
    command: list[str] | None = None
    url: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class MCPToolDef:
    name: str
    description: str
    input_schema: dict
    server_name: str
    call: Callable[..., str]


class MCPUnavailableError(RuntimeError):
    pass


def _try_import_mcp() -> tuple[Any, Any] | None:
    """Lazy-import the MCP SDK. Returns (ClientSession, stdio_client) or
    None if the SDK is not installed."""
    try:
        from mcp import ClientSession  # type: ignore
        from mcp.client.stdio import stdio_client  # type: ignore
        return ClientSession, stdio_client
    except ImportError:
        return None


class MCPClient:
    """One client = one MCP server connection. Wraps the transport, exposes
    `list_tools()` and `call_tool(name, args)`.

    Each client owns a dedicated background event loop. We can't use
    `asyncio.run()` per call because MCP transports need a long-lived loop
    to keep the subprocess / HTTP stream open across many tool invocations.
    """

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = False

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is not None and self._ready:
            return self._loop
        ready_evt = threading.Event()
        loop_holder: dict[str, Any] = {}

        def _runner() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop_holder["loop"] = loop
            ready_evt.set()
            try:
                loop.run_forever()
            finally:
                loop.close()

        self._thread = threading.Thread(
            target=_runner, name=f"mcp-{self.config.name}", daemon=True
        )
        self._thread.start()
        ready_evt.wait(timeout=5)
        self._loop = loop_holder.get("loop")
        if self._loop is None:
            raise MCPUnavailableError(
                f"Failed to start event loop for MCP server '{self.config.name}'"
            )
        self._ready = True
        return self._loop

    def _run_async(self, coro: Any) -> Any:
        loop = self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=120)

    def _transport_factory(self) -> Any:
        """Return an async context manager for the configured transport."""
        if self.config.transport == "stdio":
            from mcp import StdioServerParameters  # type: ignore
            from mcp.client.stdio import stdio_client  # type: ignore
            params = StdioServerParameters(
                command=self.config.command[0],
                args=self.config.command[1:],
                env={**os.environ, **(self.config.env or {})},
            )
            return stdio_client(params)

        if self.config.transport in ("http", "streamable_http"):
            try:
                from mcp.client.streamable_http import streamablehttp_client  # type: ignore
                return streamablehttp_client(self.config.url, headers=self.config.headers)
            except ImportError:
                pass
            from mcp.client.sse import sse_client  # type: ignore
            return sse_client(self.config.url, headers=self.config.headers)

        raise MCPUnavailableError(
            f"Unsupported MCP transport '{self.config.transport}'"
        )

    async def _list_tools_async(self) -> list[Any]:
        mcp = _try_import_mcp()
        if mcp is None:
            raise MCPUnavailableError("MCP SDK not installed. Run: `pip install mcp`")
        ClientSession, _ = mcp
        async with self._transport_factory() as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return result.tools

    async def _call_tool_async(self, name: str, arguments: dict) -> str:
        mcp = _try_import_mcp()
        if mcp is None:
            raise MCPUnavailableError("MCP SDK not installed.")
        ClientSession, _ = mcp
        async with self._transport_factory() as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments)
                parts: list[str] = []
                for block in (getattr(result, "content", None) or []):
                    text = getattr(block, "text", None)
                    if text:
                        parts.append(text)
                if parts:
                    return "\n".join(parts)
                return json.dumps(getattr(result, "content", None), default=str)

    def list_tools(self) -> list[MCPToolDef]:
        try:
            raw_tools = self._run_async(self._list_tools_async())
        except Exception as e:
            logger.warning(f"MCP list_tools for '{self.config.name}' failed: {e}")
            return []

        def _make_call(name: str) -> Callable[..., str]:
            def _call(**kwargs: Any) -> str:
                try:
                    return self._run_async(self._call_tool_async(name, kwargs))
                except Exception as e:
                    return f"Error calling MCP tool '{name}': {e}"
            return _call

        out: list[MCPToolDef] = []
        for t in raw_tools:
            schema = getattr(t, "inputSchema", None) or {
                "type": "object", "properties": {}
            }
            out.append(MCPToolDef(
                name=t.name,
                description=getattr(t, "description", "") or f"MCP tool {t.name}",
                input_schema=schema if isinstance(schema, dict) else {},
                server_name=self.config.name,
                call=_make_call(t.name),
            ))
        return out


class MCPRegistry:
    """Loads MCP server configs from `MCP_SERVERS` env var, builds clients,
    and exposes a single merged list of `MCPToolDef`s usable as CrewAI tools.

    Config format (JSON array):
    [
      {
        "name": "filesystem",
        "transport": "stdio",
        "command": ["uvx", "mcp-server-filesystem", "/data"]
      },
      {
        "name": "remote",
        "transport": "http",
        "url": "https://example.com/mcp",
        "headers": {"Authorization": "Bearer ..."}
      }
    ]
    """

    @staticmethod
    def load_from_env() -> list[MCPServerConfig]:
        raw = os.getenv("MCP_SERVERS", "").strip()
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning(f"MCP_SERVERS env var is not valid JSON: {e}")
            return []
        if not isinstance(data, list):
            logger.warning("MCP_SERVERS must be a JSON array.")
            return []
        configs: list[MCPServerConfig] = []
        for item in data:
            try:
                configs.append(MCPServerConfig(
                    name=item["name"],
                    transport=item.get("transport", "stdio"),
                    command=item.get("command"),
                    url=item.get("url"),
                    env=item.get("env", {}),
                    headers=item.get("headers", {}),
                ))
            except KeyError as e:
                logger.warning(f"MCP server config missing required key {e}: {item}")
        return configs

    @staticmethod
    def load_tools(configs: list[MCPServerConfig] | None = None) -> list[MCPToolDef]:
        """Resolve every server's tool list. Returns [] if MCP SDK is missing
        or no servers are configured. Safe to call at import time."""
        if _try_import_mcp() is None:
            logger.info("MCP SDK not installed — MCP tools disabled.")
            return []
        configs = configs if configs is not None else MCPRegistry.load_from_env()
        all_tools: list[MCPToolDef] = []
        for cfg in configs:
            try:
                client = MCPClient(cfg)
                tools = client.list_tools()
                logger.info(f"MCP server '{cfg.name}' exposed {len(tools)} tools.")
                all_tools.extend(tools)
            except Exception as e:
                logger.warning(f"Failed to load MCP server '{cfg.name}': {e}")
        return all_tools

    @staticmethod
    def to_crewai_tools(mcp_tools: list[MCPToolDef]) -> list:
        """Wrap each `MCPToolDef` as a CrewAI `BaseTool` so it can be dropped
        straight into `Agent(tools=[...])`. Uses dynamic Pydantic models so the
        LLM sees a proper tool schema for every MCP-exposed tool."""
        from crewai.tools import BaseTool  # type: ignore
        from pydantic import Field, create_model

        out = []
        for mt in mcp_tools:
            properties = (mt.input_schema or {}).get("properties", {})
            required = set((mt.input_schema or {}).get("required", []))
            fields: dict[str, Any] = {}
            for prop_name, spec in properties.items():
                py_type = _json_type_to_python(spec.get("type", "string"))
                default = ... if prop_name in required else None
                fields[prop_name] = (
                    py_type, Field(default, description=spec.get("description", ""))
                )
            model = create_model(f"{mt.name}_input", **fields) if fields else (
                create_model(f"{mt.name}_input")
            )

            class _MCPToolWrapper(BaseTool):
                name: str = mt.name
                description: str = (
                    f"{mt.description}  (MCP server: {mt.server_name})"
                )
                args_schema: type = model

                def _run(self, **kwargs: Any) -> str:
                    return mt.call(**kwargs)

            out.append(_MCPToolWrapper())
        return out


def _json_type_to_python(json_type: str) -> type:
    return {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }.get(json_type, str)
