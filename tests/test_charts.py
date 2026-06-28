import pandas as pd
import pytest
from eda_artifacts.charts import render_chart_png, validate_vegalite_spec


def _target_distribution_spec():
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Distribution of monthly rent.",
        "mark": "bar",
        "encoding": {
            "x": {"field": "rent_bin", "type": "ordinal", "title": "Rent bin"},
            "y": {"field": "listing_count", "type": "quantitative", "title": "Listings"},
        },
    }


def test_minimal_vegalite_bar_chart_spec_validates():
    validate_vegalite_spec(_target_distribution_spec())


def test_malformed_chart_spec_is_rejected():
    with pytest.raises(ValueError, match="mark"):
        validate_vegalite_spec({"encoding": {"x": {"field": "rent_bin"}}})

    with pytest.raises(ValueError, match="encoding"):
        validate_vegalite_spec({"mark": "bar"})


def test_chart_spec_and_result_data_render_non_empty_png(tmp_path):
    result_path = tmp_path / "target_distribution.parquet"
    render_path = tmp_path / "renders" / "target_distribution.png"
    pd.DataFrame(
        {
            "rent_bin": [500, 750, 1000],
            "listing_count": [12, 35, 18],
        }
    ).to_parquet(result_path, index=False)

    output_path = render_chart_png(
        spec=_target_distribution_spec(),
        result_path=result_path,
        render_path=render_path,
    )

    assert output_path == render_path
    assert render_path.exists()
    assert render_path.stat().st_size > 1000
