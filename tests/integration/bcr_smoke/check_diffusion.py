"""Verify free services cannot seed pyrolysis; legitimate initial plants can grow."""

import json
import sys
from pathlib import Path

import numpy as np
import xarray as xr

root = Path(sys.argv[1])
summary = []


def close(a, b):
    a = np.asarray(a)
    assert np.isfinite(a).all()
    assert np.allclose(a, b, rtol=1e-7, atol=1e-10), (a, b)


for case in json.loads((root / "cases.json").read_text()):
    if case["infeasible"]:
        summary.append({"case": case["case"], "outcome": "infeasible"})
        continue
    p = Path(case["result"])
    assert json.loads((p / "benchmarking.json").read_text())["solver_status"] == 2
    with (
        xr.open_dataset(p / "variables.nc") as d,
        xr.open_dataset(p / "parameters.nc") as params,
    ):

        def cap(var, t, d=d):
            return (
                d[var]
                .sel(set_technologies=t, set_capacity_types="power", set_location="CH")
                .values
                * 1000
            )

        close(params.market_share_unbounded.values, 0.02)
        close(params.max_diffusion_rate.sel(set_technologies="pyrolysis").values, 0.13)
        assert case["case"] == "seeded_pyrolysis"
        close(cap("capacity_previous", "pyrolysis")[0], 1)
        additions = cap("capacity_addition", "pyrolysis")
        assert np.isfinite(additions).all() and (additions >= -1e-8).all()
        close(additions.sum(), 0.4)
        close(cap("capacity", "pyrolysis")[-1], 1.4)
        close(cap("capacity_previous", "biochar_application"), [0, 50])
        close(cap("capacity_addition", "biochar_application"), [50, 0])
        for carrier in ["biochar_for_application", "diesel", "truck_mileage"]:
            close(
                d.flow_conversion_input.sel(
                    set_conversion_technologies="biochar_application",
                    set_input_carriers=carrier,
                ).values,
                0,
            )
        close(
            d.flow_conversion_input.sel(
                set_conversion_technologies="biochar_to_application",
                set_input_carriers="biochar",
            ).values,
            0,
        )
        output = (
            d.flow_conversion_output.sel(
                set_conversion_technologies="pyrolysis", set_output_carriers="biochar"
            ).values
            * 1000
        )
        close(output, [[0, 1.4]])
        close(
            d.flow_conversion_input.sel(
                set_conversion_technologies="biochar_to_hard_coal",
                set_input_carriers="biochar",
            ).values
            * 1000,
            output,
        )
        close(
            d.flow_conversion_input.sel(
                set_conversion_technologies="pyrolysis", set_input_carriers="biomass"
            ).values
            * 1000,
            output * 0.96 / 0.45,
        )
        for carrier, ratio in [("oil", 0.19 / 0.45), ("district_heat", 0.24 / 0.45)]:
            close(
                d.flow_conversion_output.sel(
                    set_conversion_technologies="pyrolysis", set_output_carriers=carrier
                ).values
                * 1000,
                output * ratio,
            )
        close(params.time_steps_operation_duration.values, [8760, 8760])
        close(d.carbon_emissions_technology_total.values, 0)
        close(
            d.carbon_emissions_annual.values * 1e6, [0, 1.4 * 8760 * 0.04 / 0.45 * 0.1]
        )
        for var in ["cost_capex_overnight", "cost_opex_yearly"]:
            close(d[var].sel(set_technologies="biochar_application").values, 0)
        summary.append(
            {
                "case": case["case"],
                "outcome": "optimal",
                "service_capacity_mw": [50, 50],
                "service_flow_mw": [0, 0],
                "pyrolysis_addition_mw": additions.tolist(),
                "allowance_from_service_mw": [0, 0],
                "gross_removal_t": [0, 0],
            }
        )
(root / "verified.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
