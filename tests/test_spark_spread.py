import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from spark_spread import join_legs, clean_spark_spread, driver_split   # noqa: E402


def s(vals, dates):
    return pd.Series(vals, index=pd.to_datetime(dates), dtype=float)


def test_formula_by_hand():
    df = pd.DataFrame({"power": [100.0], "gas": [30.0], "carbon": [70.0]})
    out = clean_spark_spread(df, eff=0.5, ef=0.37)
    assert abs(out["spread"].iloc[0] - (100 - 60 - 25.9)) < 1e-12


def test_join_keeps_only_common_dates():
    p = s([1, 2, 3], ["2026-01-01", "2026-01-02", "2026-01-05"])
    g = s([1, 2], ["2026-01-02", "2026-01-05"])
    c = s([1, 2, 3], ["2026-01-01", "2026-01-02", "2026-01-05"])
    joined, dropped = join_legs(p.rename("power"), g.rename("gas"), c.rename("carbon"))
    assert list(joined.index.strftime("%Y-%m-%d")) == ["2026-01-02", "2026-01-05"]
    assert dropped == 1


def test_driver_split_adds_up():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"power": rng.normal(90, 20, 100), "gas": rng.normal(30, 3, 100), "carbon": rng.normal(70, 5, 100)})
    d = driver_split(clean_spark_spread(df), n=20)
    assert abs(d["spread"] - (d["power"] - d["gas_cost"] - d["carbon_cost"])) < 1e-9
