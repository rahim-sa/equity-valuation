from equity_valuation.dcf import NaiveDCFInputs, run_naive_dcf

# Round numbers chosen specifically so you can verify by hand.
inputs = NaiveDCFInputs(
    base_fcf=100.0,
    growth_rate=0.10,
    discount_rate=0.10,
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