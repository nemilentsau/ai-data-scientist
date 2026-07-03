import json

from eda_artifacts.datasets import generate_multimodal_dataset
from eda_artifacts.profile import profile_dataset


def test_multimodal_dataset_generation_is_deterministic_and_writes_csv(tmp_path):
    first_path = tmp_path / "first.csv"
    second_path = tmp_path / "second.csv"

    first = generate_multimodal_dataset(first_path)
    second = generate_multimodal_dataset(second_path)

    assert first_path.exists()
    assert second_path.exists()
    assert first.shape == (1200, 9)
    assert first.equals(second)
    assert list(first.columns) == [
        "listing_id",
        "sq_ft",
        "bedrooms",
        "bathrooms",
        "distance_to_center_km",
        "year_built",
        "has_parking",
        "pet_friendly",
        "monthly_rent_usd",
    ]
    assert set(first["monthly_rent_usd"].quantile([0.1, 0.5, 0.9]).index) == {0.1, 0.5, 0.9}


def test_profile_dataset_writes_structural_json(tmp_path):
    dataset_path = tmp_path / "dataset.csv"
    profile_path = tmp_path / "profile.json"
    generate_multimodal_dataset(dataset_path)

    profile = profile_dataset(dataset_path, profile_path)

    assert profile_path.exists()
    assert profile == json.loads(profile_path.read_text())
    assert profile["row_count"] == 1200
    assert profile["column_count"] == 9
    assert profile["columns"]["monthly_rent_usd"]["dtype"] in {"int64", "int32"}
    assert profile["columns"]["monthly_rent_usd"]["null_count"] == 0
    assert profile["columns"]["monthly_rent_usd"]["numeric"]["min"] >= 300
    assert profile["columns"]["monthly_rent_usd"]["numeric"]["max"] > 3000
    assert len(profile["sample_rows"]) == 5


def test_profile_dataset_rejects_missing_dataset(tmp_path):
    missing_path = tmp_path / "missing.csv"

    try:
        profile_dataset(missing_path, tmp_path / "profile.json")
    except FileNotFoundError as exc:
        assert str(missing_path) in str(exc)
    else:
        raise AssertionError("profile_dataset should reject a missing dataset path")
