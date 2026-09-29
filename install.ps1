param(
    [string]$InstallDir = "$HOME\.openclaw-mcp-bridge"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WHL = Join-Path $ScriptDir "dist\openclaw_mcp_bridge-0.1.0-py3-none-any.whl"

if (-not (Test-Path $WHL)) {
    Write-Error "Wheel not found: $WHL"
    exit 1
}

Write-Host "Installing OpenClaw MCP Bridge to: $InstallDir" -ForegroundColor Cyan

# Find python
$python = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $found = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($found) { $python = $found.Source; break }
    } catch {}
}
if (-not $python) {
    Write-Error "Python not found. Install Python 3.10+ first."
    exit 1
}

Write-Host "Using Python: $python"

# Create venv
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}
& $python -m venv "$InstallDir\.venv"

# Install wheel
$venvPip = Join-Path $InstallDir ".venv\Scripts\pip"
& $venvPip install --quiet $WHL
if ($LASTEXITCODE -ne 0) {
    Write-Error "pip install failed"
    exit 1
}

# Resolve the command path
$bridgeCmd = Join-Path $InstallDir ".venv\Scripts\openclaw-mcp-bridge.exe"
$bridgeCmdUnix = $bridgeCmd -replace '\\', '/'

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
Write-Host ""
Write-Host "Add this to your Qwen Code settings.json:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  `"mcpServers`": {"
Write-Host "    `"openclaw-bridge`": {"
Write-Host "      `"command`": `"$bridgeCmdUnix`","
Write-Host "      `"env`": {"
Write-Host "        `"OPENCLAW_GATEWAY_URL`": `"http://<your-gateway-host>:18789`","
Write-Host "        `"OPENCLAW_GATEWAY_TOKEN`": `"<your-token>`""
Write-Host "      }"
Write-Host "    }"
Write-Host "  }"
Write-Host ""
Write-Host "Note: 'read_messages' requires access to OpenClaw transcript files." -ForegroundColor DarkYellow
Write-Host "      On Windows this tool is unavailable unless you mount the server's" -ForegroundColor DarkYellow
Write-Host "      transcript directory and set OPENCLAW_TRANSCRIPTS_DIR env var." -ForegroundColor DarkYellow
Write-Host "      Other tools (chat, send_message, list_sessions, etc.) work fine." -ForegroundColor DarkYellow
Write-Host ""
Write-Host "Uninstall: Remove-Item -Recurse '$InstallDir'"
