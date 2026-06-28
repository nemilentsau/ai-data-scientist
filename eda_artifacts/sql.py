import json
import re
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

_ALLOWED_STARTS = ("select", "with")
_BLOCKED_TOKENS = {
    "alter",
    "attach",
    "copy",
    "create",
    "delete",
    "detach",
    "drop",
    "insert",
    "install",
    "load",
    "pragma",
    "replace",
    "set",
    "truncate",
    "update",
}


def validate_read_only_sql(sql: str) -> None:
    """Reject SQL that is outside the MVP read-only query surface."""
    normalized = _strip_sql_comments(sql).strip().lower()
    if not normalized.startswith(_ALLOWED_STARTS):
        raise ValueError("Only read-only SELECT or WITH queries are allowed.")
    statements = [statement.strip() for statement in normalized.split(";") if statement.strip()]
    if len(statements) != 1:
        raise ValueError("Only one read-only SQL statement is allowed.")
    tokens = set(re.findall(r"[a-z_]+", statements[0]))
    blocked = sorted(tokens.intersection(_BLOCKED_TOKENS))
    if blocked:
        raise ValueError(f"SQL must be read-only; blocked token: {blocked[0]}")


def execute_query_artifact(
    *,
    dataset_path: Path | str,
    sql: str,
    result_path: Path | str,
    summary_path: Path | str,
) -> dict[str, Any]:
    """Execute read-only SQL against a CSV dataset and write result artifacts."""
    validate_read_only_sql(sql)
    source = Path(dataset_path)
    if not source.exists():
        raise FileNotFoundError(source)

    dataset = pd.read_csv(source)
    with duckdb.connect(database=":memory:") as connection:
        connection.register("dataset", dataset)
        result = connection.execute(sql).fetch_df()

    result_destination = Path(result_path)
    result_destination.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(result_destination, index=False)

    summary = _summarize_result(result, result_destination)
    summary_destination = Path(summary_path)
    summary_destination.parent.mkdir(parents=True, exist_ok=True)
    summary_destination.write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def _strip_sql_comments(sql: str) -> str:
    without_line_comments = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    return re.sub(r"/\*.*?\*/", "", without_line_comments, flags=re.DOTALL)


def _summarize_result(result: pd.DataFrame, result_path: Path) -> dict[str, Any]:
    return {
        "result_path": str(result_path),
        "row_count": int(len(result)),
        "column_count": int(len(result.columns)),
        "columns": list(result.columns),
        "preview_rows": result.head(10).to_dict(orient="records"),
    }
