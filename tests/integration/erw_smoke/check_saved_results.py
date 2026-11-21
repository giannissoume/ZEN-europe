"""Verify saved ERW material, energy, cost and emissions balances."""

import json
import sys
from pathlib import Path

import numpy as np
import xarray as xr

payload = json.loads(Path(sys.argv[1]).read_text())
c = payload["coeffs"]
node = payload["node"]
result = Path(payload["result_dir"])
assert json.loads((result / "benchmarking.json").read_text())["solver_status"] == 2


def scalar(da):
    value = float(da.squeeze().values)
    assert np.isfinite(value), ("Missing/nonfinite saved result", da.name, value)
    return value


def close(actual, expected):
    assert np.isclose(actual, expected, rtol=1e-6, atol=1e-8), (actual, expected)


with (
    xr.open_dataset(result / "variables.nc") as ds,
    xr.open_dataset(result / "parameters.nc") as params,
):
    technologies = set(ds.coords["set_conversion_technologies"].values)
    assert "basalt_grinding" in technologies
    assert ("basalt_application" in technologies) == c["enabled"]
    assert ("biochar_application" in technologies) == ("biochar_forced_mw" in c)
    durations = params["time_steps_operation_duration"].values
    assert np.isfinite(durations).all() and (durations > 0).all()
    hours = float(durations.sum())
    close(hours, 8760)

    def flow(direction, technology, carrier):
        return scalar(
            ds[f"flow_conversion_{direction}"].sel(
                set_conversion_technologies=technology,
                **{f"set_{direction}_carriers": carrier},
                set_nodes=node,
            )
        )

    def technology_value(variable, technology):
        return scalar(
            ds[variable].sel(
                set_technologies=technology,
                set_location=node,
            )
        )

    produced = flow("output", "basalt_grinding", "ground_basalt") * 1000
    applied = (
        flow("input", "basalt_application", "ground_basalt") * 1000
        if c["enabled"]
        else 0.0
    )
    close(applied, c["forced_rate"])
    close(produced, applied)
    close(flow("input", "basalt_grinding", "basalt") * 1000, produced)
    electricity = 0.1947445179009531 / 69.9062230049315 / 1000
    close(flow("input", "basalt_grinding", "electricity"), produced * electricity)
    if c["enabled"]:
        close(flow("input", "basalt_application", "diesel"), applied * 6e-6)
        close(flow("input", "basalt_application", "truck_mileage"), applied * 100 / 1e6)
        cap = technology_value("capacity", "basalt_application") * 1000
        assert cap <= c["capacity_limit"] + 1e-6
        assert applied * hours <= c["capacity_limit"] * 8760 + 1e-5
        close(
            technology_value("cost_opex_yearly", "basalt_application") * 1e6,
            applied * hours * 6 * c["money_factor"],
        )
        close(technology_value("cost_capex_overnight", "basalt_application"), 0)

    capacity = technology_value("capacity", "basalt_grinding") * 1000
    close(capacity, produced / 0.85)
    nameplate = 250000 / 8760
    close(
        technology_value("cost_capex_overnight", "basalt_grinding") * 1e6,
        capacity * 26001000 / nameplate * c["money_factor"],
    )
    close(
        technology_value("cost_opex_yearly", "basalt_grinding") * 1e6,
        capacity * (3121279 + 296406) / nameplate * c["money_factor"],
    )

    bcr_tph = c.get("biochar_forced_mw", 0) / (25 / 3.6)
    total_applied = applied + bcr_tph
    imports_expected = {
        "basalt": produced / 1000,
        "ground_basalt": 0,
        "electricity": 0.001 + produced * electricity,
        "diesel": total_applied * 6e-6,
        "truck_mileage": total_applied * 100 / 1e6,
    }
    # ZEN-garden omits unreferenced diesel/freight carriers when application
    # is absent. Require the exact expected carrier set before skipping them.
    expected_carriers = {"basalt", "ground_basalt", "electricity"}
    if c["enabled"] or "biochar_forced_mw" in c:
        expected_carriers.update({"diesel", "truck_mileage"})
    if "biochar_forced_mw" in c:
        expected_carriers.add("biochar_for_application")
    assert set(ds.coords["set_carriers"].values) == expected_carriers
    for carrier, expected in imports_expected.items():
        if carrier not in expected_carriers:
            assert expected == 0
            continue
        close(
            scalar(ds["flow_import"].sel(set_carriers=carrier, set_nodes=node)),
            expected,
        )
    import_emissions = hours * (
        imports_expected["electricity"] * 100
        + imports_expected["diesel"] * 267
        + total_applied * 100 * 0.0001
    )
    close(scalar(ds["carbon_emissions_carrier_total"]) * 1e6, import_emissions)
    technology_emissions = -hours * (applied * 0.0406875 + bcr_tph * 2.2)
    close(scalar(ds["carbon_emissions_technology_total"]) * 1e6, technology_emissions)
    annual = scalar(ds["carbon_emissions_annual"]) * 1e6
    close(annual, import_emissions + technology_emissions)
    # Carrier cost is an independent check on procurement and service boundaries.
    expected_carrier_cost = hours * (
        produced * 25 * c["money_factor"]
        + imports_expected["electricity"] * 50000
        + imports_expected["diesel"] * 80000
        + total_applied * 100 * 0.1
        + c.get("biochar_forced_mw", 0) * 50
    )
    close(scalar(ds["cost_carrier_total"]) * 1e6, expected_carrier_cost)
    summary = {
        "case": result.name,
        "solver_status": 2,
        "annual_basalt_t": applied * hours,
        "gross_erw_removal_tco2": applied * hours * 0.0406875,
        "annual_net_emissions_tco2": annual,
        "balance_error_tco2": annual - import_emissions - technology_emissions,
    }
print(json.dumps(summary))
