"""Check saved ERW functionality results in the solving environment."""

import json
import sys
from pathlib import Path

import xarray as xr

payload = json.loads(Path(sys.argv[1]).read_text())
coeffs = payload["coeffs"]
node = payload["node"]
result_dir = Path(payload["result_dir"])
bench = json.loads((result_dir / "benchmarking.json").read_text())
status = bench["solver_status"]
assert status == 2, f"expected Gurobi OPTIMAL (2), got {status}"

ds = xr.open_dataset(result_dir / "variables.nc")
hours = 8760.0
# Base units: ktproduct/h, GW, megatkm/h, megatons
forced_kt_per_h = coeffs["forced_rate"] / 1000.0


def scalar(da):
    return float(da.squeeze().values)


app = scalar(
    ds["flow_conversion_input"].sel(
        set_conversion_technologies="basalt_application",
        set_input_carriers="ground_basalt",
        set_nodes=node,
    )
)
grind = scalar(
    ds["flow_conversion_output"].sel(
        set_conversion_technologies="basalt_grinding",
        set_output_carriers="ground_basalt",
        set_nodes=node,
    )
)
elec = scalar(
    ds["flow_conversion_input"].sel(
        set_conversion_technologies="basalt_grinding",
        set_input_carriers="electricity",
        set_nodes=node,
    )
)
diesel = scalar(
    ds["flow_conversion_input"].sel(
        set_conversion_technologies="basalt_application",
        set_input_carriers="diesel",
        set_nodes=node,
    )
)
freight = scalar(
    ds["flow_conversion_input"].sel(
        set_conversion_technologies="basalt_application",
        set_input_carriers="truck_mileage",
        set_nodes=node,
    )
)
cap_app = scalar(
    ds["capacity"].sel(set_technologies="basalt_application", set_location=node)
)
limit_kt = coeffs["capacity_limit"] / 1000.0
removal_annual_mt = scalar(ds["carbon_emissions_technology_total"])
ds.close()


def approx(a, b, rel=1e-3):
    return abs(a - b) <= rel * max(abs(b), 1e-12)


assert approx(app, forced_kt_per_h), (app, forced_kt_per_h)
assert approx(grind, forced_kt_per_h), (grind, forced_kt_per_h)
assert approx(elec, coeffs["forced_rate"] * coeffs["electricity_gwh_per_t"]), (elec,)
assert approx(diesel, coeffs["forced_rate"] * coeffs["diesel_gwh_per_t"]), (diesel,)
assert approx(freight, coeffs["forced_rate"] * coeffs["delivery_tkm_per_t"] / 1e6), (
    freight,
)
assert cap_app <= limit_kt + 1e-9
assert approx(
    removal_annual_mt,
    -coeffs["removal_tco2_per_t"] * coeffs["forced_rate"] * hours / 1e6,
), removal_annual_mt

summary = {
    "solver_status": status,
    "application_t_per_h": app * 1000.0,
    "grinding_t_per_h": grind * 1000.0,
    "electricity_GW": elec,
    "diesel_GW": diesel,
    "truck_megatkm_per_h": freight,
    "removal_megatons": removal_annual_mt,
    "removal_tCO2": -removal_annual_mt * 1e6,
    "land_ceiling_t_per_h": coeffs["capacity_limit"],
    "below_ceiling": cap_app < limit_kt,
}
print(json.dumps(summary, indent=2))
print("ERW smoke checks passed")
