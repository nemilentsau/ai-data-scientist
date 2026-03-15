/** Parse a JSONL trace string into structured events. */
export function parseTrace(text) {
  const lines = text.trim().split("\n");
  const events = [];
  let meta = null;

  for (const line of lines) {
    if (!line.trim()) continue;
    try {
      const obj = JSON.parse(line);
      if (obj.type === "result") {
        meta = obj;
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
      }
    } catch {
      // skip malformed lines
    }
  }

  return { events, meta };
}

/** Parse a session.json file (Claude CLI output). */
export function parseSession(text) {
  try {
    const data = JSON.parse(text);
    // session.json is the raw Claude CLI JSON output
    return { session: data };
  } catch {
    return { session: null };
  }
}

/** Extract unique tool names from events. */
export function extractTools(events) {
  const tools = new Set();
  for (const e of events) {
    if (e.tool) tools.add(e.tool);
  }
  return [...tools].sort();
}

/** Compute summary stats from events + meta. */
export function computeStats(events, meta) {
  const toolCalls = events.filter((e) => e.tool).length;
  const errors = events.filter((e) => e.error || e.event === "PostToolUseFailure").length;

  let durationMs = meta?.duration_ms ?? 0;
  if (!durationMs && events.length >= 2) {
    const first = new Date(events[0].timestamp).getTime();
    const last = new Date(events[events.length - 1].timestamp).getTime();
    durationMs = last - first;
  }

  return {
    totalEvents: events.length,
    toolCalls,
    errors,
    durationMs,
    durationFormatted: formatDuration(durationMs),
    costUsd: meta?.total_cost_usd ?? null,
    numTurns: meta?.num_turns ?? null,
  };
}

/** Format ms to human readable duration. */
export function formatDuration(ms) {
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

/** Tool name to color mapping. */
const TOOL_COLORS = {
  Bash: "var(--green)",
  Read: "var(--accent)",
  Write: "var(--purple)",
  Edit: "var(--orange)",
  Glob: "var(--cyan)",
  Grep: "var(--cyan)",
  Agent: "var(--pink)",
};

export function toolColor(tool) {
  return TOOL_COLORS[tool] ?? "var(--text-muted)";
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
      return shortPath(input.file_path ?? "");
    case "Edit":
      return shortPath(input.file_path ?? "");
    case "Glob":
      return input.pattern ?? "";
    case "Grep":
      return input.pattern ?? "";
    case "Agent":
      return input.description ?? input.prompt?.slice(0, 80) ?? "";
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
  if (event.tool === "Edit") {
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
