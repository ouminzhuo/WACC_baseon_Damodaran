#!/usr/bin/env python3
"""Compute nominal and real WACC for Americas focus countries.

This script uses the formulas defined in the americas-wacc skill and can
resolve company default spread from repository ICR_table.csv.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime
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


def load_vat_country_table(csv_path: Path) -> Dict[str, Dict[str, bool]]:
    """Load per-country VAT switches for local/fx debt required return.

    Required columns:
    - country
    Optional columns:
    - include_vat_in_local_debt (1/0, true/false)
    - include_vat_in_fx_debt (1/0, true/false)

    Backward compatibility:
    - If only include_vat_in_fx_debt exists, local switch will reuse fx switch.
    """
    mapping: Dict[str, Dict[str, bool]] = {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            country = str(row.get("country", "")).strip()
            if not country:
                continue
            fx_raw = str(row.get("include_vat_in_fx_debt", "")).strip().lower()
            local_raw = str(row.get("include_vat_in_local_debt", "")).strip().lower()
            include_fx = fx_raw in {"1", "true", "yes", "y"}
            if local_raw:
                include_local = local_raw in {"1", "true", "yes", "y"}
            else:
                include_local = include_fx
            mapping[country.lower()] = {
                "include_local": include_local,
                "include_fx": include_fx,
            }
    if not mapping:
        raise ValueError(f"No usable rows found in VAT country table: {csv_path}")
    return mapping



def load_wht_country_table(csv_path: Path, *, max_age_days: int = 90, allow_stale: bool = False) -> Dict[str, Dict[str, Any]]:
    """Load per-country withholding tax defaults with freshness metadata.

    Required columns:
    - country
    - withholding_tax
    Optional but recommended columns:
    - source_url
    - collected_on (YYYY-MM-DD)
    """
    mapping: Dict[str, Dict[str, Any]] = {}
    today = date.today()
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            country = str(row.get("country", "")).strip()
            wht_raw = str(row.get("withholding_tax", "")).strip()
            source_url = str(row.get("source_url", "")).strip()
            collected_on_raw = str(row.get("collected_on", "")).strip()
            if not country or not wht_raw:
                continue

            collected_on = None
            age_days = None
            if collected_on_raw:
                collected_on = datetime.strptime(collected_on_raw, "%Y-%m-%d").date()
                age_days = (today - collected_on).days
                if age_days > max_age_days and not allow_stale:
                    raise ValueError(
                        f"{country}: stale WHT row ({age_days} days old). "
                        f"Refresh WHT_ctry.csv from web source before calculation"
                    )

            mapping[country.lower()] = {
                "wht": _parse_percent(wht_raw),
                "source_url": source_url,
                "collected_on": collected_on_raw,
                "age_days": age_days,
            }

    if not mapping:
        raise ValueError(f"No usable rows found in WHT country table: {csv_path}")
    return mapping


def spread_from_icr(icr: float, icr_rows: List[Tuple[float, float, str, float]]) -> Tuple[str, float]:
    for lower, upper, rating, spread in icr_rows:
        if lower <= icr <= upper:
            return rating, spread
    raise ValueError(f"ICR {icr} is outside ICR table bounds")


def compute_country(
    country: Dict[str, Any],
    assumption: Dict[str, Any],
    usd_inputs: Dict[str, Any],
    icr_rows,
    vat_fx_rules: Dict[str, bool],
    wht_country_rules: Dict[str, Dict[str, Any]],
):
    e_ratio = float(assumption["equity_ratio"])
    d_ratio = float(assumption["debt_ratio"])
    local_debt_ratio = float(assumption["local_debt_ratio"])
    fx_debt_ratio = float(assumption["fx_debt_ratio"])

    corporate_tax = _parse_percent(country["corporate_tax_rate"])
    erp_total = _parse_percent(country["total_erp"])
    unlevered_beta = float(country["unlevered_beta"])

    local_10y = _parse_percent(country["local_10y_bond_rate"])
    sovereign_spread_local = _parse_percent(country["sovereign_default_spread_local"])
    country_name = str(country.get("country", "Unknown"))

    vat_ori = _parse_percent(country.get("vat", 0))

    enforce_tax_from_tables = bool(assumption.get("enforce_tax_from_tables", True))
    error_on_tax_input_mismatch = bool(assumption.get("error_on_tax_input_mismatch", True))
    input_apply_vat = bool(assumption.get("apply_vat", False))
    input_apply_wht = bool(assumption.get("apply_wht", False))

    enforce_country_wht = bool(assumption.get("enforce_country_wht", True))
    country_wht = wht_country_rules.get(country_name.lower())
    if country_wht is None and enforce_country_wht:
        raise ValueError(f"{country_name}: missing WHT rule in WHT country table")

    table_wht = float(country_wht["wht"]) if country_wht else 0.0
    table_apply_wht = table_wht > 0

    if enforce_tax_from_tables:
        wht = table_wht if table_apply_wht else 0.0
        wht_source = "WHT_ctry.csv"
        wht_source_url = country_wht.get("source_url", "") if country_wht else ""
        wht_collected_on = country_wht.get("collected_on", "") if country_wht else ""
        if error_on_tax_input_mismatch and input_apply_wht != table_apply_wht:
            raise ValueError(
                f"{country_name}: input apply_wht={input_apply_wht} conflicts with WHT_ctry rule (apply={table_apply_wht})"
            )
    else:
        if input_apply_wht:
            fallback_wht = table_wht
            wht = _parse_percent(country.get("withholding_tax", fallback_wht))
            wht_source = "input_or_fallback"
            wht_source_url = country_wht.get("source_url", "") if country_wht else ""
            wht_collected_on = country_wht.get("collected_on", "") if country_wht else ""
        else:
            wht = 0.0
            wht_source = "disabled"
            wht_source_url = ""
            wht_collected_on = ""

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

    # FX base must use USD 10Y minus US sovereign default spread.
    usd_10y = _parse_percent(usd_inputs["usd_10y_bond_rate"])
    us_sovereign_spread = _parse_percent(usd_inputs["us_sovereign_default_spread"])
    fx_base = usd_10y - us_sovereign_spread

    local_financing = local_base + project_spread
    fx_financing = fx_base + project_spread

    hedge_spread = local_base - fx_base + 0.01 + 0.005
    apply_hedge = 1.0 if assumption.get("apply_fx_hedge", False) else 0.0

    vat_rules = vat_fx_rules.get(country_name.lower())
    if vat_rules is None:
        raise ValueError(f"{country_name}: missing VAT rule in VAT country table")

    table_apply_vat_local = bool(vat_rules["include_local"])
    table_apply_vat_fx = bool(vat_rules["include_fx"])

    if enforce_tax_from_tables:
        vat_applied = vat_ori if table_apply_vat_local else 0.0
        vat_fx_applied = vat_ori if table_apply_vat_fx else 0.0
        table_apply_vat_any = table_apply_vat_local or table_apply_vat_fx
        if error_on_tax_input_mismatch and input_apply_vat != table_apply_vat_any:
            raise ValueError(
                f"{country_name}: input apply_vat={input_apply_vat} conflicts with VAT_ctry rule (apply={table_apply_vat_any})"
            )
    else:
        vat_applied = vat_ori if (input_apply_vat and table_apply_vat_local) else 0.0
        vat_fx_applied = vat_ori if (input_apply_vat and table_apply_vat_fx) else 0.0

    kd1 = local_financing / (1 - vat_applied) if (1 - vat_applied) > 0 else float("inf")
    # Parallel-tax denominator for Kd2: 1 - WHT - VAT_fx
    fx_tax_factor = 1 - wht - vat_fx_applied
    kd2 = (fx_financing + apply_hedge * hedge_spread) / fx_tax_factor if fx_tax_factor > 0 else float("inf")

    debt_contribution = (1 - corporate_tax) * ((local_debt_ratio * kd1) + (fx_debt_ratio * kd2)) * d_ratio
    wacc_nominal = equity_contribution + debt_contribution
    wacc_real = ((1 + wacc_nominal) / (1 + inflation)) - 1 if inflation > -1 else float("nan")

    return {
        "country": country_name,
        "inputs_used": {
            "spread_rating": spread_rating,
            "project_credit_spread": project_spread,
            "equity_rf_used": equity_rf,
            "us_sovereign_spread_used": us_sovereign_spread,
            "vat_original": vat_ori,
            "vat_local_rule_applied": vat_rules["include_local"],
            "vat_fx_rule_applied": vat_rules["include_fx"],
            "tax_rules_enforced": enforce_tax_from_tables,
            "tax_input_mismatch_check": error_on_tax_input_mismatch,
            "vat_applied": vat_applied,
            "vat_fx_applied": vat_fx_applied,
            "wht_applied": wht,
            "wht_source": wht_source,
            "wht_source_url": wht_source_url,
            "wht_collected_on": wht_collected_on,
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
    parser.add_argument(
        "--vat-country-table",
        default="VAT_ctry.csv",
        help="Path to country VAT FX rule CSV (default: VAT_ctry.csv)",
    )
    parser.add_argument(
        "--wht-country-table",
        default="WHT_ctry.csv",
        help="Path to country WHT rule CSV (default: WHT_ctry.csv)",
    )
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    icr_rows = load_icr_table(Path(args.icr_table))
    vat_fx_rules = load_vat_country_table(Path(args.vat_country_table))

    assumption = payload["assumptions"]
    wht_country_rules = load_wht_country_table(
        Path(args.wht_country_table),
        max_age_days=int(assumption.get("max_wht_age_days", 90)),
        allow_stale=bool(assumption.get("allow_stale_wht", False)),
    )
    usd_inputs = payload["usd_inputs"]
    results = [compute_country(c, assumption, usd_inputs, icr_rows, vat_fx_rules, wht_country_rules) for c in payload["countries"]]

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
