/** Parse a JSONL trace string into structured events. */
export function parseTrace(text) {
  const lines = text.trim().split("\n");
  const events = [];
  const meta = { num_turns: 0 };

  for (const line of lines) {
    if (!line.trim()) continue;
    try {
      const obj = JSON.parse(line);
      if (obj.type === "result") {
        Object.assign(meta, obj);
        continue;
      }
      if (obj.tool || obj.event) {
        // Parse tool_response if it's a JSON string
        if (typeof obj.tool_response === "string") {
          try {
            obj.tool_response_parsed = JSON.parse(obj.tool_response);
          } catch {
            obj.tool_response_parsed = obj.tool_response;
          }
        } else {
          obj.tool_response_parsed = obj.tool_response;
        }
        events.push(obj);
        continue;
      }

      if (obj.type === "thread.started") {
        meta.thread_id = obj.thread_id;
        continue;
      }

      if (obj.type === "turn.completed") {
        meta.num_turns += 1;
        if (obj.usage) meta.usage = obj.usage;
        continue;
      }

      if (obj.type === "turn.failed") {
        meta.num_turns += 1;
        events.push(normalizeCodexSystemEvent(obj, "Turn failed"));
        continue;
      }

      if (obj.type === "error") {
        events.push(normalizeCodexSystemEvent(obj, obj.message ?? "Codex error"));
        continue;
      }

      if ((obj.type === "item.completed" || obj.type === "item.started") && obj.item) {
        const normalized = normalizeCodexItem(obj);
        if (normalized) events.push(normalized);
      }
    } catch {
      // skip malformed lines
    }
  }

  const hasMeta = Object.keys(meta).some((key) => key !== "num_turns") || meta.num_turns > 0;
  return { events, meta: hasMeta ? meta : null };
}

/** Extract unique tool names from events. */
export function extractTools(events) {
  const tools = new Set();
  for (const e of events) {
    if (e.tool) tools.add(e.tool);
  }
  return [...tools].sort();
}

/** Compute summary stats from events + meta + session. */
export function computeStats(events, meta, session) {
  const toolCalls = events.filter((e) => e.tool).length;
  const errors = events.filter((e) => e.error || e.event === "PostToolUseFailure").length;

  let durationMs = meta?.duration_ms ?? session?.duration_ms ?? 0;
  if (!durationMs && events.length >= 2) {
    const first = Date.parse(events[0].timestamp ?? "");
    const last = Date.parse(events[events.length - 1].timestamp ?? "");
    if (Number.isFinite(first) && Number.isFinite(last)) {
      durationMs = last - first;
    }
  }
  if (!Number.isFinite(durationMs) || durationMs < 0) durationMs = 0;

  return {
    totalEvents: events.length,
    toolCalls,
    errors,
    durationMs,
    durationFormatted: formatDuration(durationMs),
    costUsd: meta?.total_cost_usd ?? session?.total_cost_usd ?? null,
    numTurns: meta?.num_turns ?? session?.num_turns ?? null,
  };
}

