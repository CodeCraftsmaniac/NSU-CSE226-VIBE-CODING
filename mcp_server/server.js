#!/usr/bin/env node
/**
 * NSU Degree Audit - MCP Server
 * ==============================
 * Model Context Protocol server that allows AI assistants to:
 * - Scan transcripts (PDF, images, CSV)
 * - Get degree audit analysis
 * - View scan history
 * - Check graduation requirements
 * 
 * Usage with Claude Desktop / Copilot:
 *   Add to your MCP settings:
 *   {
 *     "mcpServers": {
 *       "nsu-degree-audit": {
 *         "command": "node",
 *         "args": ["path/to/mcp_server/server.js"]
 *       }
 *     }
 *   }
 */

const { Server } = require("@modelcontextprotocol/sdk/server/index.js");
const { StdioServerTransport } = require("@modelcontextprotocol/sdk/server/stdio.js");
const {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
} = require("@modelcontextprotocol/sdk/types.js");
const axios = require("axios");
const fs = require("fs");
const path = require("path");
const FormData = require("form-data");

// API Configuration
const API_BASE_URL = process.env.CLOUD_API_URL || "https://ocrapi.nsunexus.app";

// Store session state
let authToken = null;
let currentUser = null;
let lastScanResult = null;

/**
 * Create the MCP server
 */
const server = new Server(
  {
    name: "nsu-degree-audit",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
      resources: {},
    },
  }
);

/**
 * List available tools
 */
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "scan_transcript",
        description: "Scan a transcript PDF or image file and get full degree audit analysis. Returns course data, CGPA, credit tally, and graduation requirements.",
        inputSchema: {
          type: "object",
          properties: {
            file_path: {
              type: "string",
              description: "Full path to the transcript file (PDF, PNG, JPG, or CSV)",
            },
            ocr_engine: {
              type: "string",
              description: "OCR engine to use: 'auto' (default), 'google_vision', or 'azure'",
              enum: ["auto", "google_vision", "azure"],
            },
          },
          required: ["file_path"],
        },
      },
      {
        name: "get_health_status",
        description: "Check the NSU Degree Audit API health status and capabilities",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "login",
        description: "Login to NSU Degree Audit with email to enable scan history",
        inputSchema: {
          type: "object",
          properties: {
            email: {
              type: "string",
              description: "User email address",
            },
            name: {
              type: "string",
              description: "User name (optional)",
            },
          },
          required: ["email"],
        },
      },
      {
        name: "get_scan_history",
        description: "Get user's scan history (requires login)",
        inputSchema: {
          type: "object",
          properties: {
            limit: {
              type: "number",
              description: "Maximum number of scans to return (default: 10)",
            },
          },
        },
      },
      {
        name: "get_last_scan",
        description: "Get the last scan result from this session",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "calculate_cgpa",
        description: "Calculate CGPA from a list of courses with grades and credits",
        inputSchema: {
          type: "object",
          properties: {
            courses: {
              type: "array",
              description: "Array of courses with code, credits, and grade",
              items: {
                type: "object",
                properties: {
                  code: { type: "string" },
                  credits: { type: "number" },
                  grade: { type: "string" },
                },
              },
            },
          },
          required: ["courses"],
        },
      },
      {
        name: "check_graduation",
        description: "Check graduation requirements for a given program based on completed courses",
        inputSchema: {
          type: "object",
          properties: {
            program: {
              type: "string",
              description: "Program name (e.g., CSE, BBA, EEE)",
            },
            courses: {
              type: "array",
              description: "List of completed course codes",
              items: { type: "string" },
            },
          },
          required: ["program", "courses"],
        },
      },
      {
        name: "export_scan",
        description: "Export a scan result to JSON or CSV format",
        inputSchema: {
          type: "object",
          properties: {
            scan_id: {
              type: "string",
              description: "The scan ID to export (use 'last' for the most recent scan)",
            },
            format: {
              type: "string",
              description: "Export format: 'json' or 'csv'",
              enum: ["json", "csv"],
            },
          },
          required: ["scan_id"],
        },
      },
      {
        name: "predict_gpa",
        description: "Predict future GPA based on current performance and planned courses",
        inputSchema: {
          type: "object",
          properties: {
            current_cgpa: {
              type: "number",
              description: "Current CGPA",
            },
            current_credits: {
              type: "number",
              description: "Current total earned credits",
            },
            planned_courses: {
              type: "array",
              description: "Planned courses with expected grades",
              items: {
                type: "object",
                properties: {
                  credits: { type: "number" },
                  expected_grade: { type: "string" },
                },
              },
            },
          },
          required: ["current_cgpa", "current_credits", "planned_courses"],
        },
      },
      {
        name: "get_ocr_engines",
        description: "Get available OCR engines and their status",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
    ],
  };
});

