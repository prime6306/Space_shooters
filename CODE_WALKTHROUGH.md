# Complete Code Walkthrough — Every File, Every Block
### Line by line. No skips. Alternatives included.

---

# FILE 1 — `data/generate_data.py`

---

## Block 1 — Imports

```python
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os
```

**pandas** — used for creating DataFrames and saving to CSV. Could use plain Python dicts + `csv` module as alternative, but pandas `.to_csv()` is one line vs 15.

**numpy** — used for `np.random.uniform()` (spread coordinates) and `np.random.seed()`. Could use Python's `random` module for everything, but numpy is faster on large arrays and the seed system is more reproducible.

**datetime + timedelta** — to iterate day by day from Jan to Apr. `timedelta(days=1)` lets you increment a date cleanly without worrying about month boundaries.

**random** — Python's built-in random. Used alongside numpy because `random.randint()` and `random.sample()` are simpler for list operations than numpy equivalents.

**os** — only for `os.makedirs("data", exist_ok=True)`. Alternative: `pathlib.Path("data").mkdir(exist_ok=True)` — more modern Python style, either works.

---

## Block 2 — Seeds

```python
np.random.seed(42)
random.seed(42)
```

Seeds fix the random number generators so every run produces **identical data**. Without this, coordinates shift every run, models train on different data each time, and tests that depend on specific values would fail randomly.

**42** is conventional — no special meaning, just universally used in ML examples.

**Why two seeds?** `numpy` and Python's `random` are separate generators. Seeding one doesn't affect the other. If you use `np.random.uniform()` and also `random.randint()`, you need both seeded.

**Alternative:** Pass seeds as arguments to functions instead of global state — cleaner for testing but overkill here.

---

## Block 3 — Base Coordinates

```python
BASE_LAT = 26.8467
BASE_LNG = 80.9462
```

Lucknow city center. All store coordinates are generated as offsets from this point.

**Why real city coordinates?** If evaluator drops these into Google Maps, actual roads and city layout appear. Looks more credible than random ocean coordinates.

**Alternative:** Use any real city — Mumbai (19.0760, 72.8777), Delhi (28.6139, 77.2090). The math works the same.

---

## Block 4 — store_names list

```python
store_names = [
    "Metro Cash & Carry Hazratganj", "Big Bazaar Gomti Nagar", ...
]
```

50 real-sounding store names from Lucknow neighborhoods. This is purely aesthetic — makes printed output and `/docs` examples look real.

**Alternative:** Use generic names like `Store_1, Store_2...` — works but looks synthetic. Human judge notices details like this.

---

## Block 5 — `assign_traffic_zone()`

```python
def assign_traffic_zone(lat, lng):
    dist_from_center = abs(lat - BASE_LAT) + abs(lng - BASE_LNG)
    if dist_from_center < 0.05:
        return "high_traffic"
    elif dist_from_center < 0.10:
        return "medium_traffic"
    return "low_traffic"
```

Uses **Manhattan distance** (`abs(dlat) + abs(dlng)`) from city center to assign traffic zone. Central areas = high traffic, outer areas = low.

**Why Manhattan and not Euclidean?** `sqrt(dlat² + dlng²)` is also valid here. Manhattan is slightly faster (no sqrt) and the threshold values just need to be adjusted. Both produce the same zone assignment patterns.

**Thresholds (0.05, 0.10):** In degrees, 0.05° ≈ 5.5 km. So within ~5.5 km of center = high traffic. Between 5.5-11 km = medium. Beyond = low. Reasonable for a mid-size city.

**Alternative:** Use a proper GIS approach — polygon-based zone assignment. But for synthetic data, distance from center is good enough.

---

## Block 6 — `build_locations()`

```python
def build_locations():
    rows = []
    for i, name in enumerate(store_names):
        lat = BASE_LAT + np.random.uniform(-0.13, 0.13)
        lng = BASE_LNG + np.random.uniform(-0.13, 0.13)
        rows.append({
            "location_id": f"L{i+1:02d}",
            ...
            "avg_visit_min": random.randint(12, 40),
        })
    return pd.DataFrame(rows)
```

`np.random.uniform(-0.13, 0.13)` — spread of ±0.13° ≈ ±14.5 km from center. Covers a realistic city footprint.

`f"L{i+1:02d}"` — zero-padded ID like L01, L02...L50. The `:02d` format means at least 2 digits. Without it you'd get L1, L2...L10 and sorting would be lexicographic (L10 before L2).

`avg_visit_min` — each store has a baseline visit duration. This gets used in ETA calculations and is more realistic than a flat 20-minute assumption for every store.

**Alternative for IDs:** UUIDs (`uuid.uuid4()`) would be more production-like. But sequential IDs are easier to type in API test calls, which matters for demo purposes.

---

## Block 7 — `DRIVER_ZONES` dict

```python
DRIVER_ZONES = {
    "D1":  [f"L{i:02d}" for i in range(1, 11)],
    "D2":  [f"L{i:02d}" for i in range(11, 21)],
    ...
    "D6":  ["L01","L11","L21","L31","L41",...],
}
```

D1-D5 each own 10 consecutive locations (contiguous zones). D6-D10 are "cross-zone" drivers who pick from spread-out locations. This creates two pattern types the model can learn from — specialists and generalists.

`[f"L{i:02d}" for i in range(1, 11)]` — list comprehension generating `["L01","L02",...,"L10"]`. Alternative: manually write the list — same result, just more typing.

---

## Block 8 — `traffic_multiplier()`

```python
def traffic_multiplier(hour):
    if 8 <= hour <= 10 or 17 <= hour <= 19:
        return round(random.uniform(1.3, 1.8), 2)
    elif 13 <= hour <= 14:
        return round(random.uniform(1.1, 1.3), 2)
    return round(random.uniform(0.85, 1.05), 2)
```

Returns a multiplier applied to base travel time. Rush hours (8-10 AM, 5-7 PM) get 1.3-1.8×. Lunch (1-2 PM) gets a small bump. Off-peak is near 1.0.

`round(..., 2)` keeps the numbers clean in the CSV. Without rounding you get things like `1.7348291...`.

**Alternative:** Use a lookup table or a sine wave approximation for smoother variation across hours. But for generating training data, discrete bands work just fine.

---

## Block 9 — `generate_trips()` — main loop

```python
def generate_trips(locations_df):
    loc = {r["location_id"]: r for _, r in locations_df.iterrows()}
```

Dict comprehension converting the DataFrame to a fast lookup `{location_id → row_dict}`. This is important — inside the loops we call `loc[stop_id]` many times. If we used `locations_df[locations_df["location_id"] == stop_id]` inside the loop, it'd be O(n) per lookup → slow. Dict lookup is O(1).

**Alternative:** Use `locations_df.set_index("location_id")` and `.loc[stop_id]` — also O(1) with pandas index, equally valid.

```python
    start = datetime(2026, 1, 2)
    end   = datetime(2026, 4, 30)
```

