#!/bin/bash
set -e

INSTALL_DIR="${1:-$HOME/.openclaw-mcp-bridge}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WHL="$SCRIPT_DIR/dist/openclaw_mcp_bridge-0.1.0-py3-none-any.whl"

if [ ! -f "$WHL" ]; then
    echo "Error: wheel not found at $WHL"
    exit 1
fi

echo "Installing OpenClaw MCP Bridge to: $INSTALL_DIR"

python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install --quiet "$WHL"

echo ""
echo "Done! Add this to your Qwen Code settings.json:"
echo ""
echo '  "mcpServers": {'
echo '    "openclaw-bridge": {'
echo "      \"command\": \"$INSTALL_DIR/.venv/bin/openclaw-mcp-bridge\","
echo '      "env": {'
echo '        "OPENCLAW_GATEWAY_URL": "http://<your-gateway-host>:18789",'
echo '        "OPENCLAW_GATEWAY_TOKEN": "<your-token>"'
echo '      }'
echo '    }'
echo '  }'
echo ""
echo "Uninstall: rm -rf $INSTALL_DIR"
