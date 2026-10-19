"""Synthetic sample data so the pipeline runs without a Bloomberg Terminal.

Writes data/power.csv, data/gas.csv and data/carbon.csv with roughly realistic levels and
volatility, and deliberately misaligned calendars (a few dates missing from one leg) so the
date join has something to do. These numbers are made up and are not market data.
"""
import os

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
dates = pd.bdate_range("2024-01-08", "2026-07-07")
n = len(dates)

gas = 30 + np.cumsum(rng.normal(0, 0.6, n)).clip(-12, 25)                 # EUR/MWh
carbon = 70 + np.cumsum(rng.normal(0, 0.8, n)).clip(-15, 15)             # EUR/t
power = gas / 0.5 + carbon * 0.37 - 12 + rng.standard_t(3, n) * 18       # fat-tailed day-ahead noise

os.makedirs("data", exist_ok=True)
drop = rng.choice(n, 6, replace=False)                                   # gas missing on six days
keep = np.setdiff1d(np.arange(n), drop)
pd.DataFrame({"date": dates, "price": power.round(2)}).to_csv("data/power.csv", index=False)
pd.DataFrame({"date": dates[keep], "price": gas[keep].round(3)}).to_csv("data/gas.csv", index=False)
pd.DataFrame({"date": dates, "price": carbon.round(2)}).to_csv("data/carbon.csv", index=False)
print(f"wrote {n} synthetic days to data/, gas missing on {len(drop)}")
