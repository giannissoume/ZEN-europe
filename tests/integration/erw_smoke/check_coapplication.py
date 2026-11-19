"""Check the real BCR/ERW application outputs in their production units."""

import json
import sys
from pathlib import Path

import numpy as np
import xarray as xr

payload = json.loads(Path(sys.argv[1]).read_text())
result = Path(payload["result_dir"])
node = payload["node"]
coeffs = payload["coeffs"]
assert json.loads((result / "benchmarking.json").read_text())["solver_status"] == 2
with xr.open_dataset(result / "variables.nc") as data:

    def input_flow(technology, carrier):
        return float(
            data["flow_conversion_input"]
            .sel(
                set_conversion_technologies=technology,
                set_input_carriers=carrier,
                set_nodes=node,
            )
            .squeeze()
        )

    bcr_tph = coeffs["biochar_forced_mw"] / (25 / 3.6)
    erw_tph = coeffs["forced_rate"]
    bcr_gw = input_flow("biochar_application", "biochar")
    np.testing.assert_allclose(bcr_gw, coeffs["biochar_forced_mw"] / 1000, rtol=1e-6)
    np.testing.assert_allclose(
        input_flow("biochar_application", "truck_mileage"),
        bcr_tph * 100 / 1e6,
        rtol=1e-6,
    )
    np.testing.assert_allclose(
        input_flow("biochar_application", "diesel"), bcr_tph * 6 / 1e6, rtol=1e-6
    )
    np.testing.assert_allclose(
        input_flow("basalt_application", "ground_basalt"), erw_tph / 1000, rtol=1e-6
    )
    np.testing.assert_allclose(
        input_flow("basalt_application", "truck_mileage"),
        erw_tph * 100 / 1e6,
        rtol=1e-6,
    )
    np.testing.assert_allclose(
        input_flow("basalt_application", "diesel"), erw_tph * 6 / 1e6, rtol=1e-6
    )
    # Both application routes use the same imported freight service here.
    freight = float(
        data["flow_import"].sel(set_carriers="truck_mileage", set_nodes=node).squeeze()
    )
    np.testing.assert_allclose(freight, (erw_tph + bcr_tph) * 100 / 1e6, rtol=1e-6)
    gross_removal = -float(data["carbon_emissions_technology_total"].squeeze()) * 1e6
    np.testing.assert_allclose(
        gross_removal, 8760 * (bcr_tph * 2.2 + erw_tph * 0.0406875), rtol=1e-6
    )
    cap = float(
        data["capacity"]
        .sel(set_technologies="biochar_application", set_location=node)
        .squeeze()
    )
    assert cap <= coeffs["biochar_limit_mw"] / 1000 + 1e-8
print(
    "Co-application passed at the requested rates, 100 tkm/t each; "
    "BCR credit follows IPCC 0.80 retention."
)
