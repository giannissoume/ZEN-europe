"""Check balances and costs from saved ZEN-garden parameters, variables and units."""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pint
import xarray as xr
from build_and_run import (
    FREIGHT_CI,
    FREIGHT_PRICE,
    HOURS,
    HYDROGEN_MW,
    POWER_CI,
    POWER_DEMAND_MW,
    POWER_PRICE,
    TECHNOLOGY,
)


def close(actual, expected):
    np.testing.assert_allclose(actual, expected, rtol=1e-7, atol=1e-7, equal_nan=False)


def check(result: Path, case: dict, exchange: float):
    units = pint.UnitRegistry()
    units.load_definitions(str(result / "unit_definitions.txt"))
    node = case["node"]
    sequence = json.loads((result / "dict_all_sequence_time_steps.json").read_text())
    time_map = sequence["time_steps_year2operation"]
    with (
        xr.open_dataset(result / "variables.nc") as variables,
        xr.open_dataset(result / "parameters.nc") as parameters,
        pd.HDFStore(result / "variables_units.h5", mode="r") as variable_units,
        pd.HDFStore(result / "parameters_units.h5", mode="r") as parameter_units,
    ):
        assert (TECHNOLOGY in variables.coords["set_conversion_technologies"]) == case[
            "enabled"
        ]
        assert ("olivine" in variables.coords["set_carriers"]) == case["enabled"]
        report = []
        for year_index, year in enumerate(case["years"]):
            (step,) = time_map[str(year_index)]
            op = {"set_time_steps_operation": step}
            annual = {"set_years": year_index}
            capacity = {
                "set_technologies": TECHNOLOGY,
                "set_capacity_types": "power",
                "set_location": node,
            }
            close(parameters["time_steps_operation_duration"].sel(**op), HOURS)

            masked = case["enabled"] and (year < 2030 or node == "CH")
            if masked:
                close(parameters["capacity_limit"].sel(**capacity, **annual), 0)
                close(parameters["capacity_existing"].sel(**capacity), 0)
                close(parameters["capacity_investment_existing"].sel(**capacity), 0)

            def converted(
                name,
                target,
                selection,
                *,
                parameter=False,
                zero_mask=False,
                masked=masked,
            ):
                collection = parameters if parameter else variables
                table = parameter_units if parameter else variable_units
                value = float(collection[name].sel(**selection).item())
                if np.isnan(value) and zero_mask and masked:
                    return 0.0
                assert np.isfinite(value), (name, selection, value)
                saved = table[name]
                keys = tuple(selection[level] for level in saved.index.names if level)
                unit = (
                    saved.loc[keys[0] if len(keys) == 1 else keys]
                    if keys
                    else saved.iloc[0]
                )
                return units.Quantity(value, unit).to(target).magnitude

            def flow(direction, tech, carrier, unit, *, zero_mask=False, op=op):
                return converted(
                    f"flow_conversion_{direction}",
                    unit,
                    {
                        "set_conversion_technologies": tech,
                        f"set_{direction}_carriers": carrier,
                        "set_nodes": node,
                        **op,
                    },
                    zero_mask=zero_mask,
                )

            hydrogen_sink = 0.0
            fuel_cell_output = 0.0
            if case["fuel_cell_mw"]:
                fuel_cell_output = flow("output", "fuel_cell", "electricity", "MW")
                close(fuel_cell_output, case["fuel_cell_mw"])
                hydrogen_sink = flow("input", "fuel_cell", "hydrogen", "MW")
                assert hydrogen_sink > 0

            offtake = HYDROGEN_MW if year in case["active_years"] else 0
            rate = (offtake + hydrogen_sink) / HYDROGEN_MW
            electricity = rate * 2.5 / 1.5
            freight = rate * 100
            capex = fixed_om = annualized_capex = 0.0
            if case["enabled"]:
                actual_rate = flow(
                    "input", TECHNOLOGY, "olivine", "tproduct/h", zero_mask=True
                )
                close(actual_rate, rate)
                hydrogen = flow("output", TECHNOLOGY, "hydrogen", "MW", zero_mask=True)
                close(hydrogen, offtake + hydrogen_sink)
                close(
                    flow("input", TECHNOLOGY, "electricity", "MW", zero_mask=True),
                    electricity,
                )
                close(
                    flow("input", TECHNOLOGY, "truck_mileage", "tkm/h", zero_mask=True),
                    freight,
                )
                yr_capacity = rate / 0.90
                addition = yr_capacity if year in case["investment_years"] else 0
                for name, expected in (
                    ("capacity", yr_capacity),
                    ("capacity_previous", yr_capacity - addition),
                    ("capacity_addition", addition),
                    ("capacity_investment", addition),
                ):
                    close(
                        converted(
                            name, "tproduct/hour", capacity | annual, zero_mask=True
                        ),
                        expected,
                    )
                if not masked:
                    assert np.isposinf(
                        parameters["capacity_limit"].sel(**capacity, **annual)
                    )
                    assert np.isposinf(
                        parameters["max_diffusion_rate"].sel(
                            set_technologies=TECHNOLOGY, **annual
                        )
                    )
                close(parameters["lifetime"].sel(set_technologies=TECHNOLOGY), 20)
                close(
                    parameters["construction_time"].sel(set_technologies=TECHNOLOGY), 0
                )
                capex = converted(
                    "cost_capex_overnight", "Euro", capacity | annual, zero_mask=True
                )
                close(capex, addition * 8672400 * exchange)
                annualized_capex = converted(
                    "cost_capex_yearly", "Euro", capacity | annual, zero_mask=True
                )
                interest = float(parameters["discount_rate"].item())
                close(
                    annualized_capex,
                    yr_capacity
                    * 8672400
                    * exchange
                    * interest
                    / (1 - (1 + interest) ** -20),
                )
                fixed_om = converted(
                    "cost_opex_yearly",
                    "Euro",
                    {"set_technologies": TECHNOLOGY, "set_location": node, **annual},
                    zero_mask=True,
                )
                close(fixed_om, yr_capacity * 260172 * exchange)
                close(
                    converted(
                        "cost_opex_variable",
                        "Euro/hour",
                        {"set_technologies": TECHNOLOGY, "set_location": node, **op},
                        zero_mask=True,
                    ),
                    0,
                )

            power_import = POWER_DEMAND_MW + electricity - fuel_cell_output
            imports = {
                "electricity": (power_import, "MW", POWER_PRICE, POWER_CI),
                "hydrogen": (0, "MW", 0, 0),
            }
            if case["enabled"]:
                imports["truck_mileage"] = (
                    freight,
                    "tkm/hour",
                    FREIGHT_PRICE,
                    FREIGHT_CI,
                )
                imports["olivine"] = (rate, "tproduct/hour", 25 * exchange, 0)
            for carrier, (amount, unit, price, ci) in imports.items():
                selection = {"set_carriers": carrier, "set_nodes": node, **op}
                close(converted("flow_import", unit, selection), amount)
                close(converted("flow_export", unit, selection), 0)
                close(converted("shed_demand", unit, selection), 0)
                close(converted("cost_carrier", "Euro/hour", selection), amount * price)
                close(
                    converted("carbon_emissions_carrier", "ton/hour", selection),
                    amount * ci,
                )
            close(
                converted(
                    "demand",
                    "MW",
                    {"set_carriers": "hydrogen", "set_nodes": node, **op},
                    parameter=True,
                ),
                offtake,
            )
            carrier_cost = converted("cost_carrier_total", "Euro", annual)
            close(carrier_cost, HOURS * sum(a * p for a, _, p, _ in imports.values()))
            carrier_emissions = converted(
                "carbon_emissions_carrier_total", "ton", annual
            )
            close(
                carrier_emissions, HOURS * sum(a * c for a, _, _, c in imports.values())
            )
            removal = rate * HOURS / 1.5
            technology_emissions = converted(
                "carbon_emissions_technology_total", "ton", annual
            )
            close(technology_emissions, -removal)
            emissions = converted("carbon_emissions_annual", "ton", annual)
            close(emissions, carrier_emissions - removal)
            report.append(
                {
                    "year": year,
                    "rock_t": rate * HOURS,
                    "electricity_mwh": electricity * HOURS,
                    "hydrogen_mwh": (offtake + hydrogen_sink) * HOURS,
                    "freight_tkm": freight * HOURS,
                    "credited_removal_tco2": removal,
                    "carrier_emissions_tco2": carrier_emissions,
                    "net_emissions_tco2": emissions,
                    "emissions_residual_tco2": emissions - carrier_emissions + removal,
                    "investment_euro": capex,
                    "annualized_capex_euro": annualized_capex,
                    "fixed_om_euro": fixed_om,
                    "carrier_cost_euro": carrier_cost,
                }
            )
    return report


if __name__ == "__main__":
    payload = json.loads(Path(sys.argv[1]).read_text())
    ecb = Path(payload["source"]) / "04-monetary/ecb/ecb_dollar_to_euro.csv"
    usd_to_euro = 1 / pd.read_csv(ecb, index_col="year").loc[2025, "euro2dollar"]
    name = payload["case"]["name"]
    print(
        json.dumps(
            {
                "case": name,
                "condition": "optimal",
                "years": check(Path(payload["result"]), payload["case"], usd_to_euro),
            }
        )
    )
