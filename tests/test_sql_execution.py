import json

import pandas as pd
import pytest
from eda_artifacts.datasets import generate_multimodal_dataset
from eda_artifacts.sql import execute_query_artifact, validate_read_only_sql


def test_read_only_sql_accepts_select_and_cte_queries():
    validate_read_only_sql("SELECT monthly_rent_usd FROM dataset")
    validate_read_only_sql(
        """
        WITH rent_bins AS (
          SELECT monthly_rent_usd FROM dataset
        )
        SELECT COUNT(*) AS row_count FROM rent_bins
        """
    )


def test_read_only_sql_rejects_mutation_statements():
    with pytest.raises(ValueError, match="read-only"):
        validate_read_only_sql("DROP TABLE dataset")

    with pytest.raises(ValueError, match="read-only"):
        validate_read_only_sql("SELECT * FROM dataset; DELETE FROM dataset")


def test_read_only_sql_rejects_file_reader_functions():
    with pytest.raises(ValueError, match="blocked token: read_csv_auto"):
        validate_read_only_sql("SELECT * FROM read_csv_auto('dataset/dataset.csv')")


def test_query_execution_writes_parquet_and_summary_artifacts(tmp_path):
    dataset_path = tmp_path / "dataset.csv"
    result_path = tmp_path / "results" / "target_distribution.parquet"
    summary_path = tmp_path / "results" / "target_distribution.summary.json"
    generate_multimodal_dataset(dataset_path)

    query = """
    SELECT
      floor(monthly_rent_usd / 250) * 250 AS rent_bin,
      count(*) AS listing_count
    FROM dataset
    GROUP BY 1
    ORDER BY 1
    """

    summary = execute_query_artifact(
        dataset_path=dataset_path,
        sql=query,
        result_path=result_path,
        summary_path=summary_path,
    )

    assert result_path.exists()
    assert summary_path.exists()
    result = pd.read_parquet(result_path)
    assert list(result.columns) == ["rent_bin", "listing_count"]
    assert result["listing_count"].sum() == 1200
    assert summary["row_count"] == len(result)
    assert summary["columns"] == ["rent_bin", "listing_count"]
    assert json.loads(summary_path.read_text()) == summary
