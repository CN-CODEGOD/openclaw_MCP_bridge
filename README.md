# OpenClaw MCP Bridge

一个简单的 MCP Server，让外部 MCP 客户端（Codex、Claude Code、Qwen Code 等）能够与 OpenClaw Agent Session 交互。

## 架构

```
MCP Client (Codex/Claude Code/Qwen Code)
    ↓ MCP (stdio)
OpenClaw MCP Bridge
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

## 安装

### Linux / macOS

```bash
tar xzf openclaw-mcp-bridge-0.1.0.tar.gz
bash install.sh
```

默认安装到 `~/.openclaw-mcp-bridge/`，也可指定路径：

```bash
bash install.sh /custom/path
```

### Windows (PowerShell)

```powershell
tar xzf openclaw-mcp-bridge-0.1.0.tar.gz
pwsh .\install.ps1
```

默认安装到 `%USERPROFILE%\.openclaw-mcp-bridge\`，也可指定路径：

```powershell
pwsh .\install.ps1 -InstallDir "D:\tools\openclaw-bridge"
```

> 需要 Python 3.10+ 已安装（`python`、`python3` 或 `py` 任一命令可用）。

### 手动安装

```bash
python3 -m venv .venv
.venv/bin/pip install dist/openclaw_mcp_bridge-0.1.0-py3-none-any.whl
```

## 配置 MCP 客户端

安装脚本会输出配置模板，复制到你用的 MCP 客户端的 settings 中即可。

### Qwen Code

在 `~/.qwen/settings.json` 的 `mcpServers` 中添加：

**Linux:**
```json
{
  "openclaw-bridge": {
    "command": "/home/user/.openclaw-mcp-bridge/.venv/bin/openclaw-mcp-bridge",
    "env": {
      "OPENCLAW_GATEWAY_URL": "http://<gateway-host>:18789",
      "OPENCLAW_GATEWAY_TOKEN": "<your-token>"
    }
  }
}
```

**Windows:**
```json
{
  "openclaw-bridge": {
    "command": "C:/Users/user/.openclaw-mcp-bridge/.venv/Scripts/openclaw-mcp-bridge.exe",
    "env": {
      "OPENCLAW_GATEWAY_URL": "http://<gateway-host>:18789",
      "OPENCLAW_GATEWAY_TOKEN": "<your-token>"
    }
  }
}
```

### Codex / Claude Code

MCP 配置文件中添加：

```json
{
  "mcpServers": {
    "openclaw-bridge": {
      "command": "openclaw-mcp-bridge",
      "env": {
        "OPENCLAW_GATEWAY_URL": "http://<gateway-host>:18789",
        "OPENCLAW_GATEWAY_TOKEN": "<your-token>"
      }
    }
  }
}
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENCLAW_GATEWAY_URL` | `http://localhost:18789` | Gateway 地址 |
| `OPENCLAW_GATEWAY_TOKEN` | (无，必填) | Gateway 认证 Token |
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
   > 远程客户端（如 Windows）如果无法直接访问 transcript 目录，`read_messages` 工具将不可用，其余工具正常工作。

## 卸载

**Linux:** `rm -rf ~/.openclaw-mcp-bridge`
**Windows:** `Remove-Item -Recurse "$HOME\.openclaw-mcp-bridge"`