/** Format ms to human readable duration. */
export function formatDuration(ms) {
  if (!Number.isFinite(ms) || ms < 0) return "0ms";
  if (ms < 1000) return `${ms}ms`;
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}m ${rem}s`;
}

/** Format a timestamp to HH:MM:SS. */
export function formatTime(ts) {
  if (!ts) return "";
  const d = new Date(ts);
  return d.toTimeString().slice(0, 8);
}

/** Compute delta in seconds between two timestamps. */
export function deltaSeconds(ts1, ts2) {
  if (!ts1 || !ts2) return null;
  return ((new Date(ts2).getTime() - new Date(ts1).getTime()) / 1000).toFixed(1);
}

/** Verdict → CSS color variable mapping. */
export const VERDICT_COLORS = {
  solved: "var(--color-green)",
  pass: "var(--color-green)",
  partial: "var(--color-orange)",
  wrong: "var(--color-red)",
  failed: "var(--color-red)",
  run_error: "var(--color-red)",
};

/** Verdict → soft background color mapping. */
export const VERDICT_BG = {
  solved: "var(--color-green-soft)",
  pass: "var(--color-green-soft)",
  partial: "var(--color-orange-soft)",
  wrong: "var(--color-red-soft)",
  failed: "var(--color-red-soft)",
  run_error: "var(--color-red-soft)",
};

/** Display-friendly verdict label. */
export function displayVerdict(verdict) {
  return verdict === "run_error" ? "run error" : verdict;
}

/** Tool name to color mapping. */
const TOOL_COLORS = {
  Bash: "var(--color-green)",
  Read: "var(--color-accent)",
  Write: "var(--color-purple)",
  Edit: "var(--color-orange)",
  Glob: "var(--color-cyan)",
  Grep: "var(--color-cyan)",
  Agent: "var(--color-pink)",
  Reasoning: "var(--color-text-muted)",
  MCP: "var(--color-accent)",
  Web: "var(--color-cyan)",
  Plan: "var(--color-orange)",
  System: "var(--color-red)",
};

export function toolColor(tool) {
  return TOOL_COLORS[tool] ?? "var(--color-text-muted)";
}

/** Tool name to icon mapping. */
const TOOL_ICONS = {
  Bash: "$",
  Read: "R",
  Write: "W",
  Edit: "E",
  Glob: "G",
  Grep: "?",
  Agent: "A",
  Reasoning: "~",
  MCP: "M",
  Web: "W",
  Plan: "P",
  System: "!",
};

export function toolIcon(tool) {
  return TOOL_ICONS[tool] ?? tool?.[0] ?? "?";
}

/** Extract a human-readable summary from a tool input. */
export function summarizeInput(tool, input) {
  if (!input) return "";
  switch (tool) {
    case "Bash":
      return input.command ?? "";
    case "Read":
      return shortPath(input.file_path ?? "");
    case "Write":
      return summarizeFileTarget(input);
    case "Edit":
      return summarizeFileTarget(input);
    case "Glob":
      return input.pattern ?? "";
    case "Grep":
      return input.pattern ?? "";
    case "Agent":
    case "Reasoning":
    case "Plan":
      return input.description ?? input.prompt?.slice(0, 80) ?? "";
    case "Web":
      return input.query ?? input.description ?? "";
    case "MCP":
      return input.description ?? input.server ?? JSON.stringify(input).slice(0, 80);
    case "System":
      return input.description ?? "";
    default:
      return JSON.stringify(input).slice(0, 100);
  }
}

function shortPath(p) {
  if (!p) return "";
  const parts = p.split("/");
  if (parts.length <= 3) return p;
  return ".../" + parts.slice(-2).join("/");
}

/** Try to extract Python code from a tool response. */
export function extractCode(event) {
  if (!event.tool_input) return null;

  if (event.tool === "Write" && event.tool_input.content) {
    return { code: event.tool_input.content, language: guessLanguage(event.tool_input.file_path) };
  }
  if (event.tool === "Edit" && (event.tool_input.old_string || event.tool_input.new_string)) {
    return {
      code: formatDiff(event.tool_input.old_string, event.tool_input.new_string),
      language: "diff",
    };
  }
  if (event.tool === "Bash" && event.tool_input.command) {
    return { code: event.tool_input.command, language: "bash" };
  }
  return null;
}

function guessLanguage(path) {
  if (!path) return "text";
  if (path.endsWith(".py")) return "python";
  if (path.endsWith(".js") || path.endsWith(".ts")) return "javascript";
  if (path.endsWith(".json")) return "json";
  if (path.endsWith(".md")) return "markdown";
  if (path.endsWith(".sh")) return "bash";
  if (path.endsWith(".css")) return "css";
  if (path.endsWith(".html") || path.endsWith(".svelte")) return "html";
  return "text";
}

function formatDiff(old_str, new_str) {
  if (!old_str && !new_str) return "";
  const lines = [];
  if (old_str) {
    for (const l of old_str.split("\n")) {
      lines.push("- " + l);
    }
  }
  if (new_str) {
    for (const l of new_str.split("\n")) {
      lines.push("+ " + l);
    }
  }
  return lines.join("\n");
}

/** Extract plot file paths from events. */
export function extractPlots(events) {
  const plots = [];
  for (const e of events) {
    if (e.tool === "Write" && e.tool_input?.file_path?.match(/\.(png|jpg|jpeg|svg|gif)$/i)) {
      plots.push(e.tool_input.file_path);
    }
    if ((e.tool === "Write" || e.tool === "Edit") && e.tool_input?.changes) {
      for (const change of e.tool_input.changes) {
        if (change.path?.match(/\.(png|jpg|jpeg|svg|gif)$/i)) {
          plots.push(change.path);
        }
      }
    }
    // Also check Bash commands that might create plots via matplotlib savefig
    if (e.tool === "Bash" && e.tool_input?.command) {
      const matches = e.tool_input.command.match(/savefig\(['"]([^'"]+)['"]\)/g);
      if (matches) {
        for (const m of matches) {
          const path = m.match(/savefig\(['"]([^'"]+)['"]\)/)?.[1];
          if (path) plots.push(path);
        }
      }
    }
  }
  return [...new Set(plots)];
}

/** Parse analysis_report.md content and extract sections. */
export function parseReport(text) {
  if (!text) return [];
  const sections = [];
  const lines = text.split("\n");
  let currentSection = null;

  for (const line of lines) {
    const h2 = line.match(/^##\s+(.+)/);
    const h3 = line.match(/^###\s+(.+)/);
    if (h2) {
      if (currentSection) sections.push(currentSection);
      currentSection = { title: h2[1], level: 2, content: [] };
    } else if (h3) {
      if (currentSection) sections.push(currentSection);
      currentSection = { title: h3[1], level: 3, content: [] };
    } else {
      if (!currentSection) {
        currentSection = { title: "", level: 1, content: [] };
      }
      currentSection.content.push(line);
    }
  }
  if (currentSection) sections.push(currentSection);
  return sections;
}

function normalizeCodexItem(obj) {
  const item = obj.item ?? {};
  const eventType = obj.type;

  if (eventType === "item.started" && !["command_execution", "file_change"].includes(item.type)) {
    return null;
  }

  const tool = codexToolName(item);
  const tool_input = codexToolInput(item);
  const tool_response = codexToolResponse(item);
  const error = codexItemError(item);

  const normalized = {
    event: eventType,
    tool,
    tool_input,
    tool_response,
    error,
    codex_item_type: item.type,
    status: item.status ?? (eventType === "item.started" ? "in_progress" : "completed"),
    item_id: item.id ?? null,
    raw_item: item,
  };

  if (typeof tool_response === "string") {
    normalized.tool_response_parsed = tool_response;
  } else {
    normalized.tool_response_parsed = tool_response;
  }

  return normalized;
}

function normalizeCodexSystemEvent(obj, description) {
  return {
    event: obj.type,
    tool: "System",
    tool_input: { description },
    tool_response: obj,
    tool_response_parsed: obj,
    error: obj.message ?? description,
  };
}

function codexToolName(item) {
  switch (item.type) {
    case "command_execution":
      return "Bash";
    case "file_change":
      return inferFileChangeTool(item.changes);
    case "agent_message":
      return "Agent";
    case "reasoning":
      return "Reasoning";
    case "mcp_tool_call":
      return "MCP";
    case "web_search":
      return "Web";
    case "plan_update":
      return "Plan";
    case "error":
      return "System";
    default:
      return "System";
  }
}

function codexToolInput(item) {
  switch (item.type) {
    case "command_execution":
      return { command: item.command ?? "" };
    case "file_change":
      return {
        file_path: item.changes?.[0]?.path ?? "",
        changes: item.changes ?? [],
      };
    case "agent_message":
      return { description: item.text ?? "" };
    case "reasoning":
      return { description: item.text ?? item.summary ?? "" };
    case "web_search":
      return { query: item.query ?? "", description: item.query ?? "" };
    case "plan_update":
      return { description: summarizePlan(item.plan ?? item.steps ?? []) };
    case "mcp_tool_call":
      return {
        description: item.server_name ?? item.name ?? item.tool_name ?? "",
        ...item,
      };
    case "error":
      return { description: item.message ?? "Codex error" };
    default:
      return item;
  }
}

function codexToolResponse(item) {
  switch (item.type) {
    case "command_execution":
      return {
        output: item.aggregated_output ?? "",
        exit_code: item.exit_code,
      };
    case "file_change":
      return { changes: item.changes ?? [] };
    case "agent_message":
      return item.text ?? "";
    case "reasoning":
      return item.text ?? item.summary ?? item;
    case "error":
      return item.message ?? "";
    default:
      return item;
  }
}

function codexItemError(item) {
  if (item.type === "error") return item.message ?? "Codex error";
  if (item.type === "command_execution" && item.exit_code && item.exit_code !== 0) {
    return {
      exit_code: item.exit_code,
      output: item.aggregated_output ?? "",
    };
  }
  return null;
}

function inferFileChangeTool(changes = []) {
  if (changes.length > 0 && changes.every((change) => change.kind === "add")) {
    return "Write";
  }
  return "Edit";
}

function summarizeFileTarget(input) {
  if (input.file_path) return shortPath(input.file_path);
  if (Array.isArray(input.changes) && input.changes.length > 0) {
    return input.changes.map((change) => shortPath(change.path ?? "")).join(", ");
  }
  return "";
}

function summarizePlan(steps) {
  if (!Array.isArray(steps) || steps.length === 0) return "";
  return steps
    .map((step) => step?.description ?? step?.title ?? String(step))
    .join(" | ");
}
