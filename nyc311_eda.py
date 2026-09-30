"""
NYC 311 Exploratory Data Analysis — fetch and clean
Assignment 4.5

Usage:
    pip install pandas requests
    python nyc311_eda.py

Writes five aggregated CSVs, small enough to drop straight into Tableau.

Set PEEK = True to pull only 1000 rows and print the column names —
useful the first time, since Socrata field names can change.
"""

import io

import pandas as pd
import requests

# ---------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------

PEEK = False          # True = fetch 1000 rows and stop, to check the schema
START = "2024-03-01"
END = "2024-03-31"    # a single full month, roughly 267k rows
LIMIT = 300000

DATASET = "erm2-nwe9"   # 311 Service Requests from 2020 to Present
URL = f"https://data.cityofnewyork.us/resource/{DATASET}.csv"

COLS = [
    "unique_key",
    "created_date",
    "closed_date",
    "agency",
    "complaint_type",
    "borough",
]

# ---------------------------------------------------------------
# 1. Fetch
# ---------------------------------------------------------------
# Only six of the dataset's forty-odd columns, filtered server side.
# Downloading the whole thing is not an option: the dataset runs to
# tens of millions of rows.
#
# $order matters. Without it the API returns rows in an unspecified
# order, and if the result hits the row cap you get an arbitrary slice
# of the window with no warning that anything was dropped.

params = {
    "$select": ",".join(COLS),
    "$order": "created_date",
    "$where": f"created_date between '{START}T00:00:00' and '{END}T23:59:59'",
    "$limit": 1000 if PEEK else LIMIT,
}

print("Downloading...")
resp = requests.get(URL, params=params, timeout=300)
resp.raise_for_status()
df = pd.read_csv(io.StringIO(resp.text))
print(f"Got {len(df):,} rows")
print("\nColumns:")
print(df.columns.tolist())
print("\nFirst three rows:")
print(df.head(3))

if PEEK:
    print("\n>>> Schema looks right? Set PEEK = False and run again.")
    raise SystemExit

# A result exactly at the limit means the response was truncated.
if len(df) == LIMIT:
    print(f"\nWARNING: got exactly {LIMIT:,} rows — the response was capped.")
    print("Narrow the date window or raise LIMIT.")

# ---------------------------------------------------------------
# 2. Clean
# ---------------------------------------------------------------

before = len(df)

# Timestamps arrive as strings
df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
df["closed_date"] = pd.to_datetime(df["closed_date"], errors="coerce")

df = df.drop_duplicates(subset="unique_key")

# Borough labels are inconsistently cased; "Unspecified" is not a borough
df["borough"] = df["borough"].str.strip().str.title()
df = df[df["borough"].notna()]
df = df[df["borough"] != "Unspecified"]

# Same for complaint type — "HEAT/HOT WATER" and "Heat/Hot Water" both appear
df["complaint_type"] = df["complaint_type"].str.strip().str.title()

# Derived variables
df["response_hours"] = (
    (df["closed_date"] - df["created_date"]).dt.total_seconds() / 3600
)
df["weekday"] = df["created_date"].dt.day_name()
df["hour"] = df["created_date"].dt.hour

print(f"\n{before:,} rows before cleaning -> {len(df):,} after")
print(f"Dropped {before - len(df):,} rows")

# Two kinds of impossible durations. Both are excluded from timing work
# but kept in the counts, since the request itself is real.
bad = df["response_hours"] < 0
too_long = df["response_hours"] > 24 * 365
print(f"Closed before they opened: {bad.sum():,} (excluded from durations)")
print(f"Open longer than a year:   {too_long.sum():,} (excluded from durations)")
df.loc[bad | too_long, "response_hours"] = pd.NA

# ---------------------------------------------------------------
# 3. One aggregated file per question
# ---------------------------------------------------------------

# --- Overview: the twenty most common complaint types ---
overview = (
    df["complaint_type"]
    .value_counts()
    .head(20)
    .rename_axis("complaint_type")
    .reset_index(name="count")
)
overview.to_csv("q0_overview.csv", index=False)

# --- Q1: what does each borough complain about? ---
# Everything outside the top ten becomes "Other", otherwise a stacked
# chart turns into forty unreadable slivers.
top10 = df["complaint_type"].value_counts().head(10).index
df["complaint_grouped"] = df["complaint_type"].where(
    df["complaint_type"].isin(top10), "Other"
)

q1 = (
    df.groupby(["borough", "complaint_grouped"])
    .size()
    .reset_index(name="count")
)
# Percent as well as count, so mix can be compared independently of size
q1["pct_of_borough"] = (
    q1["count"] / q1.groupby("borough")["count"].transform("sum") * 100
).round(1)
q1.to_csv("q1_borough_mix.csv", index=False)

# --- Q2: how long do agencies take to close a request? ---
q2 = (
    df[df["response_hours"].notna()]
    .groupby("agency")["response_hours"]
    .agg(median_hours="median", mean_hours="mean", n="size")
    .reset_index()
)
q2 = q2[q2["n"] >= 100]            # small samples are not informative
q2["median_days"] = (q2["median_hours"] / 24).round(2)
q2 = q2.sort_values("median_hours")
q2.to_csv("q2_agency_response.csv", index=False)

# --- Q3: when do requests arrive? ---
q3 = df.groupby(["weekday", "hour"]).size().reset_index(name="count")
q3.to_csv("q3_time_heatmap.csv", index=False)

# Noise on its own, for contrast against the overall rhythm
noise = df[df["complaint_type"].str.contains("Noise", na=False)]
q3b = noise.groupby(["weekday", "hour"]).size().reset_index(name="count")
q3b.to_csv("q3b_noise_heatmap.csv", index=False)

# ---------------------------------------------------------------
# 4. Console summary, to see which questions have something in them
# ---------------------------------------------------------------

print("\n" + "=" * 55)
print("Q1  Leading complaint type by borough")
print("=" * 55)
for b in sorted(df["borough"].unique()):
    sub = q1[(q1["borough"] == b) & (q1["complaint_grouped"] != "Other")]
    if len(sub):
        top = sub.nlargest(1, "pct_of_borough").iloc[0]
        print(f"  {b:<15} {top['complaint_grouped']:<28} {top['pct_of_borough']:>5.1f}%")

print("\n" + "=" * 55)
print("Q2  Fastest and slowest agencies (median days)")
print("=" * 55)
print("  Fastest:")
for _, r in q2.head(5).iterrows():
    print(f"    {r['agency']:<10} {r['median_days']:>8.2f} days   (n={int(r['n']):,})")
print("  Slowest:")
for _, r in q2.tail(5).iloc[::-1].iterrows():
    print(f"    {r['agency']:<10} {r['median_days']:>8.2f} days   (n={int(r['n']):,})")

print("\n" + "=" * 55)
print("Q3  Busiest hours for noise complaints")
print("=" * 55)
for _, r in q3b.nlargest(5, "count").iterrows():
    print(f"    {r['weekday']:<10} {int(r['hour']):>2}:00   {int(r['count']):,}")

print("\nDone. Five CSVs written:")
print("  q0_overview.csv         complaint types, ranked")
print("  q1_borough_mix.csv      complaint mix by borough")
print("  q2_agency_response.csv  response time by agency")
print("  q3_time_heatmap.csv     all requests by weekday and hour")
print("  q3b_noise_heatmap.csv   noise requests by weekday and hour")
