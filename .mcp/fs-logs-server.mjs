#!/usr/bin/env node
/**
 * Filesystem MCP Server for LOGS directory
 *
 * Provides read-only access to test output logs.
 * Restricted to the LOGS/ directory for security.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { readFile, readdir, stat, access } from "fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const logsDir = path.resolve(__dirname, "..", "LOGS");

// Probe mode for quick self-test
if (process.argv.includes("--probe")) {
  console.log("✓ TasteOS FS-Logs MCP Server ready");
  console.log(`  LOGS directory: ${logsDir}`);

  try {
    await access(logsDir);
    const files = await readdir(logsDir);
    console.log(`  ✓ Found ${files.length} files`);
    const logFiles = files.filter(f => f.endsWith(".log") || f.endsWith(".txt"));
    if (logFiles.length > 0) {
      console.log(`  Recent logs: ${logFiles.slice(0, 3).join(", ")}`);
    }
  } catch (error) {
    console.log(`  ✗ Cannot access LOGS: ${error.message}`);
  }
  process.exit(0);
}

const server = new Server(
  {
    name: "tasteos-fs-logs",
    version: "1.0.0",
  },
  {
    capabilities: {
      resources: {},
    },
  }
);

function validatePath(filePath) {
  // Reject absolute paths
  if (path.isAbsolute(filePath)) {
    throw new Error("Access denied: Absolute paths not allowed");
  }

  // Reject paths containing '..'
  if (filePath.includes("..")) {
    throw new Error("Access denied: Parent directory traversal not allowed");
  }

  // Only allow .txt files (prevents exfiltration of DB dumps, JSON exports, etc.)
  if (!filePath.endsWith(".txt")) {
    throw new Error("Access denied: Only .txt files are allowed");
  }

  const resolvedPath = path.resolve(logsDir, filePath);
  const relativePath = path.relative(logsDir, resolvedPath);

  // Double-check it resolves inside LOGS/
  if (relativePath.startsWith("..") || path.isAbsolute(relativePath)) {
    throw new Error("Access denied: Path resolves outside LOGS directory");
  }

  return resolvedPath;
}

server.setRequestHandler(ListResourcesRequestSchema, async () => {
  try {
    const files = await readdir(logsDir);
    const resources = [];

    for (const file of files) {
      if (file === ".gitkeep") continue;

      const filePath = path.join(logsDir, file);
      const stats = await stat(filePath);

      if (stats.isFile()) {
        resources.push({
          uri: `file:///${path.join("LOGS", file).replace(/\\/g, "/")}`,
          name: file,
          mimeType: file.endsWith(".json") || file.endsWith(".jsonl") ? "application/json" : "text/plain",
        });
      }
    }

    return { resources };
  } catch (error) {
    console.error("Error listing resources:", error);
    return { resources: [] };
  }
});

server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  try {
    const uri = request.params.uri;
    const filename = path.basename(new URL(uri).pathname);
    const filePath = validatePath(filename);

    const content = await readFile(filePath, "utf-8");

    return {
      contents: [
        {
          uri,
          mimeType: filename.endsWith(".json") || filename.endsWith(".jsonl") ? "application/json" : "text/plain",
          text: content,
        },
      ],
    };
  } catch (error) {
    throw new Error(`Failed to read file: ${error.message}`);
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("TasteOS FS-Logs MCP server running");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
