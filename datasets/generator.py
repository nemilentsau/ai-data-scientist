"""
Dataset generators for AI Data Scientist benchmark.

Each generator produces a realistic-looking DataFrame with plausible column
names, extra noise columns, and enough rows to feel like real data.  Nothing
in the column names or shape should telegraph the intended finding.
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# 1. Simpson's Paradox
# ---------------------------------------------------------------------------
def generate_simpsons_paradox(save_path=None):
    """Hospital treatment data where overall success rate hides per-department reversal."""
    rng = np.random.RandomState(42)
    rows = []
    departments = ["Cardiology", "Neurology", "Orthopedics"]
    treatment_a_probs = [0.10, 0.45, 0.90]
    # Treatment A is better within each department, but it is concentrated in
    # the worse departments overall, so the aggregate comparison reverses.
    for dept_i, dept in enumerate(departments):
        n = 400
        severity = rng.normal(3 + dept_i * 2, 1, n).clip(1, 10)
        treatment = rng.choice(
            ["A", "B"],
            n,
            p=[treatment_a_probs[dept_i], 1 - treatment_a_probs[dept_i]],
        )
        base = 80 - 3 * severity + rng.normal(0, 5, n)
        effect = np.where(treatment == "A", 5, 0)
        recovery_score = (base + effect).clip(0, 100)
        age = (40 + severity * 3 + rng.normal(0, 5, n)).clip(20, 90).astype(int)
        length_of_stay = 5 + severity * 2 + rng.normal(0, 2, n) - np.where(treatment == "A", 1.5, 0)
        for i in range(n):
            rows.append({
                "department": dept,
                "age": age[i],
                "severity_index": round(severity[i], 2),
                "treatment": treatment[i],
                "length_of_stay_days": int(max(1, length_of_stay[i])),
                "recovery_score": round(recovery_score[i], 1),
                "readmitted": int(rng.random() < 0.1),
            })
    df = pd.DataFrame(rows)
    df = df.sample(frac=1, random_state=rng).reset_index(drop=True)
    df.insert(0, "patient_id", range(1, len(df) + 1))
    if save_path:
        df.to_csv(save_path, index=False)
    return df


# ---------------------------------------------------------------------------
# 2. Pure Noise
# ---------------------------------------------------------------------------
def generate_pure_noise(save_path=None):
    """Employee performance data — every column is independent noise."""
    rng = np.random.RandomState(42)
    n = 800
    df = pd.DataFrame({
        "employee_id": range(1, n + 1),
        "years_experience": rng.uniform(0, 30, n).round(1),
        "training_hours": rng.normal(40, 15, n).clip(0).round(1),
        "team_size": rng.randint(3, 25, n),
        "projects_completed": rng.poisson(8, n),
        "satisfaction_score": rng.uniform(1, 10, n).round(2),
        "commute_minutes": rng.exponential(25, n).clip(5, 120).round(0).astype(int),
        "performance_rating": rng.normal(50, 10, n).clip(0, 100).round(1),
        "salary_band": rng.choice(["L1", "L2", "L3", "L4", "L5"], n),
        "remote_pct": rng.choice([0, 25, 50, 75, 100], n),
    })
    if save_path:
        df.to_csv(save_path, index=False)
    return df


# ---------------------------------------------------------------------------
# 3. Deterministic Linear
# ---------------------------------------------------------------------------
def generate_deterministic_linear(save_path=None):
    """Sensor calibration data — voltage is an exact linear function of temperature."""
    rng = np.random.RandomState(42)
    n = 500
    temperature = rng.uniform(-20, 80, n).round(2)
    voltage = 2 * temperature + 3  # exact relationship
    # Add noise columns that are irrelevant
    humidity = rng.normal(50, 15, n).clip(5, 100).round(1)
    pressure_hpa = rng.normal(1013, 10, n).round(1)
    sensor_id = rng.choice(["S-001", "S-002", "S-003", "S-004"], n)
    timestamp = pd.date_range("2024-01-01", periods=n, freq="h")
    df = pd.DataFrame({
        "timestamp": timestamp,
        "sensor_id": sensor_id,
        "temperature_c": temperature,
        "humidity_pct": humidity,
        "pressure_hpa": pressure_hpa,
        "voltage_mv": voltage,
    })
    if save_path:
        df.to_csv(save_path, index=False)
    return df


# ---------------------------------------------------------------------------
# 4. Anscombe's Quartet
# ---------------------------------------------------------------------------
def generate_anscombes_quartet(save_path=None):
    """Four experiment batches with identical summary stats, different shapes.
    Padded with noise columns to look like a real experiment log."""
    rng = np.random.RandomState(42)
    x_vals = [
        [10, 8, 13, 9, 11, 14, 6, 4, 12, 7, 5],
        [10, 8, 13, 9, 11, 14, 6, 4, 12, 7, 5],
        [10, 8, 13, 9, 11, 14, 6, 4, 12, 7, 5],
        [8, 8, 8, 8, 8, 8, 8, 19, 8, 8, 8],
    ]
    y_vals = [
        [8.04, 6.95, 7.58, 8.81, 8.33, 9.96, 7.24, 4.26, 10.84, 4.82, 5.68],
        [9.14, 8.14, 8.74, 8.77, 9.26, 8.10, 6.13, 3.10, 9.13, 7.26, 4.74],
        [7.46, 6.77, 12.74, 7.11, 7.81, 8.84, 6.08, 5.39, 8.15, 6.42, 5.73],
        [6.58, 5.76, 7.71, 8.84, 8.47, 7.04, 5.25, 12.50, 5.56, 7.91, 6.89],
    ]
    rows = []
    batch_labels = ["batch_Q1", "batch_Q2", "batch_Q3", "batch_Q4"]
    obs_id = 1
    for batch_i in range(4):
        for j in range(11):
            rows.append({
                "observation_id": obs_id,
                "batch": batch_labels[batch_i],
                "dosage_mg": x_vals[batch_i][j],
                "response": y_vals[batch_i][j],
                "lab_temp_c": round(rng.normal(22, 0.5), 1),
                "technician": rng.choice(["Kim", "Pat", "Alex"]),
                "weight_kg": round(rng.normal(70, 12), 1),
            })
            obs_id += 1
    df = pd.DataFrame(rows)
    if save_path:
        df.to_csv(save_path, index=False)
    return df


# ---------------------------------------------------------------------------
# 5. Multicollinearity
# ---------------------------------------------------------------------------
def generate_multicollinearity(save_path=None):
    """Real-estate pricing where sq_ft, num_rooms, lot_size are near-copies of each other."""
    rng = np.random.RandomState(42)
    n = 800
    sq_ft = rng.normal(1800, 400, n).clip(600, 5000)
    num_rooms = (sq_ft / 300 + rng.normal(0, 0.3, n)).clip(2, 15).round(0).astype(int)
    lot_size_acres = (sq_ft / 2000 + rng.normal(0, 0.05, n)).clip(0.1, 5).round(3)
    garage_spaces = (sq_ft / 900 + rng.normal(0, 0.2, n)).clip(0, 4).round(0).astype(int)
    year_built = rng.randint(1950, 2024, n)
    neighborhood = rng.choice(["Downtown", "Suburbs", "Lakeside", "Hillcrest", "Eastwood"], n)
    # price depends on sq_ft (+ small year_built effect)
    price = (sq_ft * 150 + (year_built - 1950) * 500
             + rng.normal(0, 15000, n)).clip(50000).round(-2)
    df = pd.DataFrame({
        "listing_id": range(1, n + 1),
        "sq_ft": sq_ft.round(0).astype(int),
        "num_rooms": num_rooms,
        "lot_size_acres": lot_size_acres,
        "garage_spaces": garage_spaces,
        "year_built": year_built,
        "neighborhood": neighborhood,
        "has_pool": rng.choice([0, 1], n, p=[0.7, 0.3]),
        "price_usd": price.astype(int),
    })
    if save_path:
        df.to_csv(save_path, index=False)
    return df


# ---------------------------------------------------------------------------
# 6. Heteroscedasticity
# ---------------------------------------------------------------------------
def generate_heteroscedasticity(save_path=None):
    """Ad-spend vs revenue — variance of revenue balloons at high spend."""
    rng = np.random.RandomState(42)
    n = 1000
    ad_spend = rng.uniform(500, 50000, n).round(2)
    region = rng.choice(["North", "South", "East", "West"], n)
    channel = rng.choice(["Social", "Search", "Display", "Email"], n)
    # Revenue grows linearly but noise scales with spend
    noise = rng.normal(0, 1, n) * (500 + 0.3 * ad_spend)
    revenue = 2.5 * ad_spend + noise
    impressions = (ad_spend * rng.uniform(8, 15, n)).astype(int)
    clicks = (impressions * rng.uniform(0.01, 0.05, n)).astype(int)
    df = pd.DataFrame({
        "campaign_id": range(1, n + 1),
        "region": region,
        "channel": channel,
        "ad_spend_usd": ad_spend,
        "impressions": impressions,
        "clicks": clicks,
        "revenue_usd": revenue.round(2),
        "month": rng.choice(range(1, 13), n),
    })
    if save_path:
        df.to_csv(save_path, index=False)
    return df


# ---------------------------------------------------------------------------
# 7. Outlier-Dominated
# ---------------------------------------------------------------------------
def generate_outlier_dominated(save_path=None):
    """E-commerce order data — 5 % of orders have wildly wrong totals (data entry errors)."""
    rng = np.random.RandomState(42)
    n = 1200
    items = rng.randint(1, 20, n)
    unit_price = rng.uniform(5, 200, n).round(2)
    subtotal = items * unit_price
    shipping = rng.choice([0, 4.99, 9.99, 14.99], n)
    order_total = subtotal + shipping + rng.normal(0, 2, n)
    # 5 % outliers: data-entry errors multiply total by 100 or add huge offset
    n_outliers = int(0.05 * n)
    outlier_idx = rng.choice(n, n_outliers, replace=False)
    order_total[outlier_idx] += (
        rng.choice([-1, 1], n_outliers) * rng.uniform(5000, 20000, n_outliers)
    )
    customer_segment = rng.choice(["New", "Returning", "VIP"], n, p=[0.4, 0.45, 0.15])
    df = pd.DataFrame({
        "order_id": range(10000, 10000 + n),
        "customer_segment": customer_segment,
        "items_qty": items,
        "unit_price_usd": unit_price,
        "shipping_usd": shipping,
        "discount_pct": rng.choice([0, 5, 10, 15, 20], n),
        "order_total_usd": order_total.round(2),
        "returned": rng.choice([0, 1], n, p=[0.92, 0.08]),
    })
    if save_path:
        df.to_csv(save_path, index=False)
    return df


# ---------------------------------------------------------------------------
# 8. Time Series + Seasonality
# ---------------------------------------------------------------------------
def generate_time_series_seasonality(save_path=None):
    """Daily website traffic over 3 years with weekly + yearly seasonality."""
    rng = np.random.RandomState(42)
    n_days = 365 * 3
    dates = pd.date_range(start="2022-01-01", periods=n_days, freq="D")
    t = np.arange(n_days, dtype=float)

    trend = 500 + 0.8 * t
    weekly = 200 * np.sin(2 * np.pi * t / 7)
    yearly = 400 * np.sin(2 * np.pi * t / 365.25)
    noise = rng.normal(0, 80, n_days)
    pageviews = (trend + weekly + yearly + noise).clip(100).astype(int)
    unique_visitors = (pageviews * rng.uniform(0.55, 0.75, n_days)).astype(int)
    bounce_rate = (rng.normal(0.45, 0.08, n_days)).clip(0.1, 0.9).round(3)
    avg_session_sec = (rng.normal(180, 40, n_days)).clip(30).round(0).astype(int)

    df = pd.DataFrame({
        "date": dates,
        "pageviews": pageviews,
        "unique_visitors": unique_visitors,
        "bounce_rate": bounce_rate,
        "avg_session_duration_sec": avg_session_sec,
        "new_signups": rng.poisson(15, n_days),
        "support_tickets": rng.poisson(3, n_days),
    })
    if save_path:
        df.to_csv(save_path, index=False)
    return df


# ---------------------------------------------------------------------------
# 9. Missing Not At Random (MNAR)
# ---------------------------------------------------------------------------
def generate_mnar(save_path=None):
    """Customer survey data — high-income respondents skip the income question."""
    rng = np.random.RandomState(42)
    n = 1000
    age = rng.normal(42, 12, n).clip(18, 80).astype(int)
    education_years = (10 + 0.1 * age + rng.normal(0, 2, n)).clip(8, 22).round(0).astype(int)
    # True income — correlated with age and education
    true_income = (20000 + 1500 * education_years + 300 * age
                   + rng.normal(0, 12000, n)).clip(15000).round(-2)
    satisfaction = (rng.normal(6, 2, n) + 0.00002 * true_income).clip(1, 10).round(1)
    region = rng.choice(["Northeast", "Southeast", "Midwest", "West", "Southwest"], n)
    gender = rng.choice(["M", "F", "Other"], n, p=[0.48, 0.48, 0.04])

    # MNAR: probability of reporting income drops as income rises
    prob_missing = 1 / (1 + np.exp(-(true_income - np.median(true_income)) / 15000))
    is_missing = rng.random(n) < prob_missing
    reported_income = true_income.copy().astype(float)
    reported_income[is_missing] = np.nan

    df = pd.DataFrame({
        "respondent_id": range(1, n + 1),
        "age": age,
        "gender": gender,
        "region": region,
        "education_years": education_years,
        "reported_annual_income": reported_income,
        "satisfaction_score": satisfaction,
        "num_children": rng.choice([0, 1, 2, 3, 4], n, p=[0.25, 0.3, 0.25, 0.15, 0.05]),
    })
    if save_path:
        df.to_csv(save_path, index=False)
    return df


# ---------------------------------------------------------------------------
# 10. Class Imbalance (95/5)
# ---------------------------------------------------------------------------
def generate_class_imbalance(save_path=None):
    """Credit-card fraud detection — 5 % fraudulent transactions."""
    rng = np.random.RandomState(42)
    n = 3000
    n_fraud = int(0.05 * n)  # 150
    n_legit = n - n_fraud

    amount_legit = rng.lognormal(3.5, 1.2, n_legit).clip(1, 5000).round(2)
    amount_fraud = rng.lognormal(4.5, 1.0, n_fraud).clip(10, 10000).round(2)
    amounts = np.concatenate([amount_legit, amount_fraud])

    hour_probs = np.array([
        0.01, 0.005, 0.005, 0.005, 0.01, 0.02, 0.04, 0.06,
        0.07, 0.07, 0.06, 0.06, 0.07, 0.06, 0.05, 0.05,
        0.05, 0.06, 0.06, 0.05, 0.04, 0.03, 0.02, 0.015,
    ])
    hour_probs /= hour_probs.sum()
    hour_legit = rng.choice(range(24), n_legit, p=hour_probs)
    hour_fraud = rng.choice(range(24), n_fraud)
    hours = np.concatenate([hour_legit, hour_fraud])

    labels = np.array([0] * n_legit + [1] * n_fraud)
    merchant_category = rng.choice(
        ["Grocery", "Gas", "Restaurant", "Online", "Travel", "Electronics", "ATM"],
        n,
    )
    # Noise features
    card_age_months = rng.randint(1, 120, n)
    distance_from_home_km = np.where(
        labels == 0,
        rng.exponential(10, n),
        rng.exponential(50, n),
    ).round(1)
    is_international = rng.choice([0, 1], n, p=[0.85, 0.15])
    # Shuffle
    idx = rng.permutation(n)
    df = pd.DataFrame({
        "transaction_id": [f"TXN-{i:06d}" for i in range(n)],
        "amount_usd": amounts[idx],
        "hour_of_day": hours[idx],
        "merchant_category": merchant_category[idx],
        "card_age_months": card_age_months[idx],
        "distance_from_home_km": distance_from_home_km[idx],
        "is_international": is_international[idx],
        "is_fraud": labels[idx],
    })
    if save_path:
        df.to_csv(save_path, index=False)
    return df


# ---------------------------------------------------------------------------
# 11. Hidden Non-Linear (Quadratic)
# ---------------------------------------------------------------------------
def generate_quadratic(save_path=None):
    """Engine RPM vs fuel consumption — quadratic relationship masked by noise columns."""
    rng = np.random.RandomState(42)
    n = 600
    rpm = rng.uniform(800, 6000, n).round(0)
    ambient_temp = rng.normal(25, 8, n).round(1)
    humidity = rng.normal(50, 15, n).clip(10, 95).round(1)
    octane_rating = rng.choice([87, 89, 91, 93], n)
    # fuel_consumption = a * rpm^2 + noise (quadratic)
    fuel = 0.000002 * rpm**2 + rng.normal(0, 1.5, n)
    fuel = fuel.clip(0.5).round(2)
    vehicle_age_yr = rng.randint(0, 15, n)
    df = pd.DataFrame({
        "test_id": range(1, n + 1),
        "engine_rpm": rpm.astype(int),
        "ambient_temp_c": ambient_temp,
        "humidity_pct": humidity,
        "octane_rating": octane_rating,
        "vehicle_age_years": vehicle_age_yr,
        "fuel_consumption_lph": fuel,
    })
    if save_path:
        df.to_csv(save_path, index=False)
    return df


# ---------------------------------------------------------------------------
# 12. Well-Separated Clusters
# ---------------------------------------------------------------------------
def generate_well_separated_clusters(save_path=None):
    """Customer purchase behaviour — three distinct segments, no labels."""
    rng = np.random.RandomState(42)
    n_per = 200
    centers = [
        {"avg_order": 25, "frequency": 15, "recency": 5},
        {"avg_order": 120, "frequency": 3, "recency": 45},
        {"avg_order": 75, "frequency": 8, "recency": 20},
    ]
    rows = []
    for c in centers:
        for _ in range(n_per):
            rows.append({
                "avg_order_value": max(1, rng.normal(c["avg_order"], 4)),
                "purchase_frequency_monthly": max(0.1, rng.normal(c["frequency"], 1.5)),
                "days_since_last_purchase": max(0, rng.normal(c["recency"], 3)),
                "total_lifetime_spend": max(
                    10,
                    rng.normal(c["avg_order"] * c["frequency"] * 6, 200),
                ),
                "support_contacts": max(0, int(rng.normal(2, 1.5))),
                "account_age_months": rng.randint(1, 60),
            })
    df = pd.DataFrame(rows).round(2)
    df.insert(0, "customer_id", [f"C-{i:05d}" for i in range(len(df))])
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    if save_path:
        df.to_csv(save_path, index=False)
    return df


# ---------------------------------------------------------------------------
# 13. Overlapping Clusters
# ---------------------------------------------------------------------------
def generate_overlapping_clusters(save_path=None):
    """Student performance data — three loosely overlapping groups."""
    rng = np.random.RandomState(42)
    n_per = 200
    centers = [
        {"study_hrs": 10, "gpa": 3.2},
        {"study_hrs": 12, "gpa": 3.4},
        {"study_hrs": 11, "gpa": 3.0},
    ]
    rows = []
    for c in centers:
        for _ in range(n_per):
            study = max(0, rng.normal(c["study_hrs"], 4))
            gpa = min(4.0, max(0, rng.normal(c["gpa"], 0.6)))
            rows.append({
                "weekly_study_hours": round(study, 1),
                "gpa": round(gpa, 2),
                "extracurriculars": rng.randint(0, 6),
                "commute_minutes": max(0, int(rng.normal(30, 15))),
                "part_time_job_hours": max(0, round(rng.normal(8, 6), 1)),
                "absences": rng.poisson(3),
            })
    df = pd.DataFrame(rows)
    df.insert(0, "student_id", range(1, len(df) + 1))
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    if save_path:
        df.to_csv(save_path, index=False)
    return df


# ---------------------------------------------------------------------------
# 14. Survival / Censored Data
# ---------------------------------------------------------------------------
def generate_survival_censored(save_path=None):
    """Clinical trial data — right-censored, treatment B has better survival."""
    rng = np.random.RandomState(42)
    n = 800
    treatment = rng.choice(["Drug_A", "Drug_B"], n)
    age = rng.normal(62, 11, n).clip(30, 90).astype(int)
    sex = rng.choice(["M", "F"], n)
    stage = rng.choice(["I", "II", "III", "IV"], n, p=[0.2, 0.35, 0.3, 0.15])
    biomarker = rng.lognormal(1.5, 0.8, n).round(2)

    scale_a, scale_b = 12, 22
    true_time = np.where(
        treatment == "Drug_A",
        rng.exponential(scale_a, n),
        rng.exponential(scale_b, n),
    )
    true_time *= np.exp(-0.01 * (age - 60))
    censor_time = rng.uniform(6, 30, n)
    observed_time = np.minimum(true_time, censor_time).round(1)
    event = (true_time <= censor_time).astype(int)

    df = pd.DataFrame({
        "patient_id": [f"P-{i:04d}" for i in range(n)],
        "age": age,
        "sex": sex,
        "stage": stage,
        "biomarker_level": biomarker,
        "treatment": treatment,
        "months_on_study": observed_time,
        "event_occurred": event,
    })
    if save_path:
        df.to_csv(save_path, index=False)
    return df


# ---------------------------------------------------------------------------
# 15. Multi-Modal Distribution
# ---------------------------------------------------------------------------
def generate_multimodal(save_path=None):
    """Property rental prices — mixture of 3 market segments."""
    rng = np.random.RandomState(42)
    n = 1200
    component = rng.choice(3, n, p=[0.35, 0.4, 0.25])
    means = [800, 1600, 3200]
    stds = [150, 300, 500]
    rent = (
        np.array([rng.normal(means[c], stds[c]) for c in component])
        .clip(300)
        .round(0)
        .astype(int)
    )
    sq_ft = (rent * rng.uniform(0.5, 0.9, n) + rng.normal(0, 50, n)).clip(200).round(0).astype(int)
    bedrooms = np.where(rent < 1200, rng.choice([0, 1], n),
               np.where(rent < 2500, rng.choice([1, 2, 3], n),
                        rng.choice([2, 3, 4], n)))
    distance_to_center_km = (rng.exponential(5, n) + rng.normal(0, 1, n)).clip(0.5).round(1)
    year_built = rng.randint(1920, 2024, n)
    df = pd.DataFrame({
        "listing_id": range(1, n + 1),
        "sq_ft": sq_ft,
        "bedrooms": bedrooms,
        "bathrooms": (bedrooms * 0.6 + rng.choice([0, 1], n)).clip(1).astype(int),
        "distance_to_center_km": distance_to_center_km,
        "year_built": year_built,
        "has_parking": rng.choice([0, 1], n),
        "pet_friendly": rng.choice([0, 1], n, p=[0.6, 0.4]),
        "monthly_rent_usd": rent,
    })
    if save_path:
        df.to_csv(save_path, index=False)
    return df


# ---------------------------------------------------------------------------
# 16. Spurious Correlation (Confounded)
# ---------------------------------------------------------------------------
def generate_spurious_correlation(save_path=None):
    """City-level data — ice_cream_sales and drownings both driven by temperature."""
    rng = np.random.RandomState(42)
    n = 365 * 2  # two years of daily data
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    day_of_year = dates.dayofyear
    # Temperature is the confound
    temp = np.asarray(10 + 15 * np.sin(2 * np.pi * (day_of_year - 80) / 365)) + rng.normal(0, 3, n)
    ice_cream_sales = (temp * 50 + rng.normal(0, 100, n)).clip(0).round(0).astype(int)
    pool_visits = (temp * 30 + rng.normal(0, 80, n)).clip(0).round(0).astype(int)
    drowning_incidents = rng.poisson(np.maximum(0.1, temp * 0.05))
    uv_index = (temp * 0.15 + rng.normal(0, 0.5, n)).clip(0, 12).round(1)
    df = pd.DataFrame({
        "date": dates,
        "avg_temperature_c": temp.round(1),
        "ice_cream_sales_units": ice_cream_sales,
        "pool_visits": pool_visits,
        "drowning_incidents": drowning_incidents,
        "uv_index": uv_index,
        "humidity_pct": rng.normal(55, 15, n).clip(10, 100).round(0).astype(int),
    })
    if save_path:
        df.to_csv(save_path, index=False)
    return df


# ---------------------------------------------------------------------------
# 17. High-Dimensional Sparse
# ---------------------------------------------------------------------------
def generate_high_dim_sparse(save_path=None):
    """Gene expression data — 100 gene columns, only 3 predictive of outcome."""
    rng = np.random.RandomState(42)
    n = 600
    n_genes = 100
    X = rng.normal(0, 1, (n, n_genes))
    # Only genes 0, 1, 2 matter
    logit = 1.5 * X[:, 0] - 2.0 * X[:, 1] + 1.0 * X[:, 2]
    prob = 1 / (1 + np.exp(-logit))
    outcome = (rng.random(n) < prob).astype(int)

    columns = [f"gene_{i:03d}" for i in range(n_genes)]
    df = pd.DataFrame(X.round(4), columns=columns)
    df.insert(0, "sample_id", [f"S{i:04d}" for i in range(n)])
    df["age"] = rng.normal(55, 12, n).clip(20, 85).astype(int)
    df["sex"] = rng.choice(["M", "F"], n)
    df["outcome"] = outcome
    if save_path:
        df.to_csv(save_path, index=False)
    return df


# ---------------------------------------------------------------------------
# 18. Interaction Effects
# ---------------------------------------------------------------------------
def generate_interaction_effects(save_path=None):
    """Marketing experiment — conversion depends on channel x time_of_day interaction."""
    rng = np.random.RandomState(42)
    n = 1500
    ad_budget = rng.uniform(100, 5000, n).round(2)
    time_of_day_hour = rng.uniform(0, 24, n).round(1)
    channel_id = rng.uniform(0, 1, n)  # internal continuous proxy
    device = rng.choice(["mobile", "desktop", "tablet"], n, p=[0.55, 0.35, 0.1])
    page_load_sec = rng.exponential(2, n).clip(0.3, 15).round(2)
    # Conversion depends on interaction of channel_id * time_of_day, not main effects
    logit = (0.05 * ad_budget / 1000
             + 0.1 * channel_id
             + 0.1 * time_of_day_hour / 24
             + 3.0 * channel_id * (time_of_day_hour / 24)
             - 2.0 + rng.normal(0, 0.5, n))
    conversion = (rng.random(n) < (1 / (1 + np.exp(-logit)))).astype(int)
    df = pd.DataFrame({
        "session_id": range(1, n + 1),
        "ad_budget_usd": ad_budget,
        "time_of_day_hour": time_of_day_hour,
        "channel_score": channel_id.round(3),
        "device": device,
        "page_load_time_sec": page_load_sec,
        "previous_visits": rng.poisson(3, n),
        "converted": conversion,
    })
    if save_path:
        df.to_csv(save_path, index=False)
    return df


# ---------------------------------------------------------------------------
# 19. Log-Normal / Heavy Skew
# ---------------------------------------------------------------------------
def generate_lognormal_skew(save_path=None):
    """Startup funding rounds — deal size is log-normally distributed."""
    rng = np.random.RandomState(42)
    n = 800
    employees = rng.randint(5, 500, n)
    years_since_founding = rng.uniform(0.5, 15, n).round(1)
    revenue_growth_pct = rng.normal(30, 40, n).round(1)
    # log(funding) is linear in features
    log_funding = (10 + 0.003 * employees + 0.1 * years_since_founding
                   + 0.005 * revenue_growth_pct + rng.normal(0, 0.6, n))
    funding = np.exp(log_funding).round(0).astype(int)
    sector = rng.choice(["SaaS", "Biotech", "Fintech", "Hardware", "AI/ML", "Consumer"], n)
    round_type = rng.choice(["Seed", "Series_A", "Series_B", "Series_C"], n,
                            p=[0.35, 0.30, 0.20, 0.15])
    df = pd.DataFrame({
        "company_id": [f"CO-{i:04d}" for i in range(n)],
        "sector": sector,
        "round_type": round_type,
        "employees": employees,
        "years_since_founding": years_since_founding,
        "revenue_growth_pct": revenue_growth_pct,
        "num_investors": rng.randint(1, 12, n),
        "funding_amount_usd": funding,
    })
    if save_path:
        df.to_csv(save_path, index=False)
    return df


# ---------------------------------------------------------------------------
# 20. Concept Drift
# ---------------------------------------------------------------------------
def generate_concept_drift(save_path=None):
    """Manufacturing quality data — process parameters shift mid-way through."""
    rng = np.random.RandomState(42)
    n = 1500
    half = n // 2
    timestamps = pd.date_range("2023-06-01", periods=n, freq="30min")
    temperature = rng.normal(200, 5, n).round(1)
    pressure = rng.normal(50, 3, n).round(2)
    vibration = rng.exponential(2, n).round(3)
    speed_rpm = rng.normal(3000, 200, n).round(0).astype(int)

    # First half: defect_rate depends positively on temperature
    defect_first = (0.02 * temperature[:half] - 3 + rng.normal(0, 0.3, half)).clip(0, 1)
    # Second half: relationship inverts (process recalibrated)
    defect_second = (-0.015 * temperature[half:] + 4 + rng.normal(0, 0.3, n - half)).clip(0, 1)
    defect_rate = np.concatenate([defect_first, defect_second]).round(4)

    operator = rng.choice(["Shift_A", "Shift_B", "Shift_C"], n)
    df = pd.DataFrame({
        "timestamp": timestamps,
        "temperature_c": temperature,
        "pressure_bar": pressure,
        "vibration_mm_s": vibration,
        "speed_rpm": speed_rpm,
        "operator": operator,
        "defect_rate": defect_rate,
    })
    if save_path:
        df.to_csv(save_path, index=False)
    return df


# ---------------------------------------------------------------------------
# Generator registry & entry point
# ---------------------------------------------------------------------------
GENERATORS = {
    "simpsons_paradox": generate_simpsons_paradox,
    "pure_noise": generate_pure_noise,
    "deterministic_linear": generate_deterministic_linear,
    "anscombes_quartet": generate_anscombes_quartet,
    "multicollinearity": generate_multicollinearity,
    "heteroscedasticity": generate_heteroscedasticity,
    "outlier_dominated": generate_outlier_dominated,
    "time_series_seasonality": generate_time_series_seasonality,
    "mnar": generate_mnar,
    "class_imbalance": generate_class_imbalance,
    "quadratic": generate_quadratic,
    "well_separated_clusters": generate_well_separated_clusters,
    "overlapping_clusters": generate_overlapping_clusters,
    "survival_censored": generate_survival_censored,
    "multimodal": generate_multimodal,
    "spurious_correlation": generate_spurious_correlation,
    "high_dim_sparse": generate_high_dim_sparse,
    "interaction_effects": generate_interaction_effects,
    "lognormal_skew": generate_lognormal_skew,
    "concept_drift": generate_concept_drift,
}

# Maps opaque filenames to internal dataset names — agents never see the real name
FILENAME_MAP = {
    "dataset_001.csv": "simpsons_paradox",
    "dataset_002.csv": "pure_noise",
    "dataset_003.csv": "deterministic_linear",
    "dataset_004.csv": "anscombes_quartet",
    "dataset_005.csv": "multicollinearity",
    "dataset_006.csv": "heteroscedasticity",
    "dataset_007.csv": "outlier_dominated",
    "dataset_008.csv": "time_series_seasonality",
    "dataset_009.csv": "mnar",
    "dataset_010.csv": "class_imbalance",
    "dataset_011.csv": "quadratic",
    "dataset_012.csv": "well_separated_clusters",
    "dataset_013.csv": "overlapping_clusters",
    "dataset_014.csv": "survival_censored",
    "dataset_015.csv": "multimodal",
    "dataset_016.csv": "spurious_correlation",
    "dataset_017.csv": "high_dim_sparse",
    "dataset_018.csv": "interaction_effects",
    "dataset_019.csv": "lognormal_skew",
    "dataset_020.csv": "concept_drift",
}

# Reverse: internal name → opaque filename
NAME_TO_FILENAME = {v: k for k, v in FILENAME_MAP.items()}


def generate_all(output_dir: str) -> dict[str, pd.DataFrame]:
    """Generate all 20 datasets, saving under opaque filenames."""
    os.makedirs(output_dir, exist_ok=True)
    results: dict[str, pd.DataFrame] = {}
    for name, generator in GENERATORS.items():
        filename = NAME_TO_FILENAME[name]
        save_path = os.path.join(output_dir, filename)
        df = generator(save_path=save_path)
        results[name] = df
        print(f"  [{filename}] {df.shape[0]} rows x {df.shape[1]} cols -> {save_path}")
    return results


if __name__ == "__main__":
    script_dir = Path(__file__).resolve().parent
    default_output = script_dir / "generated"
    print(f"Generating 20 datasets to {default_output} ...")
    datasets = generate_all(str(default_output))
    print(f"\nDone. Generated {len(datasets)} datasets.")
