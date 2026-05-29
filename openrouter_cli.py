#!/usr/bin/env python3
"""
OpenRouter CLI - Agentic AI assistant with coding capabilities
Works like Gemini CLI with multi-turn conversation, tool use, and file ops
"""

import os
import sys
import json
import re
import subprocess
import tempfile
import shutil
import glob
try:
    import readline
    HAS_READLINE = True
except ImportError:
    # Windows doesn't include readline; try pyreadline3 as fallback
    try:
        import pyreadline3 as readline  # pip install pyreadline3
        HAS_READLINE = True
    except ImportError:
        HAS_READLINE = False
import argparse
import textwrap
from pathlib import Path
from datetime import datetime
import urllib.request
import urllib.error


# ─── Config ──────────────────────────────────────────────────────────────────

DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"  # Can override via --model
API_BASE = "https://openrouter.ai/api/v1/chat/completions"
HISTORY_FILE = Path.home() / ".openrouter_cli_history"
CONFIG_FILE = Path.home() / ".openrouter_cli.json"

COLORS = {
    "reset":   "\033[0m",
    "bold":    "\033[1m",
    "dim":     "\033[2m",
    "red":     "\033[91m",
    "green":   "\033[92m",
    "yellow":  "\033[93m",
    "blue":    "\033[94m",
    "magenta": "\033[95m",
    "cyan":    "\033[96m",
    "white":   "\033[97m",
    "gray":    "\033[90m",
}

def c(color, text):
    return f"{COLORS.get(color,'')}{text}{COLORS['reset']}"


