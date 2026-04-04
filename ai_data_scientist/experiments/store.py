"""SQLite-backed catalog for imported benchmark experiment metadata."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


def catalog_db_path(experiments_dir: Path) -> Path:
    return experiments_dir / "catalog.sqlite"


def persist_experiment(
    *,
    db_path: Path,
    experiment_record: dict[str, Any],
    config_records: list[dict[str, Any]],
    case_records: list[dict[str, Any]],
    workflow_records: list[dict[str, Any]],
    agent_records: list[dict[str, Any]],
    artifact_records: list[dict[str, Any]],
    evaluation_records: list[dict[str, Any]],
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        _initialize_schema(conn)
        _delete_existing_experiment(conn, experiment_record["experiment_id"])

        conn.execute(
            """
            INSERT INTO experiments (
                experiment_id,
                title,
                description,
                source_kind,
                created_at,
                updated_at,
                summary_json,
                payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                experiment_record["experiment_id"],
                experiment_record["title"],
                experiment_record["description"],
                experiment_record["source_kind"],
                experiment_record["created_at"],
                experiment_record["updated_at"],
                _dump_json(experiment_record["summary"]),
                _dump_json(experiment_record),
            ),
        )

        _insert_many(
            conn,
            """
            INSERT INTO config_snapshots (
                config_snapshot_id,
                experiment_id,
                config_name,
                description,
                harness,
                source_path,
                payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    record["config_snapshot_id"],
                    record["experiment_id"],
                    record["config_name"],
                    record.get("description"),
                    record.get("harness"),
                    record.get("source_path"),
                    _dump_json(record),
                )
                for record in config_records
            ],
        )
        _insert_many(
            conn,
            """
            INSERT INTO cases (
                case_id,
                experiment_id,
                dataset,
                config_name,
                config_snapshot_id,
                latest_workflow_run_id,
                evaluation_id,
                payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    record["case_id"],
                    record["experiment_id"],
                    record["dataset"],
                    record["config_name"],
                    record["config_snapshot_id"],
                    record["latest_workflow_run_id"],
                    record.get("evaluation_id"),
                    _dump_json(record),
                )
                for record in case_records
            ],
        )
        _insert_many(
            conn,
            """
            INSERT INTO workflow_runs (
                workflow_run_id,
                experiment_id,
                case_id,
                attempt,
                status,
                source_kind,
                source_path,
                config_snapshot_id,
                evaluation_id,
                payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    record["workflow_run_id"],
                    record["experiment_id"],
                    record["case_id"],
                    record["attempt"],
                    record["status"],
                    record["source_kind"],
                    record["source_path"],
                    record["config_snapshot_id"],
                    record.get("evaluation_id"),
                    _dump_json(record),
                )
                for record in workflow_records
            ],
        )
        _insert_many(
            conn,
            """
            INSERT INTO agent_runs (
                agent_run_id,
                experiment_id,
                case_id,
                workflow_run_id,
                config_snapshot_id,
                role,
                model,
                status,
                source_kind,
                payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    record["agent_run_id"],
                    record["experiment_id"],
                    record["case_id"],
                    record["workflow_run_id"],
                    record["config_snapshot_id"],
                    record["role"],
                    record.get("model"),
                    record["status"],
                    record["source_kind"],
                    _dump_json(record),
                )
                for record in agent_records
            ],
        )
        _insert_many(
            conn,
            """
            INSERT INTO artifacts (
                artifact_id,
                experiment_id,
                config_snapshot_id,
                case_id,
                workflow_run_id,
                agent_run_id,
                type,
                role,
                media_type,
                path,
                size_bytes,
                created_at,
                source_kind,
                payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    record["artifact_id"],
                    record["experiment_id"],
                    record["config_snapshot_id"],
                    record.get("case_id"),
                    record.get("workflow_run_id"),
                    record.get("agent_run_id"),
                    record["type"],
                    record["role"],
                    record["media_type"],
                    record["path"],
                    record["size_bytes"],
                    record["created_at"],
                    record["source_kind"],
                    _dump_json(record),
                )
                for record in artifact_records
            ],
        )
        _insert_many(
            conn,
            """
            INSERT INTO evaluations (
                evaluation_id,
                experiment_id,
                case_id,
                workflow_run_id,
                source_path,
                verdict,
                run_status,
                core_insight_pass,
                required_coverage,
                supporting_coverage,
                summary,
                fatal_errors_json,
                payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    record["evaluation_id"],
                    record["experiment_id"],
                    record["case_id"],
                    record["workflow_run_id"],
                    record["source_path"],
                    record.get("verdict"),
                    record.get("run_status"),
                    _bool_to_int(record.get("core_insight_pass")),
                    record.get("required_coverage"),
                    record.get("supporting_coverage"),
                    record.get("summary"),
                    _dump_json(record.get("fatal_errors", [])),
                    _dump_json(record),
                )
                for record in evaluation_records
            ],
        )


