#!/usr/bin/env python3
"""Compute nominal and real WACC for Americas focus countries.

This script uses the formulas defined in the americas-wacc skill and can
optionally resolve company default spread from repository ICR_table.csv.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _parse_percent(value: Any) -> float:
    """Convert strings like '3.25%' or numbers to decimal (0.0325)."""
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if text.endswith("%"):
        return float(text[:-1]) / 100.0
    return float(text)


def load_icr_table(csv_path: Path) -> List[Tuple[float, float, str, float]]:
    rows: List[Tuple[float, float, str, float]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lower = row.get("ICR_lower_edge", "").strip()
            upper = row.get("ICR_greater_edge", "").strip()
            rating = row.get("Rating is", "").strip()
            spread_raw = row.get("Spread is", "").strip()
            if not lower or not upper or not rating or not spread_raw:
                continue
            rows.append((float(lower), float(upper), rating, _parse_percent(spread_raw)))
    if not rows:
        raise ValueError(f"No usable rows found in ICR table: {csv_path}")
    return rows


def spread_from_icr(icr: float, icr_rows: List[Tuple[float, float, str, float]]) -> Tuple[str, float]:
    for lower, upper, rating, spread in icr_rows:
        if lower <= icr <= upper:
            return rating, spread
    raise ValueError(f"ICR {icr} is outside ICR table bounds")


def compute_country(country: Dict[str, Any], assumption: Dict[str, Any], usd_inputs: Dict[str, Any], icr_rows):
    e_ratio = float(assumption["equity_ratio"])
    d_ratio = float(assumption["debt_ratio"])
    local_debt_ratio = float(assumption["local_debt_ratio"])
    fx_debt_ratio = float(assumption["fx_debt_ratio"])

    corporate_tax = _parse_percent(country["corporate_tax_rate"])
    erp_total = _parse_percent(country["total_erp"])
    unlevered_beta = float(country["unlevered_beta"])

    local_10y = _parse_percent(country["local_10y_bond_rate"])
    sovereign_spread_local = _parse_percent(country["sovereign_default_spread_local"])
    sovereign_spread_usd = _parse_percent(country.get("sovereign_default_spread_usd", sovereign_spread_local))

    vat = _parse_percent(country.get("vat", 0)) if assumption.get("apply_vat", False) else 0.0
    wht = _parse_percent(country.get("withholding_tax", 0)) if assumption.get("apply_wht", False) else 0.0
    inflation = _parse_percent(country.get("inflation_rate", 0))

    if "project_credit_spread" in country:
        project_spread = _parse_percent(country["project_credit_spread"])
        spread_rating = "provided"
    else:
        icr = float(country["icr"])
        spread_rating, project_spread = spread_from_icr(icr, icr_rows)

    beta_l = unlevered_beta * (1 + (1 - corporate_tax) * (d_ratio / e_ratio))
    equity_rf = _parse_percent(usd_inputs.get("usd_equity_rf_rate", usd_inputs["usd_10y_bond_rate"]))
    ke = equity_rf + beta_l * erp_total
    equity_contribution = e_ratio * ke

    local_base = local_10y - sovereign_spread_local
    usd_10y = _parse_percent(usd_inputs["usd_10y_bond_rate"])
    fx_base = usd_10y - sovereign_spread_usd

    local_financing = local_base + project_spread
    fx_financing = fx_base + project_spread

    hedge_spread = local_base - fx_base + 0.01 + 0.005
    apply_hedge = 1.0 if assumption.get("apply_fx_hedge", False) else 0.0

    kd1 = local_financing / (1 - vat) if (1 - vat) > 0 else float("inf")
    kd2 = (fx_financing + apply_hedge * hedge_spread) / (1 - wht) if (1 - wht) > 0 else float("inf")

    debt_contribution = (1 - corporate_tax) * ((local_debt_ratio * kd1) + (fx_debt_ratio * kd2)) * d_ratio
    wacc_nominal = equity_contribution + debt_contribution
    wacc_real = ((1 + wacc_nominal) / (1 + inflation)) - 1 if inflation > -1 else float("nan")

    return {
        "country": country["country"],
        "inputs_used": {
            "spread_rating": spread_rating,
            "project_credit_spread": project_spread,
            "equity_rf_used": equity_rf,
            "vat_applied": vat,
            "wht_applied": wht,
        },
        "outputs": {
            "levered_beta": beta_l,
            "required_equity_return": ke,
            "equity_contribution": equity_contribution,
            "local_base_rate": local_base,
            "fx_base_rate": fx_base,
            "local_financing_rate": local_financing,
            "fx_financing_rate": fx_financing,
            "hedge_cost": hedge_spread,
            "required_local_debt_return": kd1,
            "required_fx_debt_return": kd2,
            "debt_contribution": debt_contribution,
            "wacc_nominal": wacc_nominal,
            "wacc_real": wacc_real,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute WACC for Americas focus countries")
    parser.add_argument("--input", required=True, help="Path to input JSON")
    parser.add_argument("--output", help="Write output JSON to file (default: stdout)")
    parser.add_argument(
        "--icr-table",
        default="ICR_table.csv",
        help="Path to ICR lookup table CSV (default: repo ICR_table.csv)",
    )
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    icr_rows = load_icr_table(Path(args.icr_table))

    assumption = payload["assumptions"]
    usd_inputs = payload["usd_inputs"]
    results = [compute_country(c, assumption, usd_inputs, icr_rows) for c in payload["countries"]]

    output = {
        "assumptions": assumption,
        "usd_inputs": usd_inputs,
        "results": results,
        "source_refs": payload.get("source_refs", []),
    }

    rendered = json.dumps(output, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
