/**
 * agent-sdk-example.ts - Claude Agent SDK TypeScript example
 * Run: npm install @anthropic-ai/claude-agent-sdk && npx tsx agent-sdk-example.ts
 */

import { query } from "@anthropic-ai/claude-agent-sdk";

async function runAgent(options: {
  prompt: string;
  workingDirectory?: string;
  model?: string;
  maxTurns?: number;
  allowedTools?: string[];
}): Promise<string> {
  const {
    prompt,
    workingDirectory = ".",
    model = "sonnet",
    maxTurns = 20,
    allowedTools = ["Read", "Edit", "Bash", "Glob", "Grep", "Write"],
  } = options;

  let result = "";

  for await (const message of query({
    prompt,
    options: {
      workingDirectory,
      allowedTools,
      model,
      maxTurns,
      permissionMode: "bypassPermissions",
    },
  })) {
    if ((message as any).result) {
      result = (message as any).result;
    }
  }

  return result;
}

async function main() {
  const repoPath = process.env.REPO_PATH || ".";
  const task = process.env.TASK || "Summarize this project";

  console.log(`🤖 Running agent on: ${repoPath}`);
  console.log(`   Task: ${task}`);
  console.log("---");

  const result = await runAgent({
    prompt: task,
    workingDirectory: repoPath,
  });

  console.log(result);
}

main().catch(console.error);