SYSTEM_PROMPT = """You are an expert AI coding assistant running in a CLI environment. You have access to powerful tools to help users with programming, system tasks, and agentic workflows.

## Your Capabilities
- Write, read, edit, and execute code in any language
- Manage files and directories
- Run shell commands
- Search and analyze codebases
- Create multi-step agentic workflows
- Debug errors iteratively

## Tool Use
When you need to perform actions, use the provided tools. Always:
1. Think step-by-step before acting
2. Use the minimum tools necessary
3. Verify results before proceeding
4. Handle errors gracefully and retry with corrections

## Code Quality
- Write production-quality, well-commented code
- Follow language idioms and best practices
- Include error handling
- Make code modular and reusable

## Communication Style
- Be concise but thorough
- Show your reasoning for complex tasks
- Proactively suggest improvements
- Ask for clarification when the task is ambiguous
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a shell command and return stdout/stderr. Use for executing scripts, installing packages, running tests, git operations, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute"
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory (default: current dir)"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 30)"
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to read"
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Start line (1-indexed, optional)"
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "End line (1-indexed, optional)"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file (creates or overwrites)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit a file by replacing a specific string with another (for surgical edits)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to edit"
                    },
                    "old_str": {
                        "type": "string",
                        "description": "Exact string to replace (must be unique in file)"
                    },
                    "new_str": {
                        "type": "string",
                        "description": "Replacement string"
                    }
                },
                "required": ["path", "old_str", "new_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory with optional glob pattern",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path (default: current dir)"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern filter (e.g. '*.py', '**/*.js')"
                    },
                    "show_hidden": {
                        "type": "boolean",
                        "description": "Show hidden files (default: false)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for text/patterns in files using grep",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Text or regex pattern to search"
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory or file to search in (default: current dir)"
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "File pattern to include (e.g. '*.py')"
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Case sensitive search (default: true)"
                    }
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_plan",
            "description": "Create and display a multi-step plan for a complex agentic task",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Plan title"
                    },
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of steps to execute"
                    }
                },
                "required": ["title", "steps"]
            }
        }
    }
]


# ─── Tool Implementations ─────────────────────────────────────────────────────

def tool_run_shell(command, cwd=None, timeout=30):
    cwd = cwd or os.getcwd()
    print(c("gray", f"  $ {command}"))
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        if result.returncode != 0:
            output += f"\n[exit code: {result.returncode}]"
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return f"[ERROR] Command timed out after {timeout}s"
    except Exception as e:
        return f"[ERROR] {e}"


def tool_read_file(path, start_line=None, end_line=None):
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return f"[ERROR] File not found: {path}"
        content = p.read_text(errors="replace")
        if start_line or end_line:
            lines = content.splitlines()
            s = (start_line or 1) - 1
            e = end_line or len(lines)
            content = "\n".join(lines[s:e])
        size = len(content)
        if size > 50000:
            content = content[:50000] + f"\n\n[... truncated, {size} total chars]"
        return content
    except Exception as e:
        return f"[ERROR] {e}"


def tool_write_file(path, content):
    try:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        lines = content.count("\n") + 1
        return f"Written {lines} lines to {path}"
    except Exception as e:
        return f"[ERROR] {e}"


def tool_edit_file(path, old_str, new_str):
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return f"[ERROR] File not found: {path}"
        content = p.read_text(errors="replace")
        count = content.count(old_str)
        if count == 0:
            return "[ERROR] Pattern not found in file"
        if count > 1:
            return f"[ERROR] Pattern found {count} times (must be unique). Be more specific."
        p.write_text(content.replace(old_str, new_str, 1))
        return f"Successfully edited {path}"
    except Exception as e:
        return f"[ERROR] {e}"


def tool_list_files(path=None, pattern=None, show_hidden=False):
    try:
        base = Path(path or ".").expanduser()
        if not base.exists():
            return f"[ERROR] Path not found: {path}"
        if pattern:
            files = list(base.glob(pattern))
        else:
            files = list(base.iterdir())
        if not show_hidden:
            files = [f for f in files if not f.name.startswith(".")]
        files.sort(key=lambda f: (f.is_file(), f.name))
        lines = []
        for f in files:
            if f.is_dir():
                lines.append(f"📁 {f.name}/")
            else:
                size = f.stat().st_size
                size_str = f"{size}B" if size < 1024 else f"{size//1024}KB"
                lines.append(f"📄 {f.name} ({size_str})")
        return "\n".join(lines) if lines else "(empty directory)"
    except Exception as e:
        return f"[ERROR] {e}"


def tool_search_code(pattern, path=None, file_pattern=None, case_sensitive=True):
    cmd = ["grep", "-rn"]
    if not case_sensitive:
        cmd.append("-i")
    if file_pattern:
        cmd.extend(["--include", file_pattern])
    cmd.append(pattern)
    cmd.append(path or ".")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        out = result.stdout.strip()
        if not out:
            return "No matches found"
        lines = out.splitlines()
        if len(lines) > 100:
            out = "\n".join(lines[:100]) + f"\n... ({len(lines)} total matches)"
        return out
    except Exception as e:
        return f"[ERROR] {e}"


def tool_create_plan(title, steps):
    lines = [f"\n📋 {title}", "─" * (len(title) + 4)]
    for i, step in enumerate(steps, 1):
        lines.append(f"  {i}. {step}")
    return "\n".join(lines)


TOOL_MAP = {
    "run_shell":   tool_run_shell,
    "read_file":   tool_read_file,
    "write_file":  tool_write_file,
    "edit_file":   tool_edit_file,
    "list_files":  tool_list_files,
    "search_code": tool_search_code,
    "create_plan": tool_create_plan,
}


# ─── API ──────────────────────────────────────────────────────────────────────

def call_api(messages, model, api_key, stream=True):
    payload = {
        "model": model,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
        "stream": stream,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        API_BASE,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/openrouter-cli",
            "X-Title": "OpenRouter CLI",
        }
    )
    return urllib.request.urlopen(req, timeout=120)


def stream_response(messages, model, api_key):
    """Stream response, handle tool calls, return (text, tool_calls)"""
    text_parts = []
    tool_calls_raw = {}  # id -> {name, arguments_chunks}

    try:
        resp = call_api(messages, model, api_key, stream=True)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            err = json.loads(body)
            msg = err.get("error", {}).get("message", body)
        except Exception:
            msg = body
        return None, None, f"API error {e.code}: {msg}"
    except Exception as e:
        return None, None, str(e)

    print(c("cyan", "◆ "), end="", flush=True)

    for line in resp:
        line = line.decode("utf-8", errors="replace").strip()
        if not line.startswith("data: "):
            continue
        chunk = line[6:]
        if chunk == "[DONE]":
            break
        try:
            d = json.loads(chunk)
        except Exception:
            continue

        delta = d.get("choices", [{}])[0].get("delta", {})

        # Text content
        if delta.get("content"):
            t = delta["content"]
            text_parts.append(t)
            print(t, end="", flush=True)

        # Tool calls
        for tc in delta.get("tool_calls", []):
            idx = tc.get("index", 0)
            if idx not in tool_calls_raw:
                tool_calls_raw[idx] = {"id": "", "name": "", "arguments": ""}
            if tc.get("id"):
                tool_calls_raw[idx]["id"] = tc["id"]
            if tc.get("function", {}).get("name"):
                tool_calls_raw[idx]["name"] = tc["function"]["name"]
            if tc.get("function", {}).get("arguments"):
                tool_calls_raw[idx]["arguments"] += tc["function"]["arguments"]

    print()  # newline after streaming

    tool_calls = []
    for idx in sorted(tool_calls_raw.keys()):
        tc = tool_calls_raw[idx]
        try:
            args = json.loads(tc["arguments"]) if tc["arguments"] else {}
        except Exception:
            args = {}
        tool_calls.append({"id": tc["id"], "name": tc["name"], "args": args})

    return "".join(text_parts), tool_calls, None


# ─── Display ──────────────────────────────────────────────────────────────────

def print_tool_use(name, args):
    icons = {
        "run_shell":   "⚙",
        "read_file":   "📖",
        "write_file":  "✍",
        "edit_file":   "✏",
        "list_files":  "📂",
        "search_code": "🔍",
        "create_plan": "📋",
    }
    icon = icons.get(name, "🔧")
    arg_str = ""
    if "command" in args:
        arg_str = args["command"]
    elif "path" in args:
        arg_str = args["path"]
    elif "pattern" in args:
        arg_str = args["pattern"]
    elif "title" in args:
        arg_str = args["title"]
    print(c("yellow", f"  {icon} {name}") + c("gray", f"  {arg_str}"))


def print_tool_result(result):
    lines = str(result).splitlines()
    for line in lines[:30]:
        print(c("gray", f"    {line}"))
    if len(lines) > 30:
        print(c("gray", f"    ... ({len(lines)} lines total)"))


def render_markdown(text):
    """Simple markdown rendering for terminal"""
    lines = text.splitlines()
    result = []
    in_code = False
    code_lang = ""
    code_lines = []

    for line in lines:
        # Code blocks
        if line.startswith("```"):
            if not in_code:
                in_code = True
                code_lang = line[3:].strip()
                code_lines = []
            else:
                in_code = False
                result.append(c("gray", f"  ┌─ {code_lang or 'code'} " + "─" * max(0, 40 - len(code_lang))))
                for cl in code_lines:
                    result.append(c("white", f"  │ ") + c("cyan", cl))
                result.append(c("gray", "  └" + "─" * 42))
                code_lang = ""
                code_lines = []
            continue

        if in_code:
            code_lines.append(line)
            continue

        # Headers
        if line.startswith("### "):
            result.append(c("bold", c("cyan", line[4:])))
        elif line.startswith("## "):
            result.append(c("bold", c("blue", line[3:])))
        elif line.startswith("# "):
            result.append(c("bold", c("magenta", line[2:])))
        # Bold
        elif "**" in line:
            line = re.sub(r"\*\*(.+?)\*\*", lambda m: c("bold", m.group(1)), line)
            result.append(line)
        # Bullets
        elif line.startswith("- ") or line.startswith("* "):
            result.append(c("cyan", "  • ") + line[2:])
        elif re.match(r"^\d+\. ", line):
            m = re.match(r"^(\d+)\. (.+)", line)
            if m:
                result.append(c("cyan", f"  {m.group(1)}.") + f" {m.group(2)}")
            else:
                result.append(line)
        else:
            result.append(line)

    return "\n".join(result)


def print_banner():
    banner = """
  ╔═══════════════════════════════════════════╗
  ║   OpenRouter CLI  ·  Agentic AI Shell     ║
  ╚═══════════════════════════════════════════╝"""
    print(c("cyan", banner))
    print(c("gray", "  Type your message, or /help for commands\n"))


def print_help():
    cmds = [
        ("/help",         "Show this help"),
        ("/model <name>", "Switch model (e.g. /model anthropic/claude-opus-4)"),
        ("/models",       "List popular models"),
        ("/clear",        "Clear conversation history"),
        ("/context",      "Show current context (messages)"),
        ("/save <file>",  "Save conversation to JSON"),
        ("/load <file>",  "Load conversation from JSON"),
        ("/run <file>",   "Run a prompt from a file"),
        ("/cd <path>",    "Change working directory"),
        ("/pwd",          "Show current directory"),
        ("/exit",         "Exit the CLI"),
    ]
    print(c("bold", "\n  Commands:"))
    for cmd, desc in cmds:
        print(f"    {c('cyan', cmd):<30} {c('gray', desc)}")
    print()


POPULAR_MODELS = [
    ("google/gemini-2.5-pro",           "Google Gemini 2.5 Pro (default)"),
    ("google/gemini-2.5-flash",         "Google Gemini 2.5 Flash (fast)"),
    ("anthropic/claude-opus-4",         "Claude Opus 4 (most capable)"),
    ("anthropic/claude-sonnet-4-5",     "Claude Sonnet 4.5 (balanced)"),
    ("openai/gpt-4o",                   "OpenAI GPT-4o"),
    ("openai/o3",                       "OpenAI o3 (reasoning)"),
    ("meta-llama/llama-3.3-70b-instruct","Llama 3.3 70B (open)"),
    ("deepseek/deepseek-r1",            "DeepSeek R1 (reasoning, cheap)"),
    ("qwen/qwen3-235b-a22b",            "Qwen3 235B (MoE)"),
]

def print_models():
    print(c("bold", "\n  Popular OpenRouter Models:"))
    for model, desc in POPULAR_MODELS:
        print(f"    {c('cyan', model):<45} {c('gray', desc)}")
    print()


# ─── Config ───────────────────────────────────────────────────────────────────

def load_config():
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    return {}


def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


def get_api_key(cfg):
    key = (
        cfg.get("api_key")
        or os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("OR_API_KEY")
    )
    if not key:
        print(c("yellow", "\n  No API key found."))
        print(c("gray",   "  Get one at: https://openrouter.ai/keys"))
        print(c("gray",   "  Set it with: export OPENROUTER_API_KEY=sk-or-...\n"))
        key = input(c("cyan", "  Enter API key: ")).strip()
        if key:
            cfg["api_key"] = key
            save_config(cfg)
    return key


# ─── Agentic Loop ─────────────────────────────────────────────────────────────

def run_agentic_turn(user_input, messages, model, api_key):
    """Run a full agentic turn: stream response, handle tools, loop until done"""
    messages.append({"role": "user", "content": user_input})

    max_iterations = 20
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        text, tool_calls, error = stream_response(messages, model, api_key)

        if error:
            print(c("red", f"\n  Error: {error}"))
            messages.pop()  # Remove user message on error
            return

        # Render text if any
        if text and not tool_calls:
            # Final response - already streamed, just format for display
            pass
        elif text:
            # Intermediate text before tool calls
            pass

        # Build assistant message
        assistant_msg = {"role": "assistant", "content": text or ""}

        # If there are tool calls, we need to execute them
        if tool_calls:
            # Add tool_calls to assistant message in OpenAI format
            assistant_msg["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(tc["args"])
                    }
                }
                for tc in tool_calls
            ]
            messages.append(assistant_msg)

            # Execute each tool and add results
            print()
            for tc in tool_calls:
                name = tc["name"]
                args = tc["args"]
                print_tool_use(name, args)

                fn = TOOL_MAP.get(name)
                if fn:
                    try:
                        result = fn(**args)
                    except Exception as e:
                        result = f"[ERROR] Tool execution failed: {e}"
                else:
                    result = f"[ERROR] Unknown tool: {name}"

                print_tool_result(result)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": str(result)
                })

            print()
            # Continue the loop to get next response
        else:
            # No tool calls - final response
            messages.append(assistant_msg)
            break

    if iteration >= max_iterations:
        print(c("yellow", "\n  [Max iterations reached]"))


# ─── Main REPL ────────────────────────────────────────────────────────────────

def setup_readline():
    if not HAS_READLINE:
        return
    if HISTORY_FILE.exists():
        try:
            readline.read_history_file(str(HISTORY_FILE))
        except Exception:
            pass
    readline.set_history_length(1000)


def save_readline():
    if not HAS_READLINE:
        return
    try:
        readline.write_history_file(str(HISTORY_FILE))
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="OpenRouter CLI - Agentic AI Shell",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              openrouter-cli
              openrouter-cli --model anthropic/claude-opus-4
              openrouter-cli -p "Write a FastAPI server"
              openrouter-cli --key sk-or-xxxxx
        """)
    )
    parser.add_argument("--model", "-m", default=None, help="Model to use")
    parser.add_argument("--key",   "-k", default=None, help="OpenRouter API key")
    parser.add_argument("--prompt","-p", default=None, help="Run single prompt and exit")
    parser.add_argument("--file",  "-f", default=None, help="Read prompt from file")
    parser.add_argument("--no-banner", action="store_true", help="Skip banner")
    args = parser.parse_args()

    cfg = load_config()

    if args.key:
        cfg["api_key"] = args.key
        save_config(cfg)

    api_key = get_api_key(cfg)
    if not api_key:
        sys.exit(1)

    model = args.model or cfg.get("model", DEFAULT_MODEL)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    setup_readline()

    if not args.no_banner and not args.prompt and not args.file:
        print_banner()
        print(c("gray", f"  Model: {c('cyan', model)}"))
        print(c("gray", f"  CWD:   {c('cyan', os.getcwd())}\n"))

    # Single prompt mode
    if args.prompt:
        run_agentic_turn(args.prompt, messages, model, api_key)
        save_readline()
        return

    if args.file:
        prompt = Path(args.file).read_text().strip()
        run_agentic_turn(prompt, messages, model, api_key)
        save_readline()
        return

    # Interactive REPL
    while True:
        try:
            cwd_short = str(Path.cwd()).replace(str(Path.home()), "~")
            prompt_str = (
                c("blue", f"\n[{cwd_short}] ")
                + c("bold", c("green", "you"))
                + c("gray", " › ")
            )
            user_input = input(prompt_str).strip()
        except (EOFError, KeyboardInterrupt):
            print(c("gray", "\n  Goodbye!"))
            break

        if not user_input:
            continue

        # Commands
        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd == "/exit" or cmd == "/quit":
                print(c("gray", "  Goodbye!"))
                break

            elif cmd == "/help":
                print_help()

            elif cmd == "/models":
                print_models()

            elif cmd == "/model":
                if arg:
                    model = arg
                    cfg["model"] = model
                    save_config(cfg)
                    print(c("green", f"  Model switched to: {model}"))
                else:
                    print(c("cyan", f"  Current model: {model}"))

            elif cmd == "/clear":
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                print(c("green", "  Conversation cleared."))

            elif cmd == "/context":
                print(c("bold", "\n  Conversation history:"))
                for i, m in enumerate(messages):
                    role = m["role"]
                    content = str(m.get("content") or "")[:80]
                    print(c("gray", f"  [{i}] {role}: {content}..."))
                print()

            elif cmd == "/save":
                filename = arg or f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                Path(filename).write_text(json.dumps(messages, indent=2))
                print(c("green", f"  Saved to {filename}"))

            elif cmd == "/load":
                if arg and Path(arg).exists():
                    messages = json.loads(Path(arg).read_text())
                    print(c("green", f"  Loaded from {arg} ({len(messages)} messages)"))
                else:
                    print(c("red", f"  File not found: {arg}"))

            elif cmd == "/run":
                if arg and Path(arg).exists():
                    prompt = Path(arg).read_text().strip()
                    print(c("gray", f"  Running: {prompt[:60]}..."))
                    run_agentic_turn(prompt, messages, model, api_key)
                else:
                    print(c("red", f"  File not found: {arg}"))

            elif cmd == "/cd":
                target = Path(arg or Path.home()).expanduser()
                if target.exists():
                    os.chdir(target)
                    print(c("green", f"  Changed to: {target}"))
                else:
                    print(c("red", f"  Directory not found: {arg}"))

            elif cmd == "/pwd":
                print(c("cyan", f"  {os.getcwd()}"))

            else:
                print(c("red", f"  Unknown command: {cmd}. Type /help for commands."))

            continue

        # Normal message - run agentic turn
        run_agentic_turn(user_input, messages, model, api_key)

    save_readline()


if __name__ == "__main__":
    main()