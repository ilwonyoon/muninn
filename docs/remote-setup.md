# Remote Access Setup — Claude iPhone/Web, ChatGPT

Muninn supports remote MCP access via Streamable HTTP transport. This guide covers setting up remote access for Claude Web/Mobile and ChatGPT.

## Prerequisites

- Muninn installed: `pip install muninn-mcp[http]` (or from source with `pip install -e ".[http]"`)
- Python 3.11+
- ngrok account (free tier works): https://ngrok.com

## Step 1: Start Muninn HTTP Server

```bash
# Set API key for authentication (required for remote access)
export MUNINN_API_KEY="your-secret-key-here"

# Start the server
muninn --transport http --host 0.0.0.0 --port 8000
```

Verify it works locally:
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Authorization: Bearer your-secret-key-here" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

## Step 2: Expose via ngrok

```bash
# Install ngrok (macOS)
brew install ngrok

# Authenticate (one-time)
ngrok config add-authtoken YOUR_NGROK_TOKEN

# Start tunnel
ngrok http 8000
```

ngrok will show a public URL like `https://abc123.ngrok-free.app`. This is your MCP endpoint.

Your MCP URL: `https://abc123.ngrok-free.app/mcp`

## Step 3: Connect to Claude Web/Mobile

1. Go to **claude.ai** -> Settings -> Integrations (or MCP Servers)
2. Add a new Remote MCP Server
3. Enter:
   - **URL**: `https://abc123.ngrok-free.app/mcp`
   - **Authentication**: Bearer Token -> `your-secret-key-here`
4. Save and test by asking Claude: "내 프로젝트 뭐 있어?"

### Claude iPhone App
Same setup — Claude iOS uses the same Remote MCP configuration as Claude Web.

## Step 4: Connect to ChatGPT (Web)

1. ChatGPT -> Settings -> MCP Servers (if available)
2. Add your ngrok URL with Bearer token authentication
3. Note: ChatGPT MCP support is still rolling out — check availability

## Alternative: Cloudflare Tunnel (Permanent)

For always-on access without keeping ngrok running:

```bash
# Install cloudflared
brew install cloudflared

# Create tunnel (one-time)
cloudflared tunnel create muninn
cloudflared tunnel route dns muninn muninn.yourdomain.com

# Run tunnel
cloudflared tunnel run --url http://localhost:8000 muninn
```

Then use `https://muninn.yourdomain.com/mcp` as your MCP URL.

## Security Notes

- **Always set MUNINN_API_KEY** for remote access — without it, anyone with the URL can read/write your memories
- Use a strong, random key: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
- ngrok free tier URLs change on restart — consider ngrok paid or Cloudflare Tunnel for stable URLs
- Your memory database stays local — only the API is exposed

## Troubleshooting

| Issue | Solution |
|-------|---------|
| 401 Unauthorized | Check Bearer token matches MUNINN_API_KEY |
| Connection refused | Ensure muninn server is running on port 8000 |
| ngrok URL changed | Restart ngrok, update MCP server URL in Claude/ChatGPT |
| 500 Internal Server Error | Check muninn server logs for details |

## Platform Support

| Platform | Transport | Status |
|----------|-----------|--------|
| Claude Desktop (Mac) | stdio | Working |
| Claude Code | stdio | Working |
| Cursor | stdio | Working |
| Claude Web/Mobile | HTTP + ngrok | Ready |
| ChatGPT Web | HTTP + ngrok | MCP support rolling out |
| ChatGPT Mac App | — | No MCP support |