/**
 * List available resources
 */
server.setRequestHandler(ListResourcesRequestSchema, async () => {
  return {
    resources: [
      {
        uri: "nsu://last-scan",
        name: "Last Scan Result",
        description: "The most recent transcript scan result",
        mimeType: "application/json",
      },
      {
        uri: "nsu://grading-scale",
        name: "NSU Grading Scale",
        description: "NSU grading scale and quality points",
        mimeType: "application/json",
      },
      {
        uri: "nsu://waiver-requirements",
        name: "Waiver Requirements",
        description: "Tuition waiver eligibility requirements",
        mimeType: "application/json",
      },
    ],
  };
});

/**
 * Read a resource
 */
server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  const uri = request.params.uri;

  if (uri === "nsu://last-scan") {
    return {
      contents: [
        {
          uri,
          mimeType: "application/json",
          text: JSON.stringify(lastScanResult || { message: "No scan performed yet" }, null, 2),
        },
      ],
    };
  }

  if (uri === "nsu://grading-scale") {
    return {
      contents: [
        {
          uri,
          mimeType: "application/json",
          text: JSON.stringify({
            "A": { points: 4.00, range: "90-100%" },
            "A-": { points: 3.70, range: "85-89%" },
            "B+": { points: 3.30, range: "80-84%" },
            "B": { points: 3.00, range: "75-79%" },
            "B-": { points: 2.70, range: "70-74%" },
            "C+": { points: 2.30, range: "65-69%" },
            "C": { points: 2.00, range: "60-64%" },
            "C-": { points: 1.70, range: "55-59%" },
            "D+": { points: 1.30, range: "50-54%" },
            "D": { points: 1.00, range: "45-49%" },
            "F": { points: 0.00, range: "0-44%" },
          }, null, 2),
        },
      ],
    };
  }

  if (uri === "nsu://waiver-requirements") {
    return {
      contents: [
        {
          uri,
          mimeType: "application/json",
          text: JSON.stringify({
            "Chancellor's Award": { cgpa: 3.97, waiver: "100%", minCredits: 30 },
            "VC's Scholarship": { cgpa: 3.75, waiver: "50%", minCredits: 30 },
            "Dean's Scholarship": { cgpa: 3.50, waiver: "25%", minCredits: 30 },
          }, null, 2),
        },
      ],
    };
  }

  throw new Error(`Unknown resource: ${uri}`);
});

/**
 * Handle tool calls
 */
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "get_health_status":
        return await handleHealthCheck();

      case "scan_transcript":
        return await handleScanTranscript(args.file_path, args.ocr_engine || "auto");

      case "login":
        return await handleLogin(args.email, args.name);

      case "get_scan_history":
        return await handleGetHistory(args.limit || 10);

      case "get_last_scan":
        return {
          content: [
            {
              type: "text",
              text: lastScanResult
                ? JSON.stringify(lastScanResult, null, 2)
                : "No scan performed in this session. Use scan_transcript to scan a file.",
            },
          ],
        };

      case "calculate_cgpa":
        return handleCalculateCGPA(args.courses);

      case "check_graduation":
        return handleCheckGraduation(args.program, args.courses);

      case "export_scan":
        return await handleExportScan(args.scan_id, args.format || "json");

      case "predict_gpa":
        return handlePredictGPA(args.current_cgpa, args.current_credits, args.planned_courses);

      case "get_ocr_engines":
        return await handleGetOCREngines();

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: `Error: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
});

/**
 * Health check handler
 */
async function handleHealthCheck() {
  try {
    const response = await axios.get(`${API_BASE_URL}/health`, { timeout: 10000 });
    const data = response.data;

    return {
      content: [
        {
          type: "text",
          text: `NSU Degree Audit API Status:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status: ${data.status}