def load_experiment_manifest(db_path: Path, experiment_id: str) -> dict[str, Any] | None:
    with sqlite3.connect(db_path) as conn:
        experiment_record = _load_payload_record(
            conn,
            "SELECT payload_json FROM experiments WHERE experiment_id = ?",
            (experiment_id,),
        )
        if experiment_record is None:
            return None

        config_records = _load_payload_records(
            conn,
            """
            SELECT payload_json FROM config_snapshots
            WHERE experiment_id = ?
            ORDER BY config_name
            """,
            (experiment_id,),
        )
        case_records = _load_payload_records(
            conn,
            """
            SELECT payload_json FROM cases
            WHERE experiment_id = ?
            ORDER BY dataset, config_name
            """,
            (experiment_id,),
        )
        workflow_records = _load_payload_records(
            conn,
            """
            SELECT payload_json FROM workflow_runs
            WHERE experiment_id = ?
            ORDER BY case_id, attempt
            """,
            (experiment_id,),
        )
        agent_records = _load_payload_records(
            conn,
            """
            SELECT payload_json FROM agent_runs
            WHERE experiment_id = ?
            ORDER BY case_id, agent_run_id
            """,
            (experiment_id,),
        )
        artifact_records = _load_payload_records(
            conn,
            """
            SELECT payload_json FROM artifacts
            WHERE experiment_id = ?
            ORDER BY path
            """,
            (experiment_id,),
        )
        evaluation_records = _load_payload_records(
            conn,
            """
            SELECT payload_json FROM evaluations
            WHERE experiment_id = ?
            ORDER BY case_id
            """,
            (experiment_id,),
        )

    evaluations_by_case = {
        evaluation["case_id"]: evaluation for evaluation in evaluation_records
    }
    case_summaries = [
        {
            "case_id": case["case_id"],
            "dataset": case["dataset"],
            "config_name": case["config_name"],
            "workflow_run_id": case["latest_workflow_run_id"],
            "evaluation_id": case["evaluation_id"],
            "verdict": (
                evaluations_by_case[case["case_id"]]["verdict"]
                if case["evaluation_id"] is not None
                else None
            ),
            "artifact_count": len(case["artifact_ids"]),
        }
        for case in case_records
    ]

    return {
        "experiment": experiment_record,
        "config_snapshots": config_records,
        "cases": case_summaries,
        "workflow_runs": workflow_records,
        "agent_runs": agent_records,
        "artifacts": artifact_records,
        "evaluations": evaluation_records,
    }


def load_experiments_index(db_path: Path) -> list[dict[str, Any]]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT experiment_id, title, source_kind, created_at, updated_at, summary_json
            FROM experiments
            ORDER BY created_at DESC, experiment_id ASC
            """
        ).fetchall()

    return [
        {
            "experiment_id": row[0],
            "title": row[1],
            "source_kind": row[2],
            "created_at": row[3],
            "updated_at": row[4],
            "summary": json.loads(row[5]),
        }
        for row in rows
    ]


def _initialize_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS experiments (
            experiment_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            source_kind TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            summary_json TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS config_snapshots (
            config_snapshot_id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            config_name TEXT NOT NULL,
            description TEXT,
            harness TEXT,
            source_path TEXT,
            payload_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS cases (
            case_id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            dataset TEXT NOT NULL,
            config_name TEXT NOT NULL,
            config_snapshot_id TEXT NOT NULL,
            latest_workflow_run_id TEXT NOT NULL,
            evaluation_id TEXT,
            payload_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS workflow_runs (
            workflow_run_id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            case_id TEXT NOT NULL,
            attempt INTEGER NOT NULL,
            status TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            source_path TEXT NOT NULL,
            config_snapshot_id TEXT NOT NULL,
            evaluation_id TEXT,
            payload_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agent_runs (
            agent_run_id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            case_id TEXT NOT NULL,
            workflow_run_id TEXT NOT NULL,
            config_snapshot_id TEXT NOT NULL,
            role TEXT NOT NULL,
            model TEXT,
            status TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS artifacts (
            artifact_id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            config_snapshot_id TEXT NOT NULL,
            case_id TEXT,
            workflow_run_id TEXT,
            agent_run_id TEXT,
            type TEXT NOT NULL,
            role TEXT NOT NULL,
            media_type TEXT NOT NULL,
            path TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS evaluations (
            evaluation_id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            case_id TEXT NOT NULL,
            workflow_run_id TEXT NOT NULL,
            source_path TEXT NOT NULL,
            verdict TEXT,
            run_status TEXT,
            core_insight_pass INTEGER,
            required_coverage REAL,
            supporting_coverage REAL,
            summary TEXT,
            fatal_errors_json TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_config_snapshots_experiment
            ON config_snapshots (experiment_id);
        CREATE INDEX IF NOT EXISTS idx_cases_experiment
            ON cases (experiment_id);
        CREATE INDEX IF NOT EXISTS idx_workflow_runs_experiment
            ON workflow_runs (experiment_id);
        CREATE INDEX IF NOT EXISTS idx_agent_runs_experiment
            ON agent_runs (experiment_id);
        CREATE INDEX IF NOT EXISTS idx_artifacts_experiment
            ON artifacts (experiment_id);
        CREATE INDEX IF NOT EXISTS idx_artifacts_case
            ON artifacts (case_id);
        CREATE INDEX IF NOT EXISTS idx_evaluations_experiment
            ON evaluations (experiment_id);
        """
    )


def _delete_existing_experiment(conn: sqlite3.Connection, experiment_id: str) -> None:
    for table in (
        "artifacts",
        "agent_runs",
        "workflow_runs",
        "cases",
        "config_snapshots",
        "evaluations",
        "experiments",
    ):
        conn.execute(f"DELETE FROM {table} WHERE experiment_id = ?", (experiment_id,))


def _insert_many(
    conn: sqlite3.Connection,
    statement: str,
    rows: list[tuple[Any, ...]],
) -> None:
    if not rows:
        return
    conn.executemany(statement, rows)


def _load_payload_record(
    conn: sqlite3.Connection,
    statement: str,
    params: tuple[Any, ...],
) -> dict[str, Any] | None:
    row = conn.execute(statement, params).fetchone()
    if row is None:
        return None
    return json.loads(row[0])


def _load_payload_records(
    conn: sqlite3.Connection,
    statement: str,
    params: tuple[Any, ...],
) -> list[dict[str, Any]]:
    return [json.loads(row[0]) for row in conn.execute(statement, params).fetchall()]


def _dump_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True)


def _bool_to_int(value: bool | None) -> int | None:
    if value is None:
        return None
    return int(value)
