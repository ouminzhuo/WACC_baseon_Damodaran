#!/usr/bin/env python3
"""Refresh WHT_ctry.csv from online sources (manual-assisted).

Why manual-assisted?
- Some environments block direct access to tax source sites.
- This tool still enforces a repeatable workflow: fetch online values, then write
  timestamped rows with source URLs.

Usage example:
  python americas-wacc/scripts/refresh_wht_table.py \
    --out WHT_ctry.csv \
    --set "Canada=0.25|https://taxsummaries.pwc.com/canada/corporate/withholding-taxes" \
    --set "Brazil=0.15|https://taxsummaries.pwc.com/brazil/corporate/withholding-taxes"
"""

from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Write timestamped WHT country table")
    parser.add_argument("--out", default="WHT_ctry.csv", help="Output CSV path")
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        help='Entry format: "Country=rate|source_url" (rate can be 0.15 or 15%)',
    )
    args = parser.parse_args()

    rows = []
    today = date.today().isoformat()
    for raw in args.set:
        left, url = raw.split("|", 1)
        country, rate = left.split("=", 1)
        rate = rate.strip()
        if rate.endswith("%"):
            rate = str(float(rate[:-1]) / 100.0)
        rows.append(
            {
                "country": country.strip(),
                "withholding_tax": rate,
                "source_url": url.strip(),
                "collected_on": today,
                "notes": "online refreshed",
            }
        )

    if not rows:
        raise SystemExit("No --set provided. Nothing to write.")

    out = Path(args.out)
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["country", "withholding_tax", "source_url", "collected_on", "notes"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
