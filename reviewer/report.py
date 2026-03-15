from pathlib import Path
from .scorer import ScoreResult
from .rubric import RUBRIC_DIMENSIONS

def generate_report(
    results: list[ScoreResult],
    output_path: Path,
) -> str:
    """Generate a markdown comparison report from scoring results."""
    # Group by dataset
    by_dataset: dict[str, dict[str, ScoreResult]] = {}
    for r in results:
        by_dataset.setdefault(r.dataset_name, {})[r.agent] = r

    lines = ["# AI Data Scientist Benchmark Results\n"]

    # Summary table
    lines.append("## Summary\n")
    lines.append("| Dataset | Claude | Codex | Winner |")
    lines.append("|---------|--------|-------|--------|")

    claude_total = 0
    codex_total = 0
    claude_count = 0
    codex_count = 0

    for ds_name, agents in sorted(by_dataset.items()):
        claude_score = agents.get("claude")
        codex_score = agents.get("codex")
        c = claude_score.total if claude_score else "-"
        x = codex_score.total if codex_score else "-"

        if claude_score:
            claude_total += claude_score.total
            claude_count += 1
        if codex_score:
            codex_total += codex_score.total
            codex_count += 1

        if claude_score and codex_score:
            if claude_score.total > codex_score.total:
                winner = "Claude"
            elif codex_score.total > claude_score.total:
                winner = "Codex"
            else:
                winner = "Tie"
        else:
            winner = "-"

        lines.append(f"| {ds_name} | {c} | {x} | {winner} |")

    # Averages
    claude_avg = claude_total / claude_count if claude_count else 0
    codex_avg = codex_total / codex_count if codex_count else 0
    lines.append(f"| **Average** | **{claude_avg:.1f}** | **{codex_avg:.1f}** | **{'Claude' if claude_avg > codex_avg else 'Codex' if codex_avg > claude_avg else 'Tie'}** |")
    lines.append("")

    # Dimension breakdown
    lines.append("## Score Breakdown by Dimension\n")
    for dim in RUBRIC_DIMENSIONS:
        lines.append(f"### {dim.description}\n")
        lines.append("| Dataset | Claude | Codex |")
        lines.append("|---------|--------|-------|")
        for ds_name, agents in sorted(by_dataset.items()):
            c = agents.get("claude")
            x = agents.get("codex")
            cs = c.scores.get(dim.name, "-") if c else "-"
            xs = x.scores.get(dim.name, "-") if x else "-"
            lines.append(f"| {ds_name} | {cs} | {xs} |")
        lines.append("")

    # Detailed results
    lines.append("## Detailed Results\n")
    for ds_name, agents in sorted(by_dataset.items()):
        lines.append(f"### {ds_name}\n")
        for agent_name, result in sorted(agents.items()):
            lines.append(f"#### {agent_name.title()} (Total: {result.total})\n")
            lines.append(f"**Summary:** {result.summary}\n")
            if result.modifiers:
                lines.append("**Modifiers:**")
                for m in result.modifiers:
                    sign = "+" if m["value"] > 0 else ""
                    lines.append(f"- {sign}{m['value']}: {m['description']}")
                lines.append("")

    report = "\n".join(lines)
    output_path.write_text(report)
    return report