Version: ${data.version}
Database: ${data.database?.connected ? "✓ Connected" : "✗ Disconnected"}
OCR Engines:
  - Google Vision: ${data.ocr_engines?.google_vision?.configured ? "✓" : "✗"} (${data.ocr_engines?.google_vision?.free_tier})
  - Azure Doc Intelligence: ${data.ocr_engines?.azure_doc_intelligence?.configured ? "✓" : "✗"} (${data.ocr_engines?.azure_doc_intelligence?.accuracy})

Analysis Capabilities:
  - Level 1: Credit Tally (earned/failed credits, retakes)
  - Level 2: CGPA Analysis (academic standing, waiver eligibility)
  - Level 3: Degree Audit (graduation requirements, missing courses)`,
        },
      ],
    };
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: `Failed to connect to API: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
}

/**
 * Scan transcript handler
 */
async function handleScanTranscript(filePath, ocrEngine = "auto") {
  // Resolve path
  const resolvedPath = path.resolve(filePath);

  if (!fs.existsSync(resolvedPath)) {
    return {
      content: [{ type: "text", text: `File not found: ${resolvedPath}` }],
      isError: true,
    };
  }

  // Check file extension
  const ext = path.extname(resolvedPath).toLowerCase();
  const allowed = [".pdf", ".png", ".jpg", ".jpeg", ".csv"];
  if (!allowed.includes(ext)) {
    return {
      content: [
        {
          type: "text",
          text: `Invalid file type: ${ext}. Allowed: ${allowed.join(", ")}`,
        },
      ],
      isError: true,
    };
  }

  try {
    // Create form data
    const form = new FormData();
    form.append("file", fs.createReadStream(resolvedPath));
    form.append("source", "mcp");
    form.append("ocr_engine", ocrEngine);

    const headers = { ...form.getHeaders() };
    if (authToken) {
      headers["Authorization"] = `Bearer ${authToken}`;
    }

    // Upload and analyze
    const response = await axios.post(`${API_BASE_URL}/upload`, form, {
      headers,
      timeout: 120000,
      maxContentLength: Infinity,
      maxBodyLength: Infinity,
    });

    if (!response.data.success) {
      return {
        content: [{ type: "text", text: `Analysis failed: ${response.data.error}` }],
        isError: true,
      };
    }

    const result = response.data.data;
    lastScanResult = result;

    // Format output
    const level1 = result.level1 || {};
    const level2 = result.level2 || {};
    const level3 = result.level3 || {};

    let output = `
📊 TRANSCRIPT ANALYSIS COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 LEVEL 1: CREDIT TALLY
  Total Courses: ${level1.total_entries || 0}
  Unique Courses: ${level1.unique_courses || 0}
  Credits Earned: ${level1.earned_credits || 0}
  Credits Attempted: ${level1.total_credits_attempted || 0}
  Failed Credits: ${level1.failed_credits || 0}
  Progress: ${level1.progress_130 || 0}% of 130 credits
  Retakes: ${level1.retakes_count || 0}

📈 LEVEL 2: CGPA ANALYSIS
  CGPA: ${(level2.cgpa || 0).toFixed(2)}
  Academic Standing: ${level2.standing || "N/A"} ${level2.stars || ""}
  GPA Credits: ${level2.gpa_credits || 0}
  Quality Points: ${level2.total_quality_points || 0}
  ${level2.waiver ? `🎓 Waiver: ${level2.waiver.name} (${level2.waiver.level})` : "No waiver eligible"}

🎓 LEVEL 3: DEGREE AUDIT
  Program: ${level3.program_name || "Not detected"}
  Mandatory Progress: ${level3.mandatory_progress || 0}% (${level3.mandatory_completed || 0}/${level3.mandatory_total || 0})
  Graduation Ready: ${level3.graduation_ready ? "✓ YES" : "✗ NO"}
`;

    if (level3.mandatory_missing && level3.mandatory_missing.length > 0) {
      output += `\n  Missing Mandatory Courses:\n`;
      level3.mandatory_missing.forEach((c, i) => {
        output += `    ${i + 1}. ${c}\n`;
      });
    }

    return {
      content: [{ type: "text", text: output }],
    };
  } catch (error) {
    return {
      content: [{ type: "text", text: `Scan failed: ${error.message}` }],
      isError: true,
    };
  }
}

