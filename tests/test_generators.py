"""Tests for dataset generators — verify shape, columns, and key statistical properties."""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from datasets.generator import FILENAME_MAP, GENERATORS, NAME_TO_FILENAME, generate_all


# ---------------------------------------------------------------------------
# Every generator returns a DataFrame with > 0 rows and >= 4 columns
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", sorted(GENERATORS))
def test_generator_returns_realistic_dataframe(name):
    df = GENERATORS[name]()
    assert isinstance(df, pd.DataFrame)
    assert len(df) >= 44, f"{name}: only {len(df)} rows — too few for a realistic dataset"
    assert len(df.columns) >= 3, f"{name}: only {len(df.columns)} columns — too toylike"


# ---------------------------------------------------------------------------
# CSV round-trip: save_path writes a readable CSV
# ---------------------------------------------------------------------------
def test_csv_round_trip_with_save_path():
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "test.csv")
        df = GENERATORS["pure_noise"](save_path=path)
        loaded = pd.read_csv(path)
        assert loaded.shape == df.shape


# ---------------------------------------------------------------------------
# generate_all produces exactly 20 CSVs with opaque names
# ---------------------------------------------------------------------------
def test_generate_all_creates_20_csvs_with_opaque_names():
    with tempfile.TemporaryDirectory() as tmp:
        result = generate_all(tmp)
        assert len(result) == 20
        csv_files = {p.name for p in Path(tmp).glob("*.csv")}
        for opaque_name in FILENAME_MAP:
            assert opaque_name in csv_files, f"Missing {opaque_name}"


# ---------------------------------------------------------------------------
# Filename mapping is bijective and covers all generators
# ---------------------------------------------------------------------------
def test_filename_map_covers_all_generators():
    assert set(FILENAME_MAP.values()) == set(GENERATORS.keys())
    assert set(NAME_TO_FILENAME.keys()) == set(GENERATORS.keys())


# ---------------------------------------------------------------------------
# Simpson's Paradox: aggregate vs per-department trend signs differ
# ---------------------------------------------------------------------------
def test_simpsons_paradox_trend_reversal():
    df = GENERATORS["simpsons_paradox"]()
    assert "department" in df.columns
    assert "recovery_score" in df.columns
    assert "severity_index" in df.columns

    overall_recovery = df.groupby("treatment")["recovery_score"].mean()
    assert overall_recovery["B"] > overall_recovery["A"], (
        "Aggregate recovery should incorrectly favor treatment B"
    )

    for dept in df["department"].unique():
        sub = df[df["department"] == dept]
        a = sub[sub["treatment"] == "A"]["recovery_score"].mean()
        b = sub[sub["treatment"] == "B"]["recovery_score"].mean()
        assert a > b, f"Treatment A should have higher recovery in {dept}"


# ---------------------------------------------------------------------------
# Pure Noise: no strong correlations with performance_rating
# ---------------------------------------------------------------------------
def test_pure_noise_no_significant_correlation():
    df = GENERATORS["pure_noise"]()
    numeric = df.select_dtypes(include="number").drop(columns=["employee_id"])
    target = "performance_rating"
    for col in numeric.columns:
        if col == target:
            continue
        r = abs(numeric[col].corr(numeric[target]))
        assert r < 0.15, f"{col} vs {target} correlation {r} too high for noise"


# ---------------------------------------------------------------------------
# Deterministic Linear: voltage = 2 * temperature + 3 exactly
# ---------------------------------------------------------------------------
def test_deterministic_linear_exact_relationship():
    df = GENERATORS["deterministic_linear"]()
    residuals = df["voltage_mv"] - (2 * df["temperature_c"] + 3)
    assert np.allclose(residuals, 0, atol=1e-10)


# ---------------------------------------------------------------------------
# Anscombe's Quartet: 4 batches with near-identical dosage/response stats
# ---------------------------------------------------------------------------
def test_anscombes_quartet_identical_summary_stats():
    df = GENERATORS["anscombes_quartet"]()
    batches = [df[df["batch"] == b] for b in df["batch"].unique()]
    means_x = [s["dosage_mg"].mean() for s in batches]
    means_y = [s["response"].mean() for s in batches]
    assert np.allclose(means_x, means_x[0], atol=0.5)
    assert np.allclose(means_y, means_y[0], atol=0.5)


