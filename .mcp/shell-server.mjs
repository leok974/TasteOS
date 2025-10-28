#!/usr/bin/env node
/**
 * Shell MCP Server with tightly whitelisted commands
 *
 * Only allows specific checked-in scripts to be executed.
 * No arbitrary shell access.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { spawn } from "child_process";
import { access } from "fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const cwd = path.resolve(__dirname, "..");
const scripts = path.join(cwd, "apps", "api", "scripts");

// Probe mode for quick self-test
if (process.argv.includes("--probe")) {
  console.log("✓ TasteOS Shell MCP Server ready");
  console.log(`  Workspace: ${cwd}`);
  console.log(`  Scripts: ${scripts}`);
  
  // Verify scripts exist
  const scriptFiles = ["test_api.ps1", "test_api.sh", "login.ps1"];
  for (const file of scriptFiles) {
    const scriptPath = path.join(scripts, file);
    try {
      await access(scriptPath);
      console.log(`  ✓ ${file}`);
    } catch {
      console.log(`  ✗ ${file} (missing)`);
    }
  }
  process.exit(0);
}

// Whitelisted commands - only checked-in scripts under workspace
const ALLOWED_SCRIPTS = [
  path.join(scripts, "test_api.sh"),
  path.join(scripts, "test_api.ps1"),
  path.join(scripts, "login.ps1"),
];

// Verify all scripts are under workspace root
for (const scriptPath of ALLOWED_SCRIPTS) {
  const relative = path.relative(cwd, scriptPath);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(`Security: Script outside workspace: ${scriptPath}`);
  }
}

const server = new Server(
  {
    name: "tasteos-shell-safe",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

async function executeCommand(command) {
  return new Promise((resolve, reject) => {
    // Extract script path from command
    let scriptPath;
    if (command.includes("pwsh -File")) {
      scriptPath = command.split("pwsh -File ")[1].split(" ")[0];
    } else if (command.includes("bash")) {
      scriptPath = command.split("bash ")[1].split(" ")[0];
    } else {
      reject(new Error(`Unrecognized command format: ${command}`));
      return;
    }
    
    // Validate script is whitelisted and under workspace
    if (!ALLOWED_SCRIPTS.includes(scriptPath)) {
      reject(new Error(`Script not whitelisted: ${scriptPath}\nAllowed: ${ALLOWED_SCRIPTS.join(", ")}`));
      return;
    }
    
    const relative = path.relative(cwd, scriptPath);
    if (relative.startsWith("..") || path.isAbsolute(relative)) {
      reject(new Error(`Security: Script outside workspace: ${scriptPath}`));
      return;
    }

    const proc = spawn(command, {
      shell: true,
      cwd,
    });

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    proc.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    proc.on("close", (code) => {
      resolve({ exitCode: code, stdout, stderr });
    });

    proc.on("error", (error) => {
      reject(error);
    });
  });
}

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "run_script",
        description: "Execute a whitelisted script. Only pre-approved scripts can run.",
        inputSchema: {
          type: "object",
          properties: {
            script: {
              type: "string",
              enum: ["test_api.ps1", "test_api.sh", "login.ps1"],
              description: "Script to execute",
            },
            args: {
              type: "string",
              description: "Arguments to pass to the script (e.g., '-Token abc123')",
            },
          },
          required: ["script"],
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "run_script") {
    const { script, args = "" } = request.params.arguments;

    let command;
    if (script.endsWith(".ps1")) {
      command = `pwsh -File ${path.join(scripts, script)}`;
    } else if (script.endsWith(".sh")) {
      command = `bash ${path.join(scripts, script)}`;
    } else {
      throw new Error(`Unknown script type: ${script}`);
    }

    if (args) {
      command += ` ${args}`;
    }

    try {
      const result = await executeCommand(command);
      return {
        content: [
          {
            type: "text",
            text: `Exit code: ${result.exitCode}\n\n${result.stdout}${result.stderr}`,
          },
        ],
      };
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
  }

  throw new Error(`Unknown tool: ${request.params.name}`);
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("TasteOS Shell MCP server running");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
