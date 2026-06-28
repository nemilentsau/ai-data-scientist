import copy
from pathlib import Path
from typing import Any

import pandas as pd
import vl_convert as vlc


def validate_vegalite_spec(spec: dict[str, Any]) -> None:
    """Validate the small Vega-Lite surface required by the MVP."""
    if not isinstance(spec, dict):
        raise ValueError("Vega-Lite spec must be a JSON object.")
    if "mark" not in spec:
        raise ValueError("Vega-Lite spec must include mark.")
    if "encoding" not in spec:
        raise ValueError("Vega-Lite spec must include encoding.")
    encoding = spec["encoding"]
    if not isinstance(encoding, dict) or not encoding:
        raise ValueError("Vega-Lite spec encoding must be a non-empty object.")


def render_chart_png(
    *,
    spec: dict[str, Any],
    result_path: Path | str,
    render_path: Path | str,
) -> Path:
    """Render a Vega-Lite spec with materialized result data to a PNG review artifact."""
    validate_vegalite_spec(spec)
    source = Path(result_path)
    if not source.exists():
        raise FileNotFoundError(source)

    result = pd.read_parquet(source)
    render_spec = copy.deepcopy(spec)
    render_spec["data"] = {"values": result.to_dict(orient="records")}

    destination = Path(render_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(vlc.vegalite_to_png(render_spec))
    return destination