Jan 2 to Apr 30 — ~4 months of history. Jan 1 skipped (New Year's Day). This range gives ~91 working days × 10 drivers × 6.8 avg stops = ~6200 records.

```python
    for driver, home_zone in DRIVER_ZONES.items():
        day = start
        while day <= end:
            if day.weekday() == 6:  # skip sundays
                day += timedelta(days=1)
                continue
```

`day.weekday()` returns 0=Monday through 6=Sunday. Skipping 6 = no Sunday trips. The `continue` jumps back to the `while` check after incrementing — clean loop control.

**Alternative:** Generate a list of all working days upfront with `pd.bdate_range()` — more pandas-idiomatic but less readable for this use case.

```python
            n_stops = random.randint(3, 5) if day.weekday() == 5 else random.randint(5, 8)
```

Saturday (`weekday() == 5`) gets fewer stops. Ternary expression keeps it one line. Equivalent to:
```python
if day.weekday() == 5:
    n_stops = random.randint(3, 5)
else:
    n_stops = random.randint(5, 8)
```

```python
            pool = home_zone.copy()
            random.shuffle(pool)
            stops = pool[:min(n_stops, len(pool))]
            if len(stops) < n_stops:
                extras = random.sample([x for x in all_ids if x not in pool], n_stops - len(stops))
                stops += extras
```

Step by step:
1. Copy home_zone so we don't mutate the original
2. Shuffle — so the order of stops varies each day
3. Take first `n_stops` from shuffled pool
4. If home zone has fewer locations than needed, fill from outside the zone

`random.sample(population, k)` — picks k items without replacement. Used here to avoid visiting the same "extra" stop twice in one day.

**Alternative:** `np.random.choice(all_ids, size=k, replace=False)` — numpy equivalent.

```python
            clock = datetime(day.year, day.month, day.day, 
                           random.randint(8, 9), random.randint(0, 45))
```

Start time between 8:00 and 9:45 AM. Simulates drivers starting at slightly different times.

```python
            for seq, stop_id in enumerate(stops, start=1):
```

`enumerate(..., start=1)` gives (1, first_stop), (2, second_stop)... so `stop_sequence` is 1-indexed as expected.

```python
                clock += timedelta(minutes=int(visit_min + travel_min))
```

Advance the clock after each stop by visit duration + travel time. This makes `visit_time` for each stop realistically later than the previous.

---

## Block 10 — `if __name__ == "__main__"`

```python
if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    locs = build_locations()
    trips = generate_trips(locs)
    locs.to_csv("data/locations.csv", index=False)
    trips.to_csv("data/trips.csv", index=False)
```

`if __name__ == "__main__"` — this block runs only when the file is executed directly (`python data/generate_data.py`), not when imported by another module. Standard Python pattern.

`index=False` — suppresses the pandas row index (0, 1, 2...) from being written as a column. Without it, CSVs have an ugly unnamed first column.

`exist_ok=True` — doesn't raise an error if `data/` already exists. Without it, re-running the script after the first time would crash.

---

---

# FILE 2 — `model/features.py`

---

## Block 1 — `TRAFFIC_ZONE_SCORE`

```python
TRAFFIC_ZONE_SCORE = {
    "high_traffic":   2,
    "medium_traffic": 1,
    "low_traffic":    0,
}
```

Maps string zone names to ordinal integers. ML models can't use strings directly — they need numbers. This is the simplest possible encoding.

**Alternative:** One-hot encoding (3 binary columns). Better when zones are truly categorical with no order. But high/medium/low does have order — high traffic IS worse than medium — so ordinal encoding is appropriate here.

**Alternative 2:** Label encoding with sklearn's `LabelEncoder`. Same result but requires fitting and saving the encoder object.

---

## Block 2 — `cyclic_encode()`

```python
def cyclic_encode(value, max_value):
    angle = 2 * np.pi * value / max_value
    return np.sin(angle), np.cos(angle)
```

Converts a circular value into two continuous values. The key insight: hour 23 and hour 0 are only 1 hour apart, but numerically `|23 - 0| = 23`. A model treating this as linear distance would think they're far apart. Sin/cos encoding fixes this — hour 23 and hour 0 map to nearly identical (sin, cos) pairs.

**Why both sin AND cos?** Sin alone is ambiguous — `sin(π/6)` and `sin(5π/6)` are both 0.5, representing hours 2 and 10. Adding cos makes each hour uniquely identifiable.

**Alternative:** Embed as a single angle and use a custom periodic kernel. Too complex for this use case.

**Alternative 2:** Just pass the raw hour as a feature and hope the model learns the circularity. XGBoost can sometimes approximate this with enough data, but it's unreliable.

---

## Block 3 — `haversine_km()`

```python
def haversine_km(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = np.radians(lat2 - lat1)
    dlng = np.radians(lng2 - lng1)
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlng/2)**2
    return R * 2 * np.arcsin(np.sqrt(a))
```

`R = 6371` — Earth's radius in km.

The formula accounts for Earth's curvature. For small city distances (< 50 km), the error vs flat-earth approximation is < 0.2% — negligible.

`np.arcsin(np.sqrt(a))` — this is the haversine inverse. The full formula is `2R * arcsin(sqrt(a))`.

**Important**: Returns straight-line distance. Actual road distance is typically 1.2-1.4× this. That's fine for features — we want relative distances, not exact road lengths.

**Alternative:** Use `geopy.distance.geodesic()` — handles ellipsoidal Earth model, marginally more accurate, but requires an extra dependency.

---

## Block 4 — `route_spread()`

```python
def route_spread(lats, lngs):
    if len(lats) < 2:
        return 0.0
    center_lat = np.mean(lats)
    center_lng = np.mean(lngs)
    dists = [haversine_km(lat, lng, center_lat, center_lng) for lat, lng in zip(lats, lngs)]
    return float(np.std(dists))
```

Computes **standard deviation of distances from centroid**. High std = stops are spread out unevenly.

`float()` cast at the end — converts numpy scalar to Python float. Necessary because downstream code does JSON serialization, which handles Python float but not numpy float64.

`if len(lats) < 2: return 0.0` — guard for single-stop routes. std of one point is undefined / zero.

**Alternative:** Use bounding box area (max_lat - min_lat) * (max_lng - min_lng). Simpler but doesn't capture clustering well — two stops at opposite corners vs five stops spread evenly would look the same.

---

## Block 5 — `build_driver_profiles()`

```python
def build_driver_profiles(trips_df):
    grp = trips_df.groupby(["driver_id", "date"]).agg(
        total_travel = ("travel_time_min", "sum"),
        total_stops  = ("stop_id", "count"),
        avg_traffic  = ("traffic_mult", "mean"),
    ).reset_index()

    grp["stops_per_hour"] = grp["total_stops"] / (grp["total_travel"] / 60 + 0.1)
```

Named aggregation syntax `("column", "function")` — cleaner than the old dict style. Creates route-level rows from stop-level rows.

`+ 0.1` in denominator — prevents division by zero if a route somehow has 0 travel time.

```python
    profiles = grp.groupby("driver_id").agg(
        avg_stops_per_hour = ("stops_per_hour", "mean"),
        avg_daily_stops    = ("total_stops", "mean"),
        avg_traffic_mult   = ("avg_traffic", "mean"),
    ).reset_index()
```

Second groupby — now averaging across all days for each driver. Two-stage aggregation: stop → day → driver.

`reset_index()` after groupby turns the group keys back into regular columns instead of index levels. Makes subsequent `df[df["driver_id"] == ...]` filtering work cleanly.

**Alternative:** Use `pandas.pivot_table()`. Same result, different syntax.

---

## Block 6 — `make_route_features()`

```python
def make_route_features(driver_id, date_str, stop_ids, lats, lngs,
                        traffic_zones, hour, driver_profiles):
```

This function is the **bridge between raw data and model input**. Called from both `scripts/train.py` (building training set) and `api/routes/daily.py` (live prediction). Having one function for both guarantees feature consistency.

```python
    dow = pd.Timestamp(date_str).dayofweek
```

`pd.Timestamp(date_str).dayofweek` converts "2026-05-20" to day-of-week integer (0=Monday). Alternative: `datetime.strptime(date_str, "%Y-%m-%d").weekday()` — same result.

```python
    dp = driver_profiles[driver_profiles["driver_id"] == driver_id]
    if len(dp) > 0:
        avg_speed = float(dp["avg_stops_per_hour"].iloc[0])
    else:
        avg_speed = 3.5  # global fallback
```

`.iloc[0]` — gets first row as a Series. `.iloc[0]["col"]` or `.at[idx, "col"]` would also work.

`float()` cast — same reason as before, numpy → Python type for JSON safety.

Fallback values `(3.5, 6.0, 1.1)` — these are rough dataset averages. For a new driver, the model uses typical fleet behavior. Better alternative: compute and store actual global averages from training data rather than hardcoding.

---

## Block 7 — `build_training_data()`

```python
def build_training_data(trips_df, driver_profiles):
    rows = []
    for (driver, date), grp in trips_df.groupby(["driver_id", "date"]):
        grp = grp.sort_values("stop_sequence")
```

Iterating over groups — each `(driver, date)` key gives one day's stops. Sorting by `stop_sequence` ensures the lats/lngs are in the actual visit order for computing sequential distances.

```python
        total_time = grp["travel_time_min"].sum() + grp["visit_duration_min"].sum()
        efficiency = feats["n_stops"] / (total_time / 60 + 0.1)
```

**Efficiency formula:** stops completed per hour of total time (travel + visits). This is the raw target before normalization.

```python
    mn, mx = df["efficiency"].min(), df["efficiency"].max()
    df["efficiency_score"] = (df["efficiency"] - mn) / (mx - mn + 1e-9)
```

**Min-max normalization** to 0-1. `1e-9` in denominator prevents division by zero if all routes somehow have the same efficiency (impossible in practice but safe to handle).

**Alternative target:** Ratio of actual time to estimated optimal time (from TSP). More theoretically sound but requires running TSP on every historical route — much slower. Min-max normalized efficiency is simpler and works well.

**Alternative normalization:** StandardScaler (mean=0, std=1). Better for neural networks, but since this is XGBoost target and we want the output to be interpretable as a 0-1 confidence score, min-max is appropriate.

---

## Block 8 — `FEATURE_COLS`

```python
FEATURE_COLS = [
    "n_stops", "total_dist_km", "area_spread", "avg_traffic_score",
    "hour_sin", "hour_cos", "day_sin", "day_cos",
    "is_weekend", "driver_speed", "driver_avg_stops", "driver_hist_mult",
]
```

This list is **the contract** between `features.py`, `ranker.py`, and `daily.py`. Every feature used at training time must be in this list, and every prediction must produce all these features. Shared constant prevents mismatch.

---

---

# FILE 3 — `model/tsp.py`

---

## Block 1 — `distance_matrix()`

```python
def distance_matrix(lats, lngs):
    n = len(lats)
    mat = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i != j:
                mat[i][j] = haversine_km(lats[i], lngs[i], lats[j], lngs[j])
    return mat
```

Creates an N×N matrix where `mat[i][j]` = distance from stop i to stop j.

`if i != j` — diagonal stays zero (distance from a stop to itself). Without this you'd overwrite zeros with `haversine(x,x,x,x) = 0.0` anyway, but the condition makes intent clear.

**Complexity:** O(n²) — for 8 stops that's 64 calls. Fine here.

**Alternative:** Use vectorized numpy operations with meshgrid for large N. For N < 20, the loop is readable and fast enough.

**Alternative:** Use Google's Distance Matrix API results instead of haversine — this would give real road distances. In the full system, when a real API key is present, you could precompute this matrix once and pass it to the TSP solver.

---

## Block 2 — `greedy_route()`

```python
def greedy_route(dist_mat):
    n = len(dist_mat)
    visited = [False] * n
    route = [0]
    visited[0] = True

    for _ in range(n - 1):
        current = route[-1]
        nearest = min(
            (dist_mat[current][j], j)
            for j in range(n) if not visited[j]
        )[1]
        route.append(nearest)
        visited[nearest] = True

    return route
```

Classic nearest-neighbor heuristic. Always starts at index 0 (first stop in the input list).

`min((dist, j) for j in ...)` — finds the `(distance, index)` tuple with minimum distance. `[1]` extracts just the index.

This works because Python's tuple comparison is lexicographic — it compares first elements (distances) first, breaking ties by second element (index). So `min()` returns the closest unvisited stop's index.

**Why start at 0?** Arbitrary choice. More sophisticated: try starting from every stop and pick the best — O(n²) extra work, marginal gain for < 10 stops.

**Alternative:** Random restart — run greedy from multiple random starting points, keep shortest. Better quality, more computation.

---

## Block 3 — `route_length()`

```python
def route_length(route, dist_mat):
    return sum(dist_mat[route[i]][route[i+1]] for i in range(len(route) - 1))
```

Sums consecutive edge weights. `range(len(route) - 1)` iterates pairs (0,1), (1,2), (2,3)... stopping before the last index.

**Note:** This does NOT include the return trip home. For a delivery problem you'd add `dist_mat[route[-1]][route[0]]`. For field sales, drivers go home separately, so we don't close the loop.

---

## Block 4 — `two_opt()`

```python
def two_opt(route, dist_mat, max_rounds=100):
    best = route[:]
    best_len = route_length(best, dist_mat)
    improved = True
    rounds = 0

    while improved and rounds < max_rounds:
        improved = False
        rounds += 1
        for i in range(1, len(best) - 1):
            for j in range(i + 1, len(best)):
                candidate = best[:i] + best[i:j+1][::-1] + best[j+1:]
                clen = route_length(candidate, dist_mat)
                if clen < best_len - 1e-10:
                    best = candidate
                    best_len = clen
                    improved = True

    return best, best_len
```

`best = route[:]` — shallow copy of the list. Without `[:]`, `best` and `route` would point to the same list and mutations would affect both.

`best[i:j+1][::-1]` — slice from i to j (inclusive), then `[::-1]` reverses it. This is the 2-opt "flip" operation.

`clen < best_len - 1e-10` — the `1e-10` tolerance prevents accepting floating-point noise as "improvements". Without it, routes that are effectively the same length might keep getting "improved" in tiny increments.

`improved = True` inside the `if` — this restarts the outer while loop. After finding any improvement, start checking all pairs again. This is why 2-opt is correct — it keeps going until no improvement exists.

`max_rounds=100` — safety limit. In practice for 8 stops this converges in 2-3 rounds.

**Alternative:** 3-opt — tries reversing 3 segments instead of 2. Better quality, O(n³) per round instead of O(n²). Not worth it for < 20 stops.

**Alternative:** Lin-Kernighan moves — variable-depth search used in production TSP solvers. Overkill here.

---

## Block 5 — `solve()` — main entry

```python
def solve(location_ids, lats, lngs):
    if len(location_ids) <= 1:
        return location_ids, 0.0

    if len(location_ids) == 2:
        dist = haversine_km(lats[0], lngs[0], lats[1], lngs[1])
        return location_ids, round(dist, 2)
```

Edge case handling before the main algorithm. Single stop → trivially return it. Two stops → no optimization needed, just compute the one distance. Prevents the matrix solver from being called with trivial inputs.

```python
    ordered_ids = [location_ids[i] for i in optimized]
    return ordered_ids, round(total_km, 2)
```

The TSP works on index arrays (0, 1, 2...). This list comprehension maps indices back to the original location IDs. `optimized` is a list of indices in optimal order, `location_ids[i]` retrieves the actual ID string.

---

## Block 6 — `estimate_drive_time()`

```python
def estimate_drive_time(total_km, avg_speed_kmh=30):
    return round(total_km / avg_speed_kmh, 2)
```

Used by the weekly endpoint for rough total time estimates. 30 km/h is a reasonable Indian city average.

**Alternative:** Use the ETA model per leg for more accurate estimates. But weekly predictions are inherently rough — cluster-based, not stop-by-stop. 30 km/h average is honest about the approximation level.

---

---

# FILE 4 — `model/ranker.py`

---

## Block 1 — `train()`

```python
model = xgb.XGBRegressor(
    n_estimators=200,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    verbosity=0,
)
model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
```

**n_estimators=200** — number of trees. More trees = better fit, but diminishing returns past 200 for this dataset size.

**max_depth=5** — each tree can ask 5 yes/no questions. Deeper = more expressive but overfits. 5 is a commonly safe default.

**learning_rate=0.05** — how much each tree corrects the previous. Lower = more trees needed, but more robust generalization.

**subsample=0.8** and **colsample_bytree=0.8** — use 80% of rows and 80% of features per tree. Adds randomness, prevents overfitting, similar to Random Forest's bagging idea.

**eval_set=[(X_val, y_val)]** — XGBoost internally monitors validation loss. Doesn't stop early here (no `early_stopping_rounds`), but the validation scores are tracked for logging.

**Alternative:** Random Forest from sklearn — similar performance, no hyperparameter sensitivity, but slightly slower inference. LightGBM — faster to train, similar accuracy, another dependency.

---

## Block 2 — `load()` and `score_route()`

```python
def load():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"No trained ranker found at {MODEL_PATH}. Run scripts/train.py first.")
    return joblib.load(MODEL_PATH)
```

**Why joblib and not pickle?** joblib is specifically optimized for numpy arrays and scikit-learn/xgboost objects — faster serialization and smaller file size than pickle. XGBoost models save fine with either but joblib is the sklearn-ecosystem standard.

```python
def score_route(model, feature_dict):
    row = pd.DataFrame([feature_dict])[FEATURE_COLS]
    raw = float(model.predict(row)[0])
    return round(float(np.clip(raw, 0.0, 1.0)), 3)
```

`pd.DataFrame([feature_dict])[FEATURE_COLS]` — wrapping a dict in a list creates a single-row DataFrame. `[FEATURE_COLS]` selects only the columns the model was trained on, in the right order.

`np.clip(raw, 0.0, 1.0)` — clamps prediction to [0,1]. The model was trained on 0-1 targets, but regression can sometimes extrapolate outside this range on unfamiliar inputs.

`round(..., 3)` — three decimal places, sufficient precision for a confidence score shown in API responses.

---

## Block 3 — `feature_importance()`

```python
def feature_importance(model):
    scores = model.get_booster().get_fscore()
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked
```

`get_fscore()` returns how many times each feature was used across all trees (frequency-based importance). `sorted(..., reverse=True)` ranks from most to least important.

This function isn't called in the main flow — it's utility code for analysis. You can call it in a notebook or print it during training to understand what the model learned.

**Alternative importance metric:** `model.feature_importances_` attribute — this uses "gain" (average information gain per split) which is generally more informative than frequency. Worth knowing for interviews.

---

---

# FILE 5 — `model/eta_model.py`

---

## Block 1 — `ETA_FEATURES` list

```python
ETA_FEATURES = [
    "dist_km", "hour_sin", "hour_cos", "day_sin", "day_cos",
    "is_weekend", "traffic_zone_score", "traffic_mult_est",
]
```

8 features specifically for leg-level travel time prediction. Note `traffic_mult_est` is included — in training data we have the actual multiplier. In inference (live prediction), we use a default of 1.1 or derive it from the zone.

---

## Block 2 — `build_eta_samples()`

```python
for (driver, date), grp in trips_df.groupby(["driver_id", "date"]):
    grp = grp.sort_values("stop_sequence").reset_index(drop=True)
    for i in range(1, len(grp)):
        prev = grp.iloc[i - 1]
        curr = grp.iloc[i]
        dist = haversine_km(prev["lat"], prev["lng"], curr["lat"], curr["lng"])
```

`reset_index(drop=True)` after sort — ensures `.iloc[i-1]` reliably gives the previous row. Without `drop=True`, the original index values are kept, but the positional access still works. With it, index is clean 0,1,2...

`range(1, len(grp))` — starts at 1 to access `i-1` without going negative.

Each sample is a **leg** — travel from one stop to the next. This transforms route data into leg data, multiplying our training samples. If a driver has 6 stops per day, we get 5 legs per day.

**Total leg samples:** ~6161 trips / avg 6.8 stops per route × (6.8-1) legs = ~5300 leg samples. Good training set size for an 8-feature MLP.

---

## Block 3 — `train()` with Pipeline

```python
model = Pipeline([
    ("scaler", StandardScaler()),
    ("nn", MLPRegressor(
        hidden_layer_sizes=(64, 32),
        activation="relu",
        max_iter=300,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.1,
    ))
])
```

**Pipeline** wraps scaler + model together. When you call `model.fit(X, y)`, it fits the scaler first, then passes scaled data to the MLP. When you call `model.predict(X)`, it scales the input first automatically. This is critical — you must scale with the same parameters used in training.

**Why Pipeline and not manual scaling?** If you scale separately, you need to save the scaler object and manually apply it every time. With Pipeline, both are bundled in one `joblib.dump()` call.

**StandardScaler** — subtracts mean, divides by std. Neural networks need this because gradient descent performs poorly when features have vastly different scales (dist_km in range 0-20, hour_sin in range -1 to 1).

**hidden_layer_sizes=(64, 32)** — two hidden layers: 64 neurons then 32. Input (8) → 64 → 32 → Output (1). Intentionally small to avoid overfitting on ~5000 samples.

**activation="relu"** — Rectified Linear Unit. f(x) = max(0, x). Most common activation, works well for regression. Alternative: "tanh" — sometimes better for bounded outputs, but ReLU trains faster.

**early_stopping=True, validation_fraction=0.1** — internally holds out 10% of training data to monitor validation loss. Stops training if validation loss stops improving. Prevents overfitting without manual epoch selection.

**Alternative:** `torch.nn.Sequential` with PyTorch — more flexible, GPU support, but overkill for an 8-feature regression with 5000 samples. sklearn MLP is perfect here.

---

## Block 4 — `predict_leg()`

```python
def predict_leg(model, dist_km, hour, day_of_week, traffic_zone, traffic_mult=1.1):
    ...
    pred = float(model.predict(row)[0])
    return round(max(pred, 1.0), 1)  # at least 1 minute
```

`max(pred, 1.0)` — physical constraint: travel time can't be negative or zero. Even moving 100m takes at least a minute in city traffic.

`traffic_mult=1.1` default — a slight traffic overhead is always assumed when zone-specific data is unavailable.

---

## Block 5 — `predict_route_eta()`

```python
for i in range(1, len(ordered_lats)):
    dist = haversine_km(ordered_lats[i-1], ...)
    t = predict_leg(model, dist, current_hour, ...)
    leg_times.append(t)
    current_hour = min(current_hour + int((t + avg_visit_min) / 60), 22)
```

`current_hour` advances as the day progresses — so later legs get predictions using the appropriate hour context (afternoon traffic vs morning traffic). Without this, all legs would use `start_hour=9` regardless of actual time.

`min(..., 22)` — caps hour at 10 PM. Prevents going past midnight in edge cases with many stops.

```python
total_visits = avg_visit_min * len(ordered_lats)
total_hours  = round((total_travel + total_visits) / 60, 2)
```

Total time = travel between stops + time spent at each stop. Both in minutes, divided by 60 to get hours.

---

---

# FILE 6 — `api/main.py`

---

## Block 1 — `app_state = {}`

```python
app_state = {}
```

Module-level dict that lives for the entire application lifecycle. All route handlers import this dict to access loaded models without circular imports.

**Why a plain dict and not a class?** A class would need instantiation and passing around. A module-level dict is accessible anywhere via `from api.main import app_state` — simple, but it is global state.

**Alternative:** FastAPI's `Request.state` — can attach state per request but not across requests. Use `app.state` attribute instead for application-wide state — `app.state.ranker = ranker.load()`. More idiomatic FastAPI, equally valid.

---

## Block 2 — `lifespan` context manager

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading models...")
    app_state["ranker"]   = ranker.load()
    app_state["eta"]      = eta_model.load()
    app_state["locations"] = pd.read_csv("data/locations.csv")
    trips = pd.read_csv("data/trips.csv")
    app_state["driver_profiles"] = build_driver_profiles(trips)
    app_state["trips"] = trips
    print("Ready.")
    yield
    app_state.clear()
```

`@asynccontextmanager` from contextlib — turns a generator function into a context manager. Code before `yield` runs on startup. Code after `yield` runs on shutdown.

`yield` is the dividing line. After this, the server starts accepting requests. When the server shuts down (Ctrl+C or container stop), execution resumes after `yield` for cleanup.

**Old approach (deprecated in recent FastAPI):** Using `@app.on_event("startup")` and `@app.on_event("shutdown")` decorators. The `lifespan` pattern is the current recommended approach.

**Why load `trips` into app_state?** The weekly endpoint needs it for `get_driver_locations()`. Loading once at startup vs reading the CSV every request is a 100× speed difference.

---

## Block 3 — CORS Middleware

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

CORS = Cross-Origin Resource Sharing. Without this, browsers block requests from a frontend (e.g., `localhost:3000`) to the API (`localhost:8000`). `"*"` allows all origins.

**In production:** Replace `"*"` with specific allowed origins like `["https://your-frontend.com"]`. The wildcard is fine for a demo/assignment.

---

## Block 4 — Router registration

```python
from api.routes import daily, weekly, admin
app.include_router(daily.router,  prefix="/predict")
app.include_router(weekly.router, prefix="/predict")
app.include_router(admin.router)
```

`include_router` — registers all routes defined in a module. `prefix="/predict"` means `@router.post("/daily")` inside `daily.py` becomes `POST /predict/daily` in the final API.

Import is inside the function body rather than at the top — avoids circular import issues (these modules import from `api.main`, which would create a circular dependency at module load time).

---

---

# FILE 7 — `api/google_client.py`

---

## Block 1 — `_has_key()`

```python
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

def _has_key():
    return bool(API_KEY and API_KEY != "your_api_key_here")
```

Double check: key exists AND is not the placeholder string from `.env.example`. If someone copies `.env.example` to `.env` without filling it in, this correctly identifies it as "no real key."

`bool(string)` — empty string is falsy, so `bool("")` is False.

---

## Block 2 — Real distance matrix request

```python
params = {
    "origins":       "|".join(origins),
    "destinations":  "|".join(destinations),
    "mode":          "driving",
    "departure_time": departure_time,
    "traffic_model": "best_guess",
    "key":           API_KEY,
}
```

`"|".join(origins)` — Google's Distance Matrix API expects multiple origins as a pipe-separated string: `"lat1,lng1|lat2,lng2|lat3,lng3"`.

`departure_time` — passing `"now"` tells Google to use current traffic conditions. This is what gives `duration_in_traffic` instead of just `duration` in the response.

`traffic_model: "best_guess"` — uses historical traffic data for the given time. Other options: `"optimistic"` (light traffic), `"pessimistic"` (heavy traffic). "best_guess" is appropriate for real planning.

```python
async with httpx.AsyncClient(timeout=10) as client:
    resp = await client.get(...)
```

`httpx.AsyncClient` — async HTTP client. `timeout=10` raises an exception if Google doesn't respond in 10 seconds.

`async with` — the context manager closes the connection cleanly after the request, even if an exception occurs. Alternative: `requests` library (synchronous), but that would block the entire server thread during the API call.

---

## Block 3 — Parsing real response

```python
for row in data.get("rows", []):
    for elem in row.get("elements", []):
        if elem["status"] == "OK":
            results.append({
                "distance_km":  round(elem["distance"]["value"] / 1000, 2),
                "duration_min": round(elem["duration_in_traffic"]["value"] / 60, 1),
            })
```

Google's response is nested: `rows[i].elements[j]` = result for origin i → destination j. Values are in meters and seconds, so we convert to km and minutes.

`data.get("rows", [])` — safe access: returns empty list if "rows" key is missing (error response from Google). Alternative: `data["rows"]` — would throw KeyError on error responses.

---

## Block 4 — Mock geocode with hash

```python
def _mock_geocode(address):
    seed = sum(ord(c) for c in address) % 1000
    lat = 26.8467 + (seed % 100 - 50) * 0.002
    lng = 80.9462 + (seed % 70  - 35) * 0.002
    return round(lat, 6), round(lng, 6)
```

`sum(ord(c) for c in address)` — sums ASCII values of all characters. This creates a deterministic "fingerprint" for the address string. Same address always → same seed → same coordinates.

`seed % 1000` — keeps seed bounded.

`(seed % 100 - 50) * 0.002` — generates a spread of ±50 × 0.002 = ±0.1 degrees (~11 km) from city center. Different addresses get different offsets because their ASCII sums differ.

**Why deterministic?** If the mock returned random coordinates, calling the endpoint twice for the same address would give different results — looks broken. Deterministic mock = consistent behavior.

---

---

# FILE 8 — `api/cache.py`

---

## Block 1 — Schema

```python
conn.execute("""
    CREATE TABLE IF NOT EXISTS cache (
        key       TEXT PRIMARY KEY,
        value     TEXT NOT NULL,
        saved_at  REAL NOT NULL
    )
""")
```

`TEXT PRIMARY KEY` — the SHA-256 hash key. Primary key auto-creates an index for O(log n) lookups.

`value TEXT` — JSON-serialized string of the API response. Could also use a BLOB, but TEXT is human-readable if you inspect the DB.

`saved_at REAL` — Unix timestamp (seconds since epoch) stored as floating point. Used for TTL check.

`CREATE TABLE IF NOT EXISTS` — idempotent. Calling `_connect()` multiple times doesn't crash.

---

## Block 2 — `_make_key()`

```python
def _make_key(namespace, payload):
    raw = f"{namespace}:{json.dumps(payload, sort_keys=True)}"
    return hashlib.sha256(raw.encode()).hexdigest()
```

SHA-256 produces a 64-character hex string. Collision probability is astronomically low (2⁻²⁵⁶) — effectively impossible to have two different requests map to the same key.

`sort_keys=True` — ensures `{"a":1,"b":2}` and `{"b":2,"a":1}` produce identical JSON strings before hashing.

`.encode()` — converts string to bytes before hashing (hashlib requires bytes input).

`.hexdigest()` — returns the hash as a hex string rather than raw bytes.

---

## Block 3 — `get()` / `set()`

```python
def get(namespace, payload):
    ...
    if time.time() - saved_at > TTL_SECONDS:
        return None  # stale
    return json.loads(value)
```

TTL check: if entry is older than 24 hours, treat as cache miss. The stale entry remains in the DB (lazy deletion) — cleared by `clear_expired()`.

`json.loads(value)` — deserializes the stored string back to a Python dict/list.

```python
def set(namespace, payload, result):
    conn.execute(
        "INSERT OR REPLACE INTO cache ...",
        (key, json.dumps(result), time.time())
    )
```

`INSERT OR REPLACE` — if the key already exists, replace it. Without `OR REPLACE`, re-caching the same request would raise a UNIQUE constraint violation.

---

---

# FILE 9 — `api/routes/daily.py`

---

## Block 1 — Pydantic Models

```python
class DailyRequest(BaseModel):
    driver_id: str
    date: str
    locations: List[str]

class DailyResponse(BaseModel):
    recommended_route: List[str]
    predicted_time: str
    confidence: float
    total_distance_km: float
    per_stop_eta_min: List[float]
    google_api_used: bool
```

**DailyRequest** — FastAPI validates incoming JSON against this. If `locations` is missing or not a list, FastAPI returns 422 automatically.

**DailyResponse** — used as `response_model=DailyResponse` in the route decorator. FastAPI serializes only these fields in the response and validates types. If the handler accidentally returns extra fields, they're stripped.

**`google_api_used: bool`** — extra field not in the assignment spec. This is a small but smart addition — tells the evaluator whether live Google data was used or mock. Shows thoughtfulness.

---

## Block 2 — `resolve_location()`

```python
async def resolve_location(loc_name, locations_df):
    row = locations_df[
        (locations_df["location_id"] == loc_name) |
        (locations_df["name"].str.lower() == loc_name.lower())
    ]
    if len(row) > 0:
        r = row.iloc[0]
        return {"id": loc_name, "lat": r["lat"], ...}
```

Two-condition lookup: match by ID ("L01") OR by name (case-insensitive). `str.lower()` on both sides handles "big bazaar" matching "Big Bazaar".

`row.iloc[0]` — first matching row. If multiple rows somehow match (shouldn't happen with our data), we take the first.

```python
    cached = api_cache.get("geocode", {"address": loc_name})
    if cached:
        lat, lng = cached["lat"], cached["lng"]
    else:
        lat, lng = await google_client.geocode(loc_name)
        if lat:
            api_cache.set("geocode", {"address": loc_name}, {"lat": lat, "lng": lng})
```

Cache check before calling Google. `if lat:` — only cache successful geocodes (lat=None means geocoding failed).

---

## Block 3 — Main handler flow

```python
ordered_ids, total_km = tsp_solve(ids, lats, lngs)

order_map   = {oid: i for i, oid in enumerate(ids)}
ordered_idx = [order_map[oid] for oid in ordered_ids]
o_lats  = [lats[i]  for i in ordered_idx]
```

After TSP returns `ordered_ids`, we need to re-derive the corresponding lats, lngs, and zones in the same new order.

`order_map` — reverse mapping from location ID to its original position index: `{"L01": 0, "L05": 1, ...}`. Used to find where each reordered stop was in the original lists.

`ordered_idx` — list of original indices in new order. Then `[lats[i] for i in ordered_idx]` re-orders lats to match.

**Why not store lats with IDs from the start?** The TSP solver returns indices, not dicts. Keeping coordinates in parallel lists is a deliberate simplicity choice for the solver interface.

---

---

# FILE 10 — `api/routes/weekly.py`

---

## Block 1 — `parse_week()`

```python
def parse_week(week_str):
    monday = datetime.strptime(f"{week_str}-1", "%G-W%V-%u")
    return monday
```

`%G` = ISO year, `%V` = ISO week number, `%u` = weekday (1=Monday). Appending `-1` forces parsing to Monday of that week.

**Why %G and not %Y?** For weeks near year boundaries (weeks 52/53 of one year and week 1 of next), the ISO year (`%G`) may differ from the calendar year (`%Y`). Using `%Y` would give a wrong date for week 1 of January.

---

## Block 2 — `get_driver_locations()`

```python
freq = driver_trips["stop_id"].value_counts()
common = freq.head(30).index.tolist()
locs = locations_df[locations_df["location_id"].isin(common)].copy()
locs["visit_count"] = locs["location_id"].map(freq).fillna(0)
```

`value_counts()` — returns a Series sorted by frequency, most-visited first.

`.head(30)` — top 30 most-visited locations. We limit to 30 to keep clustering reasonable (6 days × 5 avg stops per cluster).

`.copy()` on the filtered DataFrame — prevents `SettingWithCopyWarning` when we add `visit_count` column. Pandas requires explicit copy when slicing.

`locs["location_id"].map(freq)` — maps each location_id to its visit count from the freq Series. `.fillna(0)` for locations not in freq (shouldn't happen but safe).

---

## Block 3 — `cluster_by_day()`

```python
coords = locations[[" lat", "lng"]].values
k = min(n_days, len(locations))
km = KMeans(n_clusters=k, random_state=42, n_init=10)
labels = km.fit_predict(coords)
```

`[[" lat", "lng"]].values` — extracts a numpy array of shape (n, 2). KMeans needs a 2D array.

`n_init=10` — KMeans is sensitive to initial centroid placement. Running 10 initializations and picking the best result avoids bad local minima. Default was 10 in older sklearn, but explicitly setting it is good practice since the default changed to "auto" in sklearn 1.4.

`k = min(n_days, len(locations))` — prevents k > n_samples error from KMeans.

**Alternative clustering approaches:**
- **DBSCAN** — density-based, finds clusters of arbitrary shape, doesn't need k specified. But number of output clusters is unpredictable, which doesn't map cleanly to days.
- **Agglomerative clustering** — hierarchical, more interpretable, but slower for larger datasets.
- **Simple grid division** — divide city into a grid, assign grid cells to days. Faster but ignores actual stop distribution.

---

---

# FILE 11 — `api/routes/admin.py`

---

## Block 1 — Module-level state

```python
startup_time = time.time()
retrain_log  = []
```

These are module-level variables — they persist for the entire server process lifetime. `startup_time` is set when the module first loads (at import time, before first request). `retrain_log` accumulates entries across all retrain calls in this session.

**Limitation:** If the server restarts, `retrain_log` is lost. Production alternative: persist to DB.

---

## Block 2 — `_run_retrain()`

```python
def _run_retrain():
    start = time.time()
    try:
        trips = pd.read_csv("data/trips.csv")
        ...
        app_state["ranker"] = new_ranker
        app_state["eta"]    = new_eta
        ...
        retrain_log.append({"status": "success", ...})
    except Exception as e:
        retrain_log.append({"status": "failed", "error": str(e), ...})
```

The broad `except Exception` is intentional here — retrain is a background task and we don't want unhandled exceptions silently killing the task. We log the error instead of crashing.

**Hot swap:** Directly replacing values in `app_state` dict. Since Python GIL (Global Interpreter Lock) ensures dict operations are thread-safe for simple assignments, this won't corrupt state even if requests are happening concurrently.

---

## Block 3 — `retrain()` endpoint

```python
@router.post("/retrain", response_model=RetrainResponse)
def retrain(background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_retrain)
    return RetrainResponse(status="started", message="...")
```

`BackgroundTasks` is a FastAPI dependency injected automatically. `.add_task(func)` schedules the function to run after the response is sent — the endpoint returns immediately while training runs in the background.

**Alternative:** Use Celery + Redis for proper distributed background tasks. Necessary in production with multiple workers, overkill for this assignment.

---

---

# FILE 12 — `scripts/train.py`

---

## Block 1 — sys.path manipulation

```python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
```

`__file__` = path of the current script (`scripts/train.py`). `os.path.dirname(__file__)` = `scripts/`. `..` goes up one level = project root. `os.path.abspath()` makes it absolute.

`sys.path.insert(0, ...)` — adds the project root to the beginning of Python's module search path. Without this, `from model import ranker` would fail because Python doesn't know where `model/` is when running `scripts/train.py` directly.

**Alternative:** Run as `python -m scripts.train` from project root. The `-m` flag runs as a module, which sets the working directory correctly. Or install the project as a package with `pip install -e .`.

---

## Block 2 — Auto-generate data if missing

```python
if not os.path.exists("data/trips.csv"):
    print("\nNo trip data found. Generating it first...")
    os.system("python data/generate_data.py")
```

`os.system()` runs a shell command. Alternative: `subprocess.run()` with error checking — more robust, captures output, handles failures.

This small convenience makes the script "runnable from scratch" without manually running two commands.

---

---

# FILE 13 — `tests/test_api.py`

---

## Block 1 — `sys.path` fix (same as train.py)

```python
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
```

Same path manipulation — needed so `from model.tsp import ...` works when pytest runs from the project root.

**Alternative:** Create a `conftest.py` in the project root with this path manipulation. Pytest loads conftest.py automatically, so all test files inherit the path.

---

## Block 2 — `class TestTSP`

```python
class TestTSP:
    def test_two_opt_does_not_make_route_longer(self):
        mat  = distance_matrix(lats, lngs)
        greedy_len = route_length([0,1,2,3,4], mat)
        _, opt_len = two_opt([0,1,2,3,4], mat)
        assert opt_len <= greedy_len + 1e-9
```

This test verifies the **mathematical invariant** of 2-opt: it must not make routes longer. `1e-9` tolerance handles floating point arithmetic.

Grouping tests in classes isn't required in pytest (functions work too), but classes group related tests visually and allow shared fixtures with `@pytest.fixture`.

---

## Block 3 — pytest fixtures

```python
@pytest.fixture(scope="class")
def trips(self):
    if not os.path.exists("data/trips.csv"):
        pytest.skip("Run generate_data.py first")
    return pd.read_csv("data/trips.csv")
```

`scope="class"` — fixture is created once per test class, not once per test method. Avoids reading the CSV 5 times.

`pytest.skip(...)` — cleanly skips tests when preconditions aren't met, instead of failing with confusing errors.

---

## Block 4 — `TestCache.test_key_is_deterministic`

```python
def test_key_is_deterministic(self):
    k1 = _make_key("ns", {"a": 1, "b": 2})
    k2 = _make_key("ns", {"b": 2, "a": 1})
    assert k1 == k2
```

Tests that dict key ordering doesn't affect cache key. This is the exact bug that `sort_keys=True` in `json.dumps()` prevents. Having this test means if someone accidentally removes `sort_keys=True`, the test catches it immediately.

---

---

# FILE 14 — `monitoring/dashboard.py`

---

## Block 1 — Environment variable for API URL

```python
API_BASE = os.getenv("API_URL", "http://localhost:8000")
```

Default is localhost. In Docker Compose, the dashboard service sets `API_URL=http://api:8000` (using the service name as hostname). This one variable makes the same code work locally and in Docker without changes.

---

## Block 2 — `fetch_metrics()` / `fetch_health()`

```python
def fetch_metrics():
    try:
        return requests.get(f"{API_BASE}/metrics", timeout=5).json()
    except Exception:
        return None
```

`timeout=5` — dashboard shouldn't hang waiting for API. If API is down, returns None, and the dashboard shows "API not available" gracefully.

Broad `except Exception` — network errors, JSON parse errors, all handled by returning None. Dashboard handles None explicitly rather than crashing.

---

## Block 3 — Streamlit layout

```python
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Trips", metrics.get("total_trips", "—"))
```

`st.columns(4)` — creates 4 equal-width columns in one line. `col1.metric(label, value)` renders a big number card. `"—"` fallback for missing data.

```python
c1.success("✓ XGBoost Ranker") if model_files.get("ranker") else c1.error("✗ XGBoost Ranker missing")
```

Ternary with Streamlit components — conditional rendering based on model file existence. One-liner keeps it readable.

---

## Block 4 — Live prediction form

```python
with st.form("test_predict"):
    driver = st.selectbox("Driver", [f"D{i}" for i in range(1, 11)])
    ...
    submit = st.form_submit_button("Predict")

if submit:
    payload = {"driver_id": driver, ...}
    resp = requests.post(f"{API_BASE}/predict/daily", json=payload, timeout=10)
```

`st.form` — groups inputs so they don't re-run on every keystroke. Only triggers on submit button click.

`requests.post(..., json=payload)` — synchronous HTTP from Streamlit to the API. Streamlit runs in its own thread/process so sync HTTP is fine here (unlike FastAPI where we'd use `httpx.AsyncClient`).

---

---

# FILE 15 — `Dockerfile`

---

```dockerfile
FROM python:3.11-slim
```

`slim` variant — stripped-down Python image (~150MB vs ~900MB for full). Missing things like gcc, but we don't compile anything here.

**Alternative:** `python:3.11-alpine` — even smaller (~50MB) but Alpine uses musl libc and some Python packages (especially numpy, pandas) need extra compilation steps. More setup, not worth it.

```dockerfile
WORKDIR /app
```

All subsequent commands run from `/app`. Creates the directory if it doesn't exist.

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```

**Layer caching optimization:** Copy requirements first and install, then copy code. Docker caches each layer. If you only change Python code (not requirements), Docker reuses the cached pip install layer — rebuild is much faster.

If you do `COPY . .` first and THEN pip install, any code change invalidates the pip cache, forcing full reinstall every time.

`--no-cache-dir` — don't store pip's download cache in the image. Reduces image size.

```dockerfile
RUN python data/generate_data.py && python scripts/train.py
```

Bakes trained models into the image at build time. Cold-start time when container starts = essentially zero for model loading.

**Trade-off:** Image is larger (models + data). But for a submission, this is better than requiring the evaluator to run training manually after starting the container.

```dockerfile
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`EXPOSE 8000` — documents that the container listens on 8000. Doesn't actually publish the port (that's done in `docker run -p` or `docker-compose ports`).

`--host 0.0.0.0` — listens on all interfaces. Default is `127.0.0.1` which would only be accessible from inside the container. `0.0.0.0` makes it reachable from outside.

---

---

# FILE 16 — `docker-compose.yml`

---

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./model/saved:/app/model/saved
```

`build: .` — builds from `Dockerfile` in current directory.

`env_file: .env` — loads environment variables from `.env` file. API key goes here without being in the image.

`volumes:` — bind mounts. `./data:/app/data` means the local `data/` folder appears at `/app/data` inside the container. This persists generated CSV files and SQLite cache across container restarts.

`./model/saved:/app/model/saved` — persists trained models. Without this, models are baked into the image (which we did in Dockerfile), but this also allows retraining to persist on disk.

```yaml
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Docker's built-in health check. Every 30 seconds, Docker curls `/health`. If it fails 3 times in a row, container is marked "unhealthy." `restart: unless-stopped` would restart it.

```yaml
  dashboard:
    environment:
      - API_URL=http://api:8000
    depends_on:
      - api
```

`http://api:8000` — in Docker Compose, service names are DNS-resolvable hostnames. The dashboard container reaches the API container by its service name.

`depends_on: api` — Docker starts `api` before `dashboard`. Doesn't wait for api to be healthy, just for the container to start. For proper health-based waiting, use `condition: service_healthy`.

---

---

# FILE 17 — `requirements.txt`

---

```
fastapi==0.110.0
uvicorn[standard]==0.29.0
```

`uvicorn[standard]` — installs uvicorn with extras: `websockets` and `httptools` for better performance. Without `[standard]`, uvicorn falls back to slower pure-Python implementations.

```
scikit-learn==1.4.1
xgboost==2.0.3
```

Both pinned. sklearn 1.4 and XGBoost 2.0 are API-stable — no breaking changes expected within minor versions, but major bumps can break things.

```
httpx==0.27.0
```

For async Google API calls. Alternative: `aiohttp` — also async, slightly more performant for high-concurrency, slightly more verbose API.

```
streamlit==1.32.2
pytest==8.1.0
pytest-asyncio==0.23.6
```

`pytest-asyncio` — needed to test async functions with pytest. Without it, `async def test_...` functions don't run correctly.

---

---

# FILE 18 — `.env.example`

---

```
GOOGLE_MAPS_API_KEY=your_api_key_here
```

This file is committed. `.env` (with real key) is gitignored. Standard convention everyone on a team understands instantly.

**Production alternative:** Use a secrets manager (AWS Secrets Manager, HashiCorp Vault) instead of `.env` files. Environment variables in `.env` files can leak if accidentally committed or if server is compromised.

---

---

# FILE 19 — `.gitignore`

---

```gitignore
.env
__pycache__/
*.pyc
model/saved/
data/trips.csv
data/locations.csv
data/api_cache.db
.DS_Store
```

**`.env`** — API key. Never commit this.

**`__pycache__/` and `*.pyc`** — Python's compiled bytecode cache. Generated automatically, machine-specific, adds noise to diffs.

**`model/saved/`** — trained model binary files. Large, binary (can't diff), regenerable from `scripts/train.py`.

**`data/trips.csv`** — generated from `generate_data.py`. Reproducible, no need to track.

**`data/api_cache.db`** — runtime cache. Different on every machine.

**`.DS_Store`** — macOS metadata files. Meaningless to other contributors.

**Alternative:** Use `git rm --cached .DS_Store` to remove already-tracked files after adding to `.gitignore`. Just adding to `.gitignore` doesn't remove already-tracked files.

---

*Every file. Every block. Every alternative. Done.*
