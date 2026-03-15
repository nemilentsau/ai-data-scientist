import json
import os
from dataclasses import dataclass
from pathlib import Path
from anthropic import Anthropic
from .rubric import format_rubric_for_prompt, RUBRIC_DIMENSIONS, MAX_MODIFIER, MIN_MODIFIER

@dataclass
class ScoreResult:
    dataset_name: str
    agent: str
    scores: dict[str, int]          # dimension_name -> score 0-5
    modifiers: list[dict]           # [{"description": ..., "value": +/-1}]
    total: int
    summary: str
    raw_response: str

def build_reviewer_prompt(
    dataset_metadata,
    analysis_report: str,
    session_transcript: str,
) -> str:
    rubric_text = format_rubric_for_prompt()

    return f"""You are a senior data scientist reviewing an analysis. Score it against the rubric below.

## Ground Truth for This Dataset
**Key Pattern:** {dataset_metadata.key_pattern}

**Expected Findings:**
{chr(10).join(f'- {f}' for f in dataset_metadata.expected_findings)}

**Common Traps (penalize if present):**
{chr(10).join(f'- {t}' for t in dataset_metadata.traps)}

{rubric_text}

---

## Agent's Analysis Report
{analysis_report}

---

## Agent's Session Transcript (abbreviated)
{session_transcript[:20000]}

---

## Instructions
Score each of the 7 dimensions from 0 to 5 with a brief justification.
Apply any applicable bonus or penalty modifiers (max +3, min -3 total).
Be fair but rigorous.

Return ONLY valid JSON in this exact format:
{{
  "scores": {{
    "data_loading_inspection": {{"score": N, "justification": "..."}},
    "eda_quality": {{"score": N, "justification": "..."}},
    "pattern_identification": {{"score": N, "justification": "..."}},
    "method_selection": {{"score": N, "justification": "..."}},
    "assumption_checking": {{"score": N, "justification": "..."}},
    "code_quality": {{"score": N, "justification": "..."}},
    "conclusions": {{"score": N, "justification": "..."}}
  }},
  "modifiers": [
    {{"description": "...", "value": +1 or -1}}
  ],
  "total": N,
  "summary": "One paragraph overall assessment"
}}"""


def score_analysis(
    dataset_name: str,
    agent: str,
    dataset_metadata,
    results_dir: Path,
) -> ScoreResult:
    """Score an agent's analysis of a dataset."""
    # Read agent outputs
    report_path = results_dir / "analysis_report.md"
    analysis_report = report_path.read_text() if report_path.exists() else "[No analysis report found]"

    # Read session transcript
    if agent == "claude":
        transcript_path = results_dir / "session.json"
    else:
        transcript_path = results_dir / "session.log"
    session_transcript = transcript_path.read_text() if transcript_path.exists() else "[No session transcript found]"

    prompt = build_reviewer_prompt(dataset_metadata, analysis_report, session_transcript)

    client = Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text

    # Parse JSON from response
    # Try to extract JSON from markdown code blocks if present
    json_str = raw
    if "```json" in raw:
        json_str = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        json_str = raw.split("```")[1].split("```")[0]

    data = json.loads(json_str.strip())

    # Extract scores
    scores = {k: v["score"] for k, v in data["scores"].items()}

    # Clamp modifier total
    modifier_total = sum(m["value"] for m in data.get("modifiers", []))
    modifier_total = max(MIN_MODIFIER, min(MAX_MODIFIER, modifier_total))

    return ScoreResult(
        dataset_name=dataset_name,
        agent=agent,
        scores=scores,
        modifiers=data.get("modifiers", []),
        total=data["total"],
        summary=data["summary"],
        raw_response=raw,
    )
