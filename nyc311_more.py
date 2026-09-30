"""
NYC 311 Exploratory Data Analysis — second round of questions
Assignment 4.5

Usage:
    python nyc311_more.py

The first run downloads the raw data and caches it as raw_cache.csv.
Later runs read the cache and finish in a few seconds.

Writes four more CSVs, each calling for a different chart type from
the ones in nyc311_eda.py:
    q4_daily.csv          line      - daily volume across the month
    q5_sameday.csv        bar       - share of requests closed within a day
    q6_peak_hour.csv      dot plot  - each complaint type's busiest hour
    q7_heat_heatmap.csv   heatmap   - heat and hot water, by weekday and hour
"""

import io
import os

import pandas as pd
import requests

# ---------------------------------------------------------------
# Configuration (matches nyc311_eda.py)
# ---------------------------------------------------------------

START = "2024-03-01"
END = "2024-03-31"
LIMIT = 300000
CACHE = "raw_cache.csv"

DATASET = "erm2-nwe9"
URL = f"https://data.cityofnewyork.us/resource/{DATASET}.csv"

COLS = ["unique_key", "created_date", "closed_date",
        "agency", "complaint_type", "borough"]

# ---------------------------------------------------------------
# 1. Fetch, or read the cache
# ---------------------------------------------------------------

if os.path.exists(CACHE):
    print(f"Reading {CACHE}...")
    df = pd.read_csv(CACHE)
else:
    print("Downloading (this happens once)...")
    params = {
        "$select": ",".join(COLS),
        "$order": "created_date",
        "$where": f"created_date between '{START}T00:00:00' and '{END}T23:59:59'",
        "$limit": LIMIT,
    }
    resp = requests.get(URL, params=params, timeout=300)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    df.to_csv(CACHE, index=False)
    print(f"Cached to {CACHE}")

print(f"{len(df):,} rows")

if len(df) == LIMIT:
    print(f"WARNING: got exactly {LIMIT:,} rows — the response was capped.")

# ---------------------------------------------------------------
# 2. Clean (same logic as nyc311_eda.py)
# ---------------------------------------------------------------

df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
df["closed_date"] = pd.to_datetime(df["closed_date"], errors="coerce")
df = df.drop_duplicates(subset="unique_key")

df["borough"] = df["borough"].str.strip().str.title()
df = df[df["borough"].notna() & (df["borough"] != "Unspecified")]
df["complaint_type"] = df["complaint_type"].str.strip().str.title()

df["response_hours"] = (df["closed_date"] - df["created_date"]).dt.total_seconds() / 3600
bad = (df["response_hours"] < 0) | (df["response_hours"] > 24 * 365)
df.loc[bad, "response_hours"] = pd.NA

df["date"] = df["created_date"].dt.date
df["weekday"] = df["created_date"].dt.day_name()
df["hour"] = df["created_date"].dt.hour

top10 = df["complaint_type"].value_counts().head(10).index
df["complaint_grouped"] = df["complaint_type"].where(
    df["complaint_type"].isin(top10), "Other"
)

# ---------------------------------------------------------------
# q4  Daily volume — line chart
# ---------------------------------------------------------------

q4 = df.groupby("date").size().reset_index(name="count")
q4["weekday"] = pd.to_datetime(q4["date"]).dt.day_name()
q4["is_weekend"] = q4["weekday"].isin(["Saturday", "Sunday"])
q4.to_csv("q4_daily.csv", index=False)

peak_day = q4.nlargest(1, "count").iloc[0]
quiet_day = q4.nsmallest(1, "count").iloc[0]

# ---------------------------------------------------------------
# q5  Same-day closure rate — bar chart
# ---------------------------------------------------------------
# This is the counterweight to q2's median response time. An agency
# closing nearly everything within 24 hours is almost certainly marking
# requests closed on arrival, not resolving them that fast.

closed = df[df["response_hours"].notna()].copy()
closed["same_day"] = closed["response_hours"] < 24

