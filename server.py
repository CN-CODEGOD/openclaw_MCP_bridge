"""
OpenClaw MCP Bridge

A simple MCP server that connects to OpenClaw Gateway,
enabling external MCP clients (Codex, Claude Code, etc.)
to interact with OpenClaw agent sessions.

Architecture:
    MCP Client (Codex/etc.)
        ↓ MCP (stdio)
    This Bridge (server.py)
        ↓ HTTP
    OpenClaw Gateway (Docker)
        ↓
    OpenClaw Agent Sessions
"""

import os
import json
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP

GATEWAY_URL = os.environ.get("OPENCLAW_GATEWAY_URL", "http://localhost:18789")
GATEWAY_TOKEN = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")
TRANSCRIPTS_DIR = os.environ.get("OPENCLAW_TRANSCRIPTS_DIR", "/opt/openclaw/config/agents")
REQUEST_TIMEOUT = float(os.environ.get("OPENCLAW_TIMEOUT", "120"))

mcp = FastMCP("openclaw-bridge")


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {GATEWAY_TOKEN}",
        "Content-Type": "application/json",
    }


def _find_transcript(session_key: str) -> str | None:
    agents_dir = Path(TRANSCRIPTS_DIR)
    for agent_dir in agents_dir.iterdir():
        sessions_file = agent_dir / "sessions" / "sessions.json"
        if not sessions_file.exists():
            continue
        try:
            with open(sessions_file) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            continue

        session_id = None
        if isinstance(data, dict) and session_key in data:
            entry = data[session_key]
            session_id = entry.get("sessionId") or entry.get("id")
        elif isinstance(data, list):
            for s in data:
                if s.get("key") == session_key:
                    session_id = s.get("sessionId") or s.get("id")
                    break
        elif isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, dict) and (v.get("sessionId") or v.get("id")):
                    if k == session_key:
                        session_id = v.get("sessionId") or v.get("id")
                        break

        if session_id:
            path = agent_dir / "sessions" / f"{session_id}.jsonl"
            if path.exists():
                return str(path)
    return None


def _parse_transcript(path: str, limit: int = 20) -> list[dict]:
    messages = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") != "message":
                    continue
                msg = entry.get("message", {})
                role = msg.get("role", "unknown")
                content = msg.get("content", "")

                if isinstance(content, list):
                    text_parts = []
                    tool_names = []
                    for p in content:
                        if not isinstance(p, dict):
                            continue
                        pt = p.get("type", "")
                        if pt == "text" and p.get("text", "").strip():
                            text_parts.append(p["text"])
                        elif pt == "toolCall" or pt == "tool_use":
                            tool_names.append(p.get("name", "unknown"))
                    text = "\n".join(text_parts)
                    if tool_names and not text.strip():
                        text = f"[tool calls: {', '.join(tool_names)}]"
                    elif tool_names:
                        text += f"\n[tools: {', '.join(tool_names)}]"
                else:
                    text = str(content)

                if text.strip():
                    messages.append({
                        "role": role,
                        "content": text[:2000],
                        "timestamp": entry.get("timestamp", ""),
                    })
    except IOError:
        return []
    return messages[-limit:]


@mcp.tool(description="List all OpenClaw agent sessions with their keys, status, model, and activity.")
async def list_sessions(limit: int = 20) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{GATEWAY_URL}/tools/invoke",
            headers=_headers(),
            json={"tool": "sessions_list", "args": {}},
        )
        resp.raise_for_status()
        data = resp.json()

    if not data.get("ok"):
        return json.dumps({"error": data.get("error", {}).get("message", "unknown")})

    sessions = data.get("result", {}).get("details", {}).get("sessions", [])[:limit]
    return json.dumps({
        "count": len(sessions),
        "sessions": [
            {
                "key": s["key"],
                "agentId": s.get("agentId"),
                "status": s.get("status"),
                "model": s.get("model"),
                "channel": s.get("channel"),
                "totalTokens": s.get("totalTokens"),
                "updatedAt": s.get("updatedAt"),
            }
            for s in sessions
        ],
    }, indent=2, ensure_ascii=False)


