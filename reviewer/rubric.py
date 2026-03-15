from dataclasses import dataclass, field

@dataclass
class Dimension:
    name: str
    description: str
    fail_description: str      # score 0
    adequate_description: str  # score 3
    excellent_description: str # score 5
    weight: float = 1.0

RUBRIC_DIMENSIONS = [
    Dimension(
        name="data_loading_inspection",
        description="Data Loading & Inspection",
        fail_description="Didn't load or crashed",
        adequate_description="Loaded, printed head/shape",
        excellent_description="Checked dtypes, nulls, duplicates, distributions",
    ),
    Dimension(
        name="eda_quality",
        description="EDA Quality",
        fail_description="No exploration",
        adequate_description="Basic summary stats",
        excellent_description="Visualizations + stats + narrative",
    ),
    Dimension(
        name="pattern_identification",
        description="Pattern Identification",
        fail_description="Missed the key pattern entirely",
        adequate_description="Partially identified",
        excellent_description="Correctly identified the core pattern + nuances",
    ),
    Dimension(
        name="method_selection",
        description="Method Selection",
        fail_description="Wrong or no method",
        adequate_description="Reasonable but suboptimal",
        excellent_description="Appropriate method with justification",
    ),
    Dimension(
        name="assumption_checking",
        description="Assumption Checking",
        fail_description="No checks",
        adequate_description="Mentioned assumptions",
        excellent_description="Formally tested assumptions, adapted approach",
    ),
    Dimension(
        name="code_quality",
        description="Code Quality",
        fail_description="Broken / doesn't run",
        adequate_description="Runs but messy",
        excellent_description="Clean, reproducible, well-structured",
    ),
    Dimension(
        name="conclusions",
        description="Conclusions",
        fail_description="Wrong or absent",
        adequate_description="Partially correct",
        excellent_description="Correct, nuanced, acknowledges limitations",
    ),
]

@dataclass
class Modifier:
    description: str
    value: int  # +1 or -1

BONUS_MODIFIERS = [
    Modifier("Agent proactively explored something not in the prompt", +1),
    Modifier("Agent caught a subtle secondary pattern", +1),
    Modifier("Agent produced publication-quality visualizations", +1),
]

PENALTY_MODIFIERS = [
    Modifier("Agent hallucinated a pattern that doesn't exist", -1),
    Modifier("Agent used a method that violates data assumptions without noting it", -1),
    Modifier("Agent's code crashes or produces wrong output", -1),
]

# Critical miss: if the agent fails to identify the core pattern the dataset was
# designed to test (pattern_identification <= 3), apply a heavy penalty and zero
# out any bonuses.  Without this, an agent that does excellent technical work but
# misses the entire point can still score 33/35.
CRITICAL_MISS_THRESHOLD = 3      # pattern_identification score at or below this
CRITICAL_MISS_PENALTY = -5        # flat penalty applied on critical miss
CRITICAL_MISS_ZEROES_BONUSES = True  # bonuses are wiped when core pattern missed

MAX_DIMENSION_SCORE = 5 * len(RUBRIC_DIMENSIONS)  # 35
MAX_MODIFIER = 3
MIN_MODIFIER = -8  # allow room for critical miss penalty

def format_rubric_for_prompt() -> str:
    """Format the rubric as text for inclusion in the reviewer LLM prompt."""
    lines = ["## Scoring Rubric (7 dimensions, 0-5 each, max 35)\n"]
    for dim in RUBRIC_DIMENSIONS:
        lines.append(f"### {dim.description}")
        lines.append(f"- 0 (Fail): {dim.fail_description}")
        lines.append(f"- 3 (Adequate): {dim.adequate_description}")
        lines.append(f"- 5 (Excellent): {dim.excellent_description}")
        lines.append("")
    lines.append("## Bonus Modifiers (+1 each, max +3)")
    for m in BONUS_MODIFIERS:
        lines.append(f"- +1: {m.description}")
    lines.append("\n## Penalty Modifiers (-1 each, max -3)")
    for m in PENALTY_MODIFIERS:
        lines.append(f"- -1: {m.description}")
    lines.append("\n## Critical Miss Rule")
    lines.append(
        "Each dataset is designed to test ONE core statistical pattern (listed in "
        "the Ground Truth section). If the agent fails to explicitly identify and "
        "discuss this pattern — even if the rest of the analysis is technically "
        "excellent — **pattern_identification must score ≤ 3** and "
        "**conclusions must score ≤ 3**. Thorough execution that misses the point "
        "is NOT a high-scoring analysis. When pattern_identification ≤ 3, all "
        "bonus modifiers are forfeited and a -5 critical miss penalty is applied."
    )
    return "\n".join(lines)
