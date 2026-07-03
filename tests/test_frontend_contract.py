import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_backend_fake_run_matches_frontend_contract(tmp_path: Path) -> None:
    run_root = tmp_path / "runs" / "eda-artifacts"
    run_id = "frontend-contract"
    run_dir = run_root / "multimodal" / run_id

    subprocess.run(
        [
            sys.executable,
            "-m",
            "eda_artifacts.cli",
            "run",
            "--adapter",
            "fake",
            "--run-root",
            str(run_root),
            "--run-id",
            run_id,
            "--question",
            "Assess whether monthly_rent_usd has a simple distribution.",
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )

    env = {
        **os.environ,
        "EDA_RUN_DIR": str(run_dir),
    }
    subprocess.run(
        ["npm", "--prefix", "frontend", "test", "--", "src/backendContract.test.ts"],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
    )
