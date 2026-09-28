# OpenClaw MCP Bridge

一个简单的 MCP Server，让外部 MCP 客户端（Codex、Claude Code 等）能够与 OpenClaw Agent Session 交互。

## 架构

```
MCP Client (Codex/Claude Code/etc.)
    ↓ MCP (stdio)
OpenClaw MCP Bridge (server.py)
    ↓ HTTP
OpenClaw Gateway (Docker:18789)
    ↓
OpenClaw Agent Sessions
```

## 工具列表

| Tool | 说明 |
|------|------|
| `list_sessions` | 列出所有 OpenClaw Agent Session |
| `read_messages` | 读取 Session 历史消息（从 transcript 文件） |
| `send_message` | 向指定 Session 发消息并获取 Agent 回复 |
| `chat` | 一次性对话，自动创建新 Session |
| `list_agents` | 列出所有配置的 Agent |
| `health_check` | 检查 Gateway 连通性 |

## 快速开始

```bash
cd /root/openclaw-mcp-bridge
.venv/bin/python server.py
```

## 在 MCP 客户端中配置

### Codex / Claude Code

在 MCP 配置文件中添加：

```json
{
  "mcpServers": {
    "openclaw-bridge": {
      "command": "/root/openclaw-mcp-bridge/.venv/bin/python",
      "args": ["/root/openclaw-mcp-bridge/server.py"],
      "env": {
        "OPENCLAW_GATEWAY_URL": "http://localhost:18789",
        "OPENCLAW_GATEWAY_TOKEN": "your-gateway-token"
      }
    }
  }
}
```

### Qwen Code

在 `.qwen/settings.json` 的 `mcp.servers` 中添加：

```json
{
  "openclaw-bridge": {
    "command": "/root/openclaw-mcp-bridge/.venv/bin/python",
    "args": ["/root/openclaw-mcp-bridge/server.py"]
  }
}
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENCLAW_GATEWAY_URL` | `http://localhost:18789` | Gateway 地址 |
| `OPENCLAW_GATEWAY_TOKEN` | (内置) | Gateway 认证 Token |
| `OPENCLAW_TRANSCRIPTS_DIR` | `/opt/openclaw/config/agents` | Transcript 文件目录 |
| `OPENCLAW_TIMEOUT` | `120` | HTTP 请求超时（秒） |

## 前置条件

1. OpenClaw Gateway 运行中（Docker 容器）
2. Gateway 已启用 `/v1/chat/completions` 端点：
   ```json
   {
     "gateway": {
       "http": {
         "endpoints": {
           "chatCompletions": { "enabled": true }
         }
       }
     }
   }
   ```
3. Transcript 文件可访问（Docker 挂载到宿主机）
