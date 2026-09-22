# from equity_valuation.dcf import NaiveDCFInputs, run_naive_dcf

# # Round numbers chosen specifically so you can verify by hand.
# inputs = NaiveDCFInputs(
#     base_fcf=100.0,
#     growth_rate=0.10,
#     discount_rate=0.10,
#     terminal_growth_rate=0.03,
#     projection_years=5,
#     net_debt=200.0,
#     shares_outstanding=50.0,
# )

# result = run_naive_dcf(inputs)
# for key, value in result.items():
#     print(f"{key}: {value}")

from equity_valuation.dcf import NaiveDCFInputs, run_naive_dcf
from equity_valuation.wacc import (
    CostOfEquityInputs,
    CostOfDebtInputs,
    WACCInputs,
    cost_of_equity_capm,
    cost_of_debt_effective_rate,
    wacc,
)

# --- WACC inputs (still hardcoded placeholders, same discipline as before —
# real EDGAR/FRED/Damodaran data comes in stage (c)) ---
coe_inputs = CostOfEquityInputs(risk_free_rate=0.04, beta=1.1, equity_risk_premium=0.05)
cost_of_equity = cost_of_equity_capm(coe_inputs)

cod_inputs = CostOfDebtInputs(interest_expense=10.0, total_debt=200.0)
cost_of_debt = cost_of_debt_effective_rate(cod_inputs)

wacc_inputs = WACCInputs(
    market_value_equity=2500.0,   # e.g. share_price * shares_outstanding
    market_value_debt=200.0,
    cost_of_equity=cost_of_equity,
    cost_of_debt=cost_of_debt,
    tax_rate=0.21,
)
discount_rate = wacc(wacc_inputs)

print(f"cost_of_equity: {cost_of_equity:.4f}")
print(f"cost_of_debt: {cost_of_debt:.4f}")
print(f"computed WACC (discount_rate): {discount_rate:.4f}")

# --- DCF inputs, now using computed WACC instead of a hardcoded discount_rate ---
inputs = NaiveDCFInputs(
    base_fcf=100.0,
    growth_rate=0.10,
    discount_rate=discount_rate,
    terminal_growth_rate=0.03,
    projection_years=5,
    net_debt=200.0,
    shares_outstanding=50.0,
)

result = run_naive_dcf(inputs)
for key, value in result.items():
    print(f"{key}: {value}")


from equity_valuation.sensitivity import sensitivity_grid, format_grid

growth_rates = [0.06, 0.08, 0.10, 0.12, 0.14]
discount_rates = [0.08, 0.09, 0.10, 0.11, 0.12]

grid = sensitivity_grid(inputs, growth_rates, discount_rates)
print("\nSensitivity table (value per share):")
print(format_grid(grid, growth_rates, discount_rates))