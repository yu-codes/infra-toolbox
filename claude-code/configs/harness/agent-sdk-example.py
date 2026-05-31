"""
agent_sdk_example.py - Claude Agent SDK Python example
Run: pip install claude-agent-sdk && python agent_sdk_example.py
"""

import asyncio
import os
from claude_agent_sdk import query, ClaudeAgentOptions


async def run_agent(
    prompt: str,
    working_directory: str = ".",
    model: str = "sonnet",
    max_turns: int = 20,
    allowed_tools: list[str] | None = None,
):
    """Run a Claude Code agent with the given configuration."""
    if allowed_tools is None:
        allowed_tools = ["Read", "Edit", "Bash", "Glob", "Grep", "Write"]

    result = ""
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            working_directory=working_directory,
            allowed_tools=allowed_tools,
            model=model,
            max_turns=max_turns,
            permission_mode="bypassPermissions",
        ),
    ):
        if hasattr(message, "result"):
            result = message.result

    return result


async def main():
    repo_path = os.environ.get("REPO_PATH", ".")
    task = os.environ.get("TASK", "Summarize this project")

    print(f"🤖 Running agent on: {repo_path}")
    print(f"   Task: {task}")
    print("---")

    result = await run_agent(prompt=task, working_directory=repo_path)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