@mcp.tool(description="Read recent messages from an OpenClaw agent session transcript.")
async def read_messages(session_key: str, limit: int = 20) -> str:
    path = _find_transcript(session_key)
    if not path:
        return json.dumps({"error": f"Transcript not found for session: {session_key}"})
    messages = _parse_transcript(path, limit)
    if not messages:
        return json.dumps({"error": f"No messages found in session: {session_key}"})
    return json.dumps({
        "session_key": session_key,
        "message_count": len(messages),
        "messages": messages,
    }, indent=2, ensure_ascii=False)


@mcp.tool(description="Send a message to an OpenClaw agent session and get the response. Uses the Gateway /v1/chat/completions endpoint.")
async def send_message(session_key: str, message: str, agent_id: str = "main") -> str:
    headers = _headers()
    headers["x-openclaw-session-key"] = session_key
    payload = {
        "model": f"openclaw/{agent_id}",
        "messages": [{"role": "user", "content": message}],
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.post(
            f"{GATEWAY_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    choices = data.get("choices", [])
    if not choices:
        return json.dumps({"error": "No response from agent"})
    reply = choices[0].get("message", {}).get("content", "")
    usage = data.get("usage", {})
    return json.dumps({
        "session_key": session_key,
        "agent": agent_id,
        "reply": reply,
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
        },
    }, indent=2, ensure_ascii=False)


@mcp.tool(description="Send a one-shot message to an OpenClaw agent. Creates a new ephemeral session.")
async def chat(message: str, agent_id: str = "main") -> str:
    payload = {
        "model": f"openclaw/{agent_id}",
        "messages": [{"role": "user", "content": message}],
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.post(
            f"{GATEWAY_URL}/v1/chat/completions",
            headers=_headers(),
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    choices = data.get("choices", [])
    if not choices:
        return json.dumps({"error": "No response from agent"})
    reply = choices[0].get("message", {}).get("content", "")
    return json.dumps({"agent": agent_id, "reply": reply}, indent=2, ensure_ascii=False)


@mcp.tool(description="List all configured OpenClaw agents with their names, models, and workspaces.")
async def list_agents() -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{GATEWAY_URL}/v1/models", headers=_headers())
        if resp.status_code != 200:
            config_path = Path("/opt/openclaw/config/openclaw.json")
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
                agents = config.get("agents", {}).get("list", [])
                return json.dumps({
                    "agents": [
                        {"id": a.get("id"), "name": a.get("name"), "model": a.get("model"), "default": a.get("default", False)}
                        for a in agents
                    ],
                }, indent=2, ensure_ascii=False)
            return json.dumps({"error": "Could not retrieve agents list"})
        data = resp.json()

    models = data.get("data", [])
    agents = []
    for m in models:
        mid = m.get("id", "")
        if mid.startswith("openclaw/") and mid not in ("openclaw/default",):
            agent_id = mid.replace("openclaw/", "")
            agents.append({"id": agent_id, "model_target": mid})
        elif mid == "openclaw":
            agents.append({"id": "default", "model_target": mid, "default": True})
    return json.dumps({"agents": agents}, indent=2, ensure_ascii=False)


@mcp.tool(description="Check if the OpenClaw Gateway is reachable and responsive.")
async def health_check() -> str:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{GATEWAY_URL}/")
            return json.dumps({
                "healthy": resp.status_code == 200,
                "gateway_url": GATEWAY_URL,
                "status_code": resp.status_code,
            })
    except Exception as e:
        return json.dumps({"healthy": False, "gateway_url": GATEWAY_URL, "error": str(e)})


def main():
    mcp.run()


if __name__ == "__main__":
    main()