/**
 * Login handler
 */
async function handleLogin(email, name) {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/auth/google`,
      {
        email,
        name: name || "MCP User",
        provider: "mcp",
      },
      { timeout: 30000 }
    );

    if (response.data.success) {
      authToken = response.data.token;
      currentUser = response.data.user;

      return {
        content: [
          {
            type: "text",
            text: `✓ Logged in as ${currentUser.name || email}\nEmail: ${currentUser.email}\nYour scans will be saved to history.`,
          },
        ],
      };
    } else {
      return {
        content: [{ type: "text", text: `Login failed: ${response.data.error}` }],
        isError: true,
      };
    }
  } catch (error) {
    return {
      content: [{ type: "text", text: `Login error: ${error.message}` }],
      isError: true,
    };
  }
}

/**
 * Get history handler
 */
async function handleGetHistory(limit) {
  if (!authToken) {
    return {
      content: [{ type: "text", text: "Please login first using the login tool" }],
      isError: true,
    };
  }

  try {
    const response = await axios.get(`${API_BASE_URL}/history`, {
      params: { limit },
      headers: { Authorization: `Bearer ${authToken}` },
      timeout: 30000,
    });

    if (!response.data.success) {
      return {
        content: [{ type: "text", text: "Failed to get history" }],
        isError: true,
      };
    }

    const history = response.data.history || [];
    if (history.length === 0) {
      return {
        content: [{ type: "text", text: "No scans in history yet." }],
      };
    }

    let output = `📜 SCAN HISTORY (${history.length} scans)\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n`;

    history.forEach((scan, i) => {
      output += `${i + 1}. ${scan.filename || "Transcript"}\n`;
      output += `   CGPA: ${(scan.cgpa || 0).toFixed(2)} | Courses: ${scan.total_courses} | Credits: ${scan.total_credits}\n`;
      output += `   Date: ${new Date(scan.created_at).toLocaleString()}\n\n`;
    });

    return {
      content: [{ type: "text", text: output }],
    };
  } catch (error) {
    return {
      content: [{ type: "text", text: `Error: ${error.message}` }],
      isError: true,
    };
  }
}

/**
 * Calculate CGPA handler
 */
function handleCalculateCGPA(courses) {
  const gradePoints = {
    A: 4.0, "A-": 3.7,
    "B+": 3.3, B: 3.0, "B-": 2.7,
    "C+": 2.3, C: 2.0, "C-": 1.7,
    "D+": 1.3, D: 1.0,
    F: 0.0,
  };

  let totalPoints = 0;
  let totalCredits = 0;

  const results = courses.map((c) => {
    const grade = c.grade.toUpperCase();
    const credits = parseFloat(c.credits) || 0;
    const points = gradePoints[grade];

    if (points !== undefined && credits > 0) {
      const qp = points * credits;
      totalPoints += qp;
      totalCredits += credits;
      return { code: c.code, credits, grade, points, qp: qp.toFixed(2) };
    }
    return { code: c.code, credits, grade, points: "N/A", qp: "N/A" };
  });

  const cgpa = totalCredits > 0 ? totalPoints / totalCredits : 0;

  let output = `CGPA CALCULATION\n━━━━━━━━━━━━━━━━━━━━\n\n`;
  output += `Course\t\tCredits\tGrade\tQP\n`;
  output += `────────────────────────────────\n`;
  results.forEach((r) => {
    output += `${r.code}\t\t${r.credits}\t${r.grade}\t${r.qp}\n`;
  });
  output += `────────────────────────────────\n`;
  output += `Total Credits: ${totalCredits}\n`;
  output += `Total Quality Points: ${totalPoints.toFixed(2)}\n`;
  output += `CGPA: ${cgpa.toFixed(2)}\n`;

  return {
    content: [{ type: "text", text: output }],
  };
}

/**
 * Check graduation handler
 */
function handleCheckGraduation(program, courses) {
  // Basic program requirements (simplified)
  const requirements = {
    CSE: {
      mandatory: ["CSE115", "CSE173", "CSE215", "CSE225", "CSE311", "CSE323", "CSE331", "CSE332"],
      totalCredits: 130,
    },
    BBA: {
      mandatory: ["BUS101", "BUS201", "BUS301", "BUS401", "ECO101", "ECO201"],
      totalCredits: 124,
    },
    EEE: {
      mandatory: ["EEE101", "EEE201", "EEE301", "EEE401", "PHY101", "PHY102"],
      totalCredits: 130,
    },
  };

  const programUpper = program.toUpperCase();
  const req = requirements[programUpper];

  if (!req) {
    return {
      content: [
        {
          type: "text",
          text: `Program "${program}" not found. Available: CSE, BBA, EEE`,
        },
      ],
    };
  }

  const coursesUpper = courses.map((c) => c.toUpperCase());
  const completed = req.mandatory.filter((m) => coursesUpper.includes(m));
  const missing = req.mandatory.filter((m) => !coursesUpper.includes(m));
  const progress = Math.round((completed.length / req.mandatory.length) * 100);

  let output = `GRADUATION CHECK: ${programUpper}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n`;
  output += `Progress: ${progress}% (${completed.length}/${req.mandatory.length} mandatory)\n`;
  output += `Required Credits: ${req.totalCredits}\n\n`;

  if (completed.length > 0) {
    output += `✓ Completed Mandatory:\n`;
    completed.forEach((c) => (output += `  - ${c}\n`));
  }

  if (missing.length > 0) {
    output += `\n✗ Missing Mandatory:\n`;
    missing.forEach((c) => (output += `  - ${c}\n`));
  }

  output += `\nGraduation Ready: ${missing.length === 0 ? "✓ YES" : "✗ NO"}`;

  return {
    content: [{ type: "text", text: output }],
  };
}

/**
 * Export scan handler
 */
async function handleExportScan(scanId, format = "json") {
  try {
    const id = scanId === "last" ? (lastScanResult?.scan_id || "") : scanId;
    
    if (!id) {
      return {
        content: [{ type: "text", text: "No scan ID available. Perform a scan first or provide a scan_id." }],
        isError: true,
      };
    }

    const headers = {};
    if (authToken) {
      headers["Authorization"] = `Bearer ${authToken}`;
    }

    const response = await axios.get(`${API_BASE_URL}/export/${id}?format=${format}`, {
      headers,
      timeout: 30000,
    });

    if (format === "csv") {
      return {
        content: [{ type: "text", text: `CSV Export:\n\n${response.data}` }],
      };
    }

    return {
      content: [{ type: "text", text: JSON.stringify(response.data, null, 2) }],
    };
  } catch (error) {
    return {
      content: [{ type: "text", text: `Export failed: ${error.message}` }],
      isError: true,
    };
  }
}

/**
 * Predict GPA handler
 */
function handlePredictGPA(currentCGPA, currentCredits, plannedCourses) {
  const gradePoints = {
    A: 4.0, "A-": 3.7,
    "B+": 3.3, B: 3.0, "B-": 2.7,
    "C+": 2.3, C: 2.0, "C-": 1.7,
    "D+": 1.3, D: 1.0,
    F: 0.0,
  };

  let currentQP = currentCGPA * currentCredits;
  let totalCredits = currentCredits;
  let plannedCredits = 0;

  const predictions = plannedCourses.map((c) => {
    const grade = c.expected_grade.toUpperCase();
    const credits = parseFloat(c.credits) || 0;
    const points = gradePoints[grade];

    if (points !== undefined && credits > 0) {
      currentQP += points * credits;
      totalCredits += credits;
      plannedCredits += credits;
      return { credits, grade, points };
    }
    return { credits, grade, points: "N/A" };
  });

  const predictedCGPA = totalCredits > 0 ? currentQP / totalCredits : 0;

  let output = `GPA PREDICTION\n━━━━━━━━━━━━━━━━━━━━\n\n`;
  output += `Current CGPA: ${currentCGPA.toFixed(2)}\n`;
  output += `Current Credits: ${currentCredits}\n\n`;
  output += `Planned Courses:\n`;
  predictions.forEach((p, i) => {
    output += `  Course ${i + 1}: ${p.credits} credits, Grade ${p.grade} (${p.points} points)\n`;
  });
  output += `\nPlanned Credits: ${plannedCredits}\n`;
  output += `Total Credits After: ${totalCredits}\n`;
  output += `Predicted CGPA: ${predictedCGPA.toFixed(2)}\n`;
  
  // Check waiver eligibility
  if (predictedCGPA >= 3.97) {
    output += `\n🎓 Eligible for: Chancellor's Award (100% waiver)`;
  } else if (predictedCGPA >= 3.75) {
    output += `\n🎓 Eligible for: VC's Scholarship (50% waiver)`;
  } else if (predictedCGPA >= 3.50) {
    output += `\n🎓 Eligible for: Dean's Scholarship (25% waiver)`;
  }

  return {
    content: [{ type: "text", text: output }],
  };
}

