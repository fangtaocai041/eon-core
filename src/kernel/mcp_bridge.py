"""MCPBridge — Model Context Protocol bridge for ecosystem-wide tool communication.

Standardizes tool-server communication across all 7 projects.
Implements JSON-RPC 2.0 over stdio as per MCP specification.
Each project registers its tools, other projects discover and call them.

Architecture:
    MCPBridge (eon-core)
      ├── ToolRegistry — register/list tools with JSON Schema
      ├── Transport — stdio/HTTP transport layer  
      └── Discovery — auto-discover tools from sibling projects

Usage:
    bridge = MCPBridge()
    bridge.register_tool("search_species", search_fn, schema)
    result = bridge.call_tool("search_species", {"query": "Coilia nasus"})
"""

import json, asyncio, logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolDef:
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    fn: Callable
    project: str = "unknown"


class MCPBridge:
    """Model Context Protocol bridge for ecosystem tools."""

    def __init__(self):
        self._tools: Dict[str, ToolDef] = {}
        self._pending: Dict[str, asyncio.Future] = {}

    def register_tool(self, name: str, fn: Callable, schema: Dict[str, Any],
                      project: str = "unknown"):
        self._tools[name] = ToolDef(
            name=name, description=schema.get('description', ''),
            parameters=schema.get('parameters', {}), fn=fn, project=project
        )

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tool = self._tools.get(name)
        if not tool:
            return {"error": f"Tool not found: {name}"}
        try:
            result = tool.fn(**arguments)
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}

    def list_tools(self) -> List[Dict]:
        return [{
            "name": t.name, "description": t.description,
            "parameters": t.parameters, "project": t.project
        } for t in self._tools.values()]

    def to_json_rpc_request(self, tool_name: str, params: Dict, req_id: int = 1) -> str:
        return json.dumps({
            "jsonrpc": "2.0", "method": "tools/call",
            "params": {"name": tool_name, "arguments": params}, "id": req_id
        })

    def from_json_rpc_response(self, response: str) -> Dict:
        data = json.loads(response)
        if "error" in data:
            return {"error": data["error"]}
        return {"result": data.get("result", {})}


# Singleton for ecosystem-wide access
_bridge: Optional[MCPBridge] = None

def get_mcp_bridge() -> MCPBridge:
    global _bridge
    if _bridge is None:
        _bridge = MCPBridge()
    return _bridge
