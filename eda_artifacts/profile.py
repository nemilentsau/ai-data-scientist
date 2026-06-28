import json
from pathlib import Path
from typing import Any

import pandas as pd


def profile_dataset(dataset_path: Path | str, profile_path: Path | str) -> dict[str, Any]:
    """Write a compact structural JSON profile for a CSV dataset."""
    source = Path(dataset_path)
    if not source.exists():
        raise FileNotFoundError(source)

    frame = pd.read_csv(source)
    profile = {
        "dataset_path": str(source),
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "columns": {
            column: _profile_column(frame[column])
            for column in frame.columns
        },
        "sample_rows": frame.head(5).to_dict(orient="records"),
    }

    destination = Path(profile_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(profile, indent=2, sort_keys=True))
    return profile


def _profile_column(series: pd.Series) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "dtype": str(series.dtype),
        "null_count": int(series.isna().sum()),
    }
    if pd.api.types.is_numeric_dtype(series):
        numeric = series.dropna()
        payload["numeric"] = {
            "min": _json_number(numeric.min()),
            "max": _json_number(numeric.max()),
            "mean": _json_number(numeric.mean()),
            "median": _json_number(numeric.median()),
        }
    else:
        payload["unique_count"] = int(series.nunique(dropna=True))
    return payload


def _json_number(value: Any) -> float | int:
    if pd.isna(value):
        return 0
    if float(value).is_integer():
        return int(value)
    return float(value)
