# MCP Demo Guide (NSU Degree Audit)

Use this guide when presenting your MCP integration.

## 1) Start the MCP server

From project root:

```powershell
cd mcp_server
npm install
node server.js
```

Expected startup log:

```text
NSU Degree Audit MCP Server running
```

## 2) Copilot MCP configuration (VS Code)

Workspace setting is already configured in:

- .vscode/settings.json

Configured server:

```json
{
  "mcp.servers": {
    "nsu-degree-audit": {
      "command": "node",
      "args": [
        "D:/Future projects/CSE226 VIBE CODING/Project 3 (CLI, Flutter App, WebApp)/mcp_server/server.js"
      ]
    }
  }
}
```

After this, reload VS Code window.

## 3) Start website (for visual MCP showcase)

```powershell
cd web_app
python -m uvicorn app:app --host 127.0.0.1 --port 5055
```

Open:

- http://127.0.0.1:5055

Look for:

- Header button: MCP Server
- Floating key button: MCP
- Section title: Model Context Protocol Server

## 4) Live prompts to demonstrate

Use these in Copilot Chat:

1. Scan my transcript at D:/Transcripts/my_transcript.pdf
2. Calculate my CGPA with CSE115 A, CSE173 B+, MAT120 A-
3. Check my graduation requirements for CSE
4. Show my scan history

## 4.1) One-command terminal proof test

From mcp_server folder:

```powershell
node demo_live_test.js
```

This runs a real MCP client against your local MCP server and prints:

- total tools count
- tool names
- CGPA test output
- real transcript scan summary

## 5) What to explain in presentation

- MCP is the bridge that lets AI assistants call your backend tools.
- Your server exposes domain tools (scan, cgpa, graduation, history, export, prediction).
- The website now includes a dedicated MCP showcase so audience can see capabilities clearly.
- The key icon gives one-click access to the MCP explanation section during demo.

## 6) Verified test outputs (already tested)

MCP tool discovery output included:

- scan_transcript
- get_health_status
- login
- get_scan_history
- get_last_scan
- calculate_cgpa
- check_graduation
- export_scan
- predict_gpa
- get_ocr_engines

Example CGPA test output:

```text
Total Credits: 9
Total Quality Points: 33.00
CGPA: 3.67
```
