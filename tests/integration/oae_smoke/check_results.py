"""Check saved OAE flow units and the complete fixture emissions balance."""

import json
import sys
from pathlib import Path

import numpy as np
import xarray as xr

payload = json.loads(Path(sys.argv[1]).read_text())
c = payload["coefficients"]
with (
    xr.open_dataset(Path(payload["result"]) / "variables.nc") as ds,
    xr.open_dataset(Path(payload["result"]) / "parameters.nc") as params,
):

    def scalar(da):
        return float(da.squeeze().values)

    def flow(direction, tech, carrier):
        value = scalar(
            ds[f"flow_conversion_{direction}"].sel(
                set_conversion_technologies=tech,
                **{f"set_{direction}_carriers": carrier},
                set_nodes=c["node"],
            )
        )
        # Accept a masked OAE flow only when saved inputs prove no capacity can
        # exist. A country name alone must not turn missing results into zero.
        if np.isnan(value) and tech in {
            "lime_production_ccs",
            "lime_ocean_application",
        }:
            selection = dict(
                set_technologies=tech,
                set_capacity_types="power",
                set_location=c["node"],
            )
            for parameter in (
                "capacity_limit",
                "capacity_existing",
                "capacity_investment_existing",
            ):
                values = params[parameter].sel(**selection).values
                assert np.isfinite(values).all() and (values == 0).all(), (
                    "Unexpected masked flow",
                    tech,
                    carrier,
                    parameter,
                    values,
                )
            return 0.0
        assert np.isfinite(value), ("Missing/nonfinite flow", tech, carrier, value)
        return value

    has_application = (
        "lime_ocean_application" in ds.coords["set_conversion_technologies"]
    )
    assert (
        has_application == c["application"]
    ), "Unexpected application presence/absence"
    assert np.isclose(params["time_steps_operation_duration"].sum(), 8760)
    applied = (
        flow("input", "lime_ocean_application", "hydrated_lime") * 1000
        if has_application
        else 0.0
    )
    produced = flow("output", "lime_production_ccs", "hydrated_lime") * 1000
    assert np.isclose(applied, c["forced_rate"], rtol=1e-5, atol=1e-8), (applied, c)
    assert np.isclose(produced, applied, rtol=1e-5, atol=1e-8), (produced, applied)
    for carrier in ("limestone", "natural_gas", "electricity", "carbon"):
        direction = "output" if carrier == "carbon" else "input"
        value = flow(direction, "lime_production_ccs", carrier)
        # ktproduct/h and ktCO2/h, versus GW energy input.
        scale = 1000 if carrier in ("limestone", "carbon") else 1
        assert np.isclose(value * scale, produced * c[carrier], rtol=1e-5, atol=1e-8), (
            carrier,
            value,
            c[carrier],
        )
    if applied:
        assert np.isclose(
            flow("input", "lime_ocean_application", "diesel"),
            applied * c["diesel"],
            rtol=1e-5,
        )
        assert np.isclose(
            flow("input", "lime_ocean_application", "truck_mileage"),
            applied * 100 / 1e6,
            rtol=1e-5,
        )
    if produced:
        capacity_tph = (
            scalar(
                ds["capacity"].sel(
                    set_technologies="lime_production_ccs",
                    set_capacity_types="power",
                    set_location=c["node"],
                )
            )
            * 1000
        )
        assert capacity_tph >= produced / 0.95 - 1e-7
        for tech, expected in (
            (
                "lime_production_ccs",
                capacity_tph * c["production_fixed_opex"]
                + produced * 8760 * c["production_variable_opex"],
            ),
            ("lime_ocean_application", applied * 8760 * c["application_variable_opex"]),
        ):
            actual = (
                scalar(
                    ds["cost_opex_yearly"].sel(
                        set_technologies=tech,
                        set_location=c["node"],
                    )
                )
                * 1e6
            )
            assert np.isclose(actual, expected, rtol=1e-5), (tech, actual, expected)
    stored = flow("input", "fixture_storage", "carbon") * 1000
    carbon_feed = 0.0
    if c["gas_route"] == "synthetic":
        carbon_feed = flow("input", "fixture_methanation", "carbon") * 1000
    assert np.isclose(
        stored + carbon_feed, produced * c["carbon"], rtol=1e-5, atol=1e-8
    )
    # Baseline CCS uses the same gas factor across supply routes. With zero-carbon
    # gas supply, fuel-carbon storage may produce a negative emissions term.
    expected_capture = 0.9 * (
        0.786 / (74.1 / 56.08) + 3.76 / 3.6 / (74.1 / 56.08) * 0.20196
    )
    assert np.isclose(c["carbon"], expected_capture, rtol=1e-10)
    assert stored <= produced * expected_capture + 1e-8
    imports = scalar(ds["carbon_emissions_carrier_total"]) * 1e6
    technology = scalar(ds["carbon_emissions_technology_total"]) * 1e6
    expected_technology = (
        produced * c["process"] - stored - applied * c["removal"]
    ) * 8760
    assert np.isclose(technology, expected_technology, rtol=1e-5, atol=1e-5), (
        technology,
        expected_technology,
    )
    annual = scalar(ds["carbon_emissions_annual"]) * 1e6
    assert np.isclose(annual, imports + expected_technology, rtol=1e-5, atol=1e-5), (
        annual,
        imports,
        expected_technology,
    )
    # Independent import emissions, including the 0.001-MW neutral demand.
    expected_imports = (
        0.001 * 0.1
        + produced * c["electricity"] * 1000 * 0.1
        + produced * c["natural_gas"] * 1000 * c["gas_ci"]
        + applied * c["diesel"] * 1000 * 0.267
        + applied * 100 * 0.0001
    ) * 8760
    assert np.isclose(imports, expected_imports, rtol=1e-5, atol=1e-5), (
        imports,
        expected_imports,
    )
    report = dict(
        case=Path(payload["result"]).name,
        condition="optimal",
        applied_t_per_year=applied * 8760,
        gross_uptake_tco2=applied * c["removal"] * 8760,
        stored_tco2=stored * 8760,
        annual_net_emissions_tco2=annual,
        balance_error_tco2=annual - imports - expected_technology,
    )
print(json.dumps(report))
