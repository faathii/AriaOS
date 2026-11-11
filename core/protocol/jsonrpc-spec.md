# AriaOS Connector Wire Protocol (JSON-RPC 2.0)

All connectors communicate with `aria-daemon` using newline-delimited **JSON-RPC 2.0** messages (compatible with MCP-style tool discovery and execution).

## Standard Methods

### 1. `aria/info`
Returns connector metadata and protocol version.

**Request:**
```json
{"jsonrpc": "2.0", "id": 1, "method": "aria/info", "params": {}}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "id": "os-files",
    "version": "0.1.0",
    "protocol": "aria-jsonrpc/1.0"
  }
}
```

### 2. `tools/list`
Lists the tool names registered by the connector.

**Request:**
```json
{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
```

### 3. `tools/call`
Executes a named tool with structured JSON arguments.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "scan_directory",
    "arguments": {"path": "/home/user/Downloads"}
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "ok": true,
    "data": {"total_files": 42}
  }
}
```

## Error Codes

- `-32700`: Parse error (invalid JSON)
- `-32600`: Invalid Request
- `-32601`: Method or tool not found
- `-32602`: Invalid parameters
- `-32000`: Tool execution failure