# ---------------------------------------------------------------------------
# Multicollinearity: sq_ft, num_rooms, lot_size highly correlated
# ---------------------------------------------------------------------------
def test_multicollinearity_high_correlation():
    df = GENERATORS["multicollinearity"]()
    assert df["sq_ft"].corr(df["num_rooms"]) > 0.85
    assert df["sq_ft"].corr(df["lot_size_acres"]) > 0.85


# ---------------------------------------------------------------------------
# Heteroscedasticity: revenue variance grows with ad_spend
# ---------------------------------------------------------------------------
def test_heteroscedasticity_growing_variance():
    df = GENERATORS["heteroscedasticity"]()
    slope = np.polyfit(df["ad_spend_usd"], df["revenue_usd"], 1)
    residuals = df["revenue_usd"] - np.polyval(slope, df["ad_spend_usd"])
    low = residuals[df["ad_spend_usd"] < df["ad_spend_usd"].quantile(0.25)]
    high = residuals[df["ad_spend_usd"] > df["ad_spend_usd"].quantile(0.75)]
    assert high.std() > low.std() * 2


# ---------------------------------------------------------------------------
# Outlier-Dominated: ~5% extreme order totals
# ---------------------------------------------------------------------------
def test_outlier_dominated_has_extreme_values():
    df = GENERATORS["outlier_dominated"]()
    expected_total = df["items_qty"] * df["unit_price_usd"] + df["shipping_usd"]
    residuals = (df["order_total_usd"] - expected_total).abs()
    n_extreme = (residuals > 3000).sum()
    assert 30 < n_extreme < 100, f"Expected ~60 outliers, got {n_extreme}"


# ---------------------------------------------------------------------------
# MNAR: high-income respondents skip income question
# ---------------------------------------------------------------------------
def test_mnar_missing_values_biased():
    df = GENERATORS["mnar"]()
    assert df["reported_annual_income"].isna().sum() > 0
    # Rows with missing income should have higher education (proxy for income)
    has_income = df.dropna(subset=["reported_annual_income"])
    missing_income = df[df["reported_annual_income"].isna()]
    assert missing_income["education_years"].mean() > has_income["education_years"].mean()


# ---------------------------------------------------------------------------
# Class Imbalance: ~5% fraud
# ---------------------------------------------------------------------------
def test_class_imbalance_ratio():
    df = GENERATORS["class_imbalance"]()
    ratio = df["is_fraud"].mean()
    assert 0.03 < ratio < 0.07, f"Fraud ratio {ratio} not near 5%"


# ---------------------------------------------------------------------------
# Quadratic: fuel_consumption ~ rpm^2
# ---------------------------------------------------------------------------
def test_quadratic_nonlinear_relationship():
    df = GENERATORS["quadratic"]()
    x, y = df["engine_rpm"], df["fuel_consumption_lph"]
    p1 = np.polyfit(x, y, 1)
    p2 = np.polyfit(x, y, 2)
    ss_tot = ((y - y.mean()) ** 2).sum()
    r2_lin = 1 - ((y - np.polyval(p1, x)) ** 2).sum() / ss_tot
    r2_quad = 1 - ((y - np.polyval(p2, x)) ** 2).sum() / ss_tot
    assert r2_quad > r2_lin + 0.02, "Quadratic should fit better"
    assert r2_quad > 0.98, "Quadratic R² should be very high"


# ---------------------------------------------------------------------------
# Concept Drift: temperature→defect relationship inverts at midpoint
# ---------------------------------------------------------------------------
def test_concept_drift_two_regimes():
    df = GENERATORS["concept_drift"]()
    half = len(df) // 2
    first = df.iloc[:half]
    second = df.iloc[half:]
    corr_1 = first["temperature_c"].corr(first["defect_rate"])
    corr_2 = second["temperature_c"].corr(second["defect_rate"])
    assert corr_1 > 0, f"First half should have positive temp-defect corr, got {corr_1}"
    assert corr_2 < 0, f"Second half should have negative temp-defect corr, got {corr_2}"


# ---------------------------------------------------------------------------
# Reproducibility: same seed → same data
# ---------------------------------------------------------------------------
def test_generators_are_deterministic():
    df1 = GENERATORS["pure_noise"]()
    df2 = GENERATORS["pure_noise"]()
    pd.testing.assert_frame_equal(df1, df2)
