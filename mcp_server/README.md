# NSU Degree Audit - MCP Server

Model Context Protocol (MCP) server that allows AI assistants like Claude and Copilot to interact with the NSU Degree Audit system.

## Features

The MCP server exposes these tools to AI assistants:

| Tool | Description |
|------|-------------|
| `scan_transcript` | Scan a PDF/image transcript and get full analysis |
| `get_health_status` | Check API status and capabilities |
| `login` | Login with email to enable history sync |
| `get_scan_history` | Get user's scan history |
| `get_last_scan` | Get the last scan result from this session |
| `calculate_cgpa` | Calculate CGPA from course list |
| `check_graduation` | Check graduation requirements |

## Installation

```bash
cd mcp_server
npm install
```

## Configuration

### For Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on Mac or `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "nsu-degree-audit": {
      "command": "node",
      "args": ["D:/Future projects/CSE226 VIBE CODING/Project 3 (CLI, Flutter App, WebApp)/mcp_server/server.js"]
    }
  }
}
```

### For VS Code Copilot

Add to your VS Code settings:

```json
{
  "mcp.servers": {
    "nsu-degree-audit": {
      "command": "node",
      "args": ["path/to/mcp_server/server.js"]
    }
  }
}
```

## Usage Examples

Once configured, you can ask your AI assistant:

- "Scan my transcript at D:/Transcripts/my_transcript.pdf"
- "Check my graduation requirements for CSE"
- "Calculate my CGPA with these courses: CSE115 (3 credits, A), CSE173 (3 credits, B+)"
- "Login with my email test@nsu.edu"
- "Show my scan history"

## Resources

The server also provides these resources:

- `nsu://last-scan` - Most recent scan result
- `nsu://grading-scale` - NSU grading scale
- `nsu://waiver-requirements` - Tuition waiver requirements

## API Endpoint

The MCP server connects to: `https://ocrapi.nsunexus.app`

You can override this with the `CLOUD_API_URL` environment variable.
