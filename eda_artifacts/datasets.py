from pathlib import Path

import numpy as np
import pandas as pd


def generate_multimodal_dataset(save_path: Path | str | None = None) -> pd.DataFrame:
    """Generate the rental-pricing mixture dataset used by the MVP."""
    rng = np.random.RandomState(42)
    row_count = 1200
    component = rng.choice(3, row_count, p=[0.35, 0.4, 0.25])
    means = [800, 1600, 3200]
    stds = [150, 300, 500]
    rent = (
        np.array([rng.normal(means[value], stds[value]) for value in component])
        .clip(300)
        .round(0)
        .astype(int)
    )
    sq_ft = (
        rent * rng.uniform(0.5, 0.9, row_count) + rng.normal(0, 50, row_count)
    ).clip(200).round(0).astype(int)
    bedrooms = np.where(
        rent < 1200,
        rng.choice([0, 1], row_count),
        np.where(
            rent < 2500,
            rng.choice([1, 2, 3], row_count),
            rng.choice([2, 3, 4], row_count),
        ),
    )
    distance_to_center_km = (
        rng.exponential(5, row_count) + rng.normal(0, 1, row_count)
    ).clip(0.5).round(1)

    data = pd.DataFrame(
        {
            "listing_id": range(1, row_count + 1),
            "sq_ft": sq_ft,
            "bedrooms": bedrooms,
            "bathrooms": (bedrooms * 0.6 + rng.choice([0, 1], row_count))
            .clip(1)
            .astype(int),
            "distance_to_center_km": distance_to_center_km,
            "year_built": rng.randint(1920, 2024, row_count),
            "has_parking": rng.choice([0, 1], row_count),
            "pet_friendly": rng.choice([0, 1], row_count, p=[0.6, 0.4]),
            "monthly_rent_usd": rent,
        }
    )
    if save_path is not None:
        destination = Path(save_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        data.to_csv(destination, index=False)
    return data