/**
 * Get OCR engines handler
 */
async function handleGetOCREngines() {
  try {
    const response = await axios.get(`${API_BASE_URL}/health`, { timeout: 10000 });
    const data = response.data;
    const ocr = data.ocr_engines || {};

    let output = `OCR ENGINES STATUS\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n`;
    
    output += `Google Cloud Vision:\n`;
    output += `  Status: ${ocr.google_vision?.configured ? "✓ Configured" : "✗ Not Configured"}\n`;
    output += `  Accuracy: 98%+\n`;
    output += `  Free Tier: ${ocr.google_vision?.free_tier || "1,000 requests/month"}\n`;
    output += `  Best For: General documents, fast processing\n\n`;
    
    output += `Azure Document Intelligence:\n`;
    output += `  Status: ${ocr.azure_doc_intelligence?.configured ? "✓ Configured" : "✗ Not Configured"}\n`;
    output += `  Accuracy: ${ocr.azure_doc_intelligence?.accuracy || "99%+"}\n`;
    output += `  Free Tier: ${ocr.azure_doc_intelligence?.free_tier || "500 pages/month"}\n`;
    output += `  Best For: Complex tables, academic transcripts\n\n`;
    
    output += `Usage:\n`;
    output += `  Use 'auto' to let the system choose the best available engine.\n`;
    output += `  Use 'google_vision' or 'azure' to force a specific engine.`;

    return {
      content: [{ type: "text", text: output }],
    };
  } catch (error) {
    return {
      content: [{ type: "text", text: `Failed to get OCR status: ${error.message}` }],
      isError: true,
    };
  }
}

/**
 * Start the server
 */
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("NSU Degree Audit MCP Server running");
}

main().catch(console.error);
