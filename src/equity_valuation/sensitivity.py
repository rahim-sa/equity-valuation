"""
Sensitivity analysis: value-per-share across a grid of
growth rate x discount rate assumptions.

Reuses run_naive_dcf as-is — this module doesn't duplicate DCF math,
it just sweeps inputs and collects outputs. Keeping the DCF engine
as the single source of truth for the calculation matters: if the
sweep re-implemented the formula, the two could drift out of sync.

FLAG: terminal_growth_rate is held fixed across the sweep here, only
growth_rate (explicit period) and discount_rate vary. A real analysis
often also wants to sweep terminal_growth_rate, but a 3-variable grid
stops being readable as a single table — that's a reasonable follow-up,
not a v1 requirement.

FLAG: any (growth_rate, discount_rate) pair where terminal_growth_rate
>= discount_rate is invalid (see dcf.terminal_value). Rather than
skipping those cells silently, we surface them explicitly as None in
the grid so a caller can see exactly which assumption combinations are
infeasible, not just get a smaller-than-expected table.
"""

from dataclasses import replace

from equity_valuation.dcf import NaiveDCFInputs, run_naive_dcf


def sensitivity_grid(
    base_inputs: NaiveDCFInputs,
    growth_rates: list[float],
    discount_rates: list[float],
) -> dict[tuple[float, float], float | None]:
    """
    Returns {(growth_rate, discount_rate): value_per_share_or_None}.
    None marks an infeasible combination (terminal_growth_rate >= discount_rate).
    """
    grid: dict[tuple[float, float], float | None] = {}
    for g in growth_rates:
        for d in discount_rates:
            scenario_inputs = replace(base_inputs, growth_rate=g, discount_rate=d)
            if base_inputs.terminal_growth_rate >= d:
                grid[(g, d)] = None
                continue
            result = run_naive_dcf(scenario_inputs)
            grid[(g, d)] = result["value_per_share"]
    return grid


def format_grid(
    grid: dict[tuple[float, float], float | None],
    growth_rates: list[float],
    discount_rates: list[float],
) -> str:
    """Simple text table: rows = growth rate, columns = discount rate."""
    header = "growth\\discount".ljust(16) + "".join(f"{d:>10.1%}" for d in discount_rates)
    lines = [header]
    for g in growth_rates:
        row = f"{g:>15.1%} "
        for d in discount_rates:
            value = grid[(g, d)]
            row += f"{'n/a':>10}" if value is None else f"{value:>10.2f}"
        lines.append(row)
    return "\n".join(lines)