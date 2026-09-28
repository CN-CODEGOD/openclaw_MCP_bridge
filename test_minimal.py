from mcp.server.fastmcp import FastMCP

mcp = FastMCP("test-minimal")

@mcp.tool()
def ping() -> str:
    """A simple ping test."""
    return "pong"

if __name__ == "__main__":
    mcp.run()
