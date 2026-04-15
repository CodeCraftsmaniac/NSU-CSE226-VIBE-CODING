#!/usr/bin/env node

const path = require("path");
const { Client } = require("@modelcontextprotocol/sdk/client/index.js");
const { StdioClientTransport } = require("@modelcontextprotocol/sdk/client/stdio.js");

const transcriptArg = process.argv[2];
const defaultTranscript = path.resolve(__dirname, "..", "samples", "transcript.csv");
const transcriptPath = transcriptArg ? path.resolve(transcriptArg) : defaultTranscript;

async function runDemo() {
  const client = new Client({ name: "mcp-demo-live-test", version: "1.0.0" });
  const transport = new StdioClientTransport({
    command: "node",
    args: ["server.js"],
    cwd: __dirname,
    stderr: "pipe",
  });

  if (transport.stderr) {
    transport.stderr.on("data", (chunk) => {
      process.stderr.write(`[server] ${chunk.toString()}`);
    });
  }

  await client.connect(transport);

  try {
    const tools = await client.listTools();
    console.log("TOOLS_COUNT:", tools.tools.length);
    console.log("TOOLS:", tools.tools.map((tool) => tool.name).join(", "));

    const cgpaResult = await client.callTool({
      name: "calculate_cgpa",
      arguments: {
        courses: [
          { code: "CSE115", credits: 3, grade: "A" },
          { code: "CSE173", credits: 3, grade: "B+" },
          { code: "MAT120", credits: 3, grade: "A-" },
        ],
      },
    });

    const cgpaText = cgpaResult.content?.[0]?.text || "";
    const cgpaLine =
      cgpaText
        .split("\n")
        .find((line) => line.trim().startsWith("CGPA:")) || "CGPA line not found";
    console.log("CGPA_TEST:", cgpaLine.trim());

    console.log("SCAN_FILE:", transcriptPath);
    const scanResult = await client.callTool({
      name: "scan_transcript",
      arguments: {
        file_path: transcriptPath,
        ocr_engine: "auto",
      },
    });

    console.log("SCAN_IS_ERROR:", !!scanResult.isError);

    const scanText = scanResult.content?.[0]?.text || "";
    const summaryLines = scanText
      .split("\n")
      .map((line) => line.trim())
      .filter((line) =>
        /^(Total Courses:|Credits Earned:|CGPA:|Program:|Graduation Ready:)/.test(line)
      );

    console.log("SCAN_SUMMARY:");
    if (summaryLines.length === 0) {
      console.log("No summary lines found.");
    } else {
      summaryLines.forEach((line) => console.log(line));
    }
  } finally {
    await client.close();
  }
}

runDemo().catch((error) => {
  console.error("DEMO_TEST_FAILED:", error && error.stack ? error.stack : error);
  process.exit(1);
});
