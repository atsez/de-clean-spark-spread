"""German clean spark spread: the generation margin of a benchmark gas-fired plant.

    clean spark spread = power - gas / efficiency - carbon * emissions factor      (EUR/MWh of power)

Inputs are three daily price series, one CSV per leg with columns date,price:
    power   German day-ahead baseload, EUR/MWh        (Bloomberg ELGBDAHD BCFV Index)
    gas     TTF front-month, EUR/MWh of gas            (Bloomberg TTFG1MON BCFV Index)
    carbon  EUA Dec-26, EUR per tonne of CO2           (Bloomberg EEUAM Z26 Index)

The legs trade on slightly different calendars, so they are joined on dates where all three
settled. Every spread is then built from three same-day prices.

    python3 spark_spread.py --data data            # writes results/results.md and results/spread.png
"""
from __future__ import annotations

import argparse
import os

import pandas as pd

EFFICIENCY = 0.50        # benchmark CCGT, MWh of power per MWh of gas
EMISSIONS = 0.37         # tCO2 per MWh of power for that plant
RECENT_DAYS = 20         # "recent" window for the driver split, about one trading month


def load_leg(path: str, name: str) -> pd.Series:
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.dropna().drop_duplicates("date").sort_values("date")
    return df.set_index("date")["price"].rename(name)


def join_legs(power: pd.Series, gas: pd.Series, carbon: pd.Series) -> tuple[pd.DataFrame, int]:
    """Inner join on date. Returns the joined frame and how many dates were dropped."""
    all_dates = power.index.union(gas.index).union(carbon.index)
    joined = pd.concat([power, gas, carbon], axis=1, join="inner")
    return joined, len(all_dates) - len(joined)


def clean_spark_spread(df: pd.DataFrame, eff: float = EFFICIENCY, ef: float = EMISSIONS) -> pd.DataFrame:
    out = df.copy()
    out["gas_cost"] = out["gas"] / eff               # EUR of gas burned per MWh of power
    out["carbon_cost"] = out["carbon"] * ef          # EUR of allowances per MWh of power
    out["spread"] = out["power"] - out["gas_cost"] - out["carbon_cost"]
    return out


def summary(s: pd.Series) -> dict:
    return {"current": s.iloc[-1], "mean": s.mean(), "median": s.median(),
            "q1": s.quantile(0.25), "q3": s.quantile(0.75), "min": s.min(), "max": s.max(),
            "days_negative": (s < 0).mean()}


def driver_split(df: pd.DataFrame, n: int = RECENT_DAYS) -> dict:
    """Recent average minus full-period average for each leg, in EUR/MWh of power.
    Spread change = power change - gas cost change - carbon cost change, exactly."""
    recent, full = df.iloc[-n:].mean(), df.mean()
    d = recent - full
    return {"power": d["power"], "gas_cost": d["gas_cost"], "carbon_cost": d["carbon_cost"], "spread": d["spread"]}


def plot(df: pd.DataFrame, path: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(df.index, df["spread"], lw=0.8, color="#1f5aa6", label="daily clean spark spread")
    ax.plot(df.index, df["spread"].rolling(20).mean(), lw=1.8, color="#d1762b", label="20-day average")
    ax.axhline(0, color="#1a1a1a", lw=0.8)
    ax.axhline(df["spread"].mean(), color="#8a8a8a", lw=1, ls="--", label="full-period average")
    ax.set_ylabel("EUR/MWh")
    ax.set_title("German clean spark spread, day-ahead baseload, 50% efficiency CCGT", loc="left", fontsize=10)
    ax.legend(fontsize=8, frameon=False, loc="upper left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data", help="folder with power.csv, gas.csv, carbon.csv")
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    legs = [load_leg(os.path.join(args.data, f"{n}.csv"), n) for n in ("power", "gas", "carbon")]
    joined, dropped = join_legs(*legs)
    df = clean_spark_spread(joined)
    st, dr = summary(df["spread"]), driver_split(df)
    plot(df, os.path.join(args.out, "spread.png"))

    f = lambda v: f"{v:+.2f}"
    L = ["# Results", "",
         f"{len(df)} common trading days from {df.index[0]:%d %b %Y} to {df.index[-1]:%d %b %Y}, "
         f"{dropped} non-common days dropped. Benchmark plant {EFFICIENCY:.0%} efficient, {EMISSIONS} tCO2/MWh.", "",
         "## Where the spread sits (EUR/MWh)", "",
         "| metric | value |", "|---|---|",
         f"| current | {f(st['current'])} |", f"| average | {f(st['mean'])} |", f"| median | {f(st['median'])} |",
         f"| middle 50% of days | {f(st['q1'])} to {f(st['q3'])} |", f"| full range | {f(st['min'])} to {f(st['max'])} |",
         f"| share of days negative | {st['days_negative']:.0%} |", "",
         f"## What moved it, last {RECENT_DAYS} days against the full-period average (EUR/MWh of power)", "",
         "| leg | change |", "|---|---|",
         f"| power | {f(dr['power'])} |", f"| gas cost | {f(dr['gas_cost'])} |", f"| carbon cost | {f(dr['carbon_cost'])} |",
         f"| spread (power - gas - carbon) | {f(dr['spread'])} |", "",
         "![spread](spread.png)", ""]
    open(os.path.join(args.out, "results.md"), "w").write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