q5 = (
    closed.groupby("agency")
    .agg(same_day_pct=("same_day", "mean"), n=("same_day", "size"))
    .reset_index()
)
q5["same_day_pct"] = (q5["same_day_pct"] * 100).round(1)
q5 = q5[q5["n"] >= 100].sort_values("same_day_pct", ascending=False)
q5.to_csv("q5_sameday.csv", index=False)

# ---------------------------------------------------------------
# q6  Busiest hour per complaint type — dot plot
# ---------------------------------------------------------------
# Each type's hourly distribution, normalised to its own volume, then
# reduced to the single hour where it peaks. Plotted on one 24-hour
# axis, ten types separate into clear clusters.

by_type_hour = (
    df[df["complaint_grouped"] != "Other"]
    .groupby(["complaint_grouped", "hour"])
    .size()
    .reset_index(name="count")
)
by_type_hour["pct_of_type"] = (
    by_type_hour["count"]
    / by_type_hour.groupby("complaint_grouped")["count"].transform("sum")
    * 100
).round(2)

# Full matrix, in case a type-by-hour heatmap is wanted instead
by_type_hour.to_csv("q6_type_hour_full.csv", index=False)

q6 = (
    by_type_hour.loc[by_type_hour.groupby("complaint_grouped")["count"].idxmax()]
    .rename(columns={"hour": "peak_hour", "pct_of_type": "peak_share"})
    .sort_values("peak_hour")
    .reset_index(drop=True)
)
q6["total"] = q6["complaint_grouped"].map(df["complaint_grouped"].value_counts())
q6.to_csv("q6_peak_hour.csv", index=False)

# ---------------------------------------------------------------
# q7  Heat and hot water by weekday and hour — heatmap
# ---------------------------------------------------------------
# A third rhythm to set against the overall pattern and against noise.

heat = df[df["complaint_type"].str.contains("Heat", na=False)]
q7 = heat.groupby(["weekday", "hour"]).size().reset_index(name="count")
q7.to_csv("q7_heat_heatmap.csv", index=False)

# ---------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------

print("\n" + "=" * 58)
print("q4  Daily volume")
print("=" * 58)
print(f"  Busiest:  {peak_day['date']} ({peak_day['weekday']})  {peak_day['count']:,}")
print(f"  Quietest: {quiet_day['date']} ({quiet_day['weekday']})  {quiet_day['count']:,}")
print(f"  Weekday average: {q4[~q4['is_weekend']]['count'].mean():,.0f}")
print(f"  Weekend average: {q4[q4['is_weekend']]['count'].mean():,.0f}")

print("\n" + "=" * 58)
print("q5  Share closed within 24 hours")
print("=" * 58)
for _, r in q5.head(5).iterrows():
    print(f"  {r['agency']:<8} {r['same_day_pct']:>6.1f}%   (n={int(r['n']):,})")
print("  ...")
for _, r in q5.tail(3).iterrows():
    print(f"  {r['agency']:<8} {r['same_day_pct']:>6.1f}%   (n={int(r['n']):,})")

print("\n" + "=" * 58)
print("q6  Busiest hour, by complaint type")
print("=" * 58)
for _, r in q6.iterrows():
    print(
        f"  {int(r['peak_hour']):>2}:00  {r['complaint_grouped']:<26}"
        f" {r['peak_share']:>5.2f}% of that type's month"
    )

print("\n" + "=" * 58)
print("q7  Busiest hours for heat and hot water")
print("=" * 58)
for _, r in q7.nlargest(5, "count").iterrows():
    print(f"  {r['weekday']:<10} {int(r['hour']):>2}:00   {int(r['count']):,}")

print("\nWritten:")
print("  q4_daily.csv           line     - daily volume")
print("  q5_sameday.csv         bar      - same-day closure rate")
print("  q6_peak_hour.csv       dot plot - busiest hour per type")
print("  q6_type_hour_full.csv  (spare)  - full type x hour matrix")
print("  q7_heat_heatmap.csv    heatmap  - heat and hot water timing")
