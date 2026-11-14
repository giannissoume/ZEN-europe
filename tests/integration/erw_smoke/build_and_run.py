"""Generate real ERW elements and check a tiny ordinary ZEN-garden solve.

Only the energy-system boundary and electricity/diesel/freight imports are
synthetic. Basalt carriers and technologies are built and written by the
production classes through ZEN-creator, without rewriting their attributes.
Forced application and unconstrained diffusion are confined to test copies.
"""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import pandas as pd
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTPUT = HERE / "outputs"
NODE = "CH"
FORCED_RATE_T_PER_H = 1.0


def _write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def check_variant_registration() -> None:
    """Resolve both actual model variants without downloading sector data."""
    from zen_creator import Model
    from zen_creator.utils.settings import ModelSet, Settings

    from zen_europe.model_creator import DATA_PATH

    variants = ModelSet.load_from_yaml(DATA_PATH / "models.yaml")
    for name in ("erw", "erw_without_application"):
        settings = Settings.load_from_yaml(
            DATA_PATH / "zen_europe_config.yaml", patch=variants.settings_patch(name)
        )
        model = Model.from_config(
            DATA_PATH / "zen_europe_config.yaml", settings=settings
        )
        assert "basalt_grinding" in model.elements
        assert "basalt" in model.elements and "ground_basalt" in model.elements
        assert ("basalt_application" in model.elements) == (name == "erw")
        assert "biochar_application" in model.elements
    print("Both production variants resolve with BCR preserved.")


def build_dataset(name: str, *, enabled: bool = True, above_limit: bool = False):
    """Build and write the real ERW classes, with small test-only boundaries."""
    from zen_creator import AssumptionInformation, Dataset, DatasetCollection, Model
    from zen_creator.elements.carriers.carrier import GenericCarrier

    from zen_europe.model_creator import DATA_PATH

    Dataset._registries.clear()
    DatasetCollection._registries.clear()
    config = yaml.safe_load((DATA_PATH / "zen_europe_config.yaml").read_text())
    config["source_path"] = str(DATA_PATH / "raw_data")
    config["settings"] = {
        "time": {
            "reference_year": 2026,
            "last_year": 2026,
            "interval_between_years": 1,
        },
        "region": {"set_nodes": [NODE]},
        "structure": {
            "energy_system": "",
            "set_sectors": [],
            "set_carriers": ["basalt", "ground_basalt"],
            "set_conversion_technologies": (
                ["basalt_grinding", "basalt_application"]
                if enabled
                else ["basalt_grinding"]
            ),
        },
    }
    config["system"] = {
        "total_hours_per_year": 8760,
        "unaggregated_time_steps_per_year": 8760,
        "aggregated_time_steps_per_year": 1,
        "conduct_time_series_aggregation": True,
        "use_rolling_horizon": False,
    }
    # GenericEnergySystem needs explicit nodes and edges; no fabricated links.
    config["solver"] = {
        "name": "gurobi",
        "run_diagnostics": True,
        "save_parameters": True,
        "solver_options": {"DualReductions": 0},
    }
    config["analysis"] = {"overwrite_output": True, "earliest_year_of_data": 2026}
    path = OUTPUT / "generation" / f"{name}.yaml"
    _write_yaml(path, config)
    model = Model.from_config(path)
    model.name = name
    model.output_folder = OUTPUT / "generated"
    source = AssumptionInformation(
        description="Isolated ERW functionality fixture; not production assumptions."
    )
    model.energy_system.set_nodes.set_data(
        df=pd.DataFrame(
            {"lon": [8.2], "lat": [46.8]}, index=pd.Index([NODE], name="node")
        ),
        source=source,
    )
    model.energy_system.set_edges.set_data(
        df=pd.DataFrame(
            columns=["node_from", "node_to"], index=pd.Index([], name="edge")
        ),
        source=source,
    )
    # Import services here only; production uses the real electricity/freight sectors.
    for name_carrier, power, energy, price in (
        ("electricity", "GW", "GWh", 50000.0),
        ("diesel", "GW", "GWh", 80000.0),
        ("truck_mileage", "tkm/h", "tkm", 0.1),
    ):
        carrier = GenericCarrier(name_carrier, model, power_unit=power)
        carrier.availability_import.set_data(
            default_value=math.inf, unit=power, source=source
        )
        carrier.price_import.set_data(
            default_value=price, unit=f"Euro/{energy}", source=source
        )
        carrier.carbon_intensity_carrier_import.set_data(
            default_value=0, unit=f"ton/{energy}", source=source
        )
        if name_carrier == "electricity":
            # A small neutral demand avoids an all-zero RHS in the disabled case.
            carrier.demand.set_data(default_value=0.001, unit=power, source=source)
        model.elements[name_carrier] = carrier
    model.build()
    coefficients = {}
    for tech in model.conversion_technologies.values():
        tech.max_diffusion_rate.set_data(default_value=math.inf, source=source)
    if enabled:
        app = model.elements["basalt_application"]
        limit = float(app.capacity_limit.df.loc[NODE])
        rate = limit * 1.01 if above_limit else FORCED_RATE_T_PER_H
        app.capacity_lower_limit.set_data(
            default_value=rate, unit="tproduct/h", source=source
        )
        app.min_full_load_hours_fraction.set_data(default_value=1.0, source=source)
        grinding = model.elements["basalt_grinding"]
        apply_cf = {
            k: v["default_value"]
            for row in app.conversion_factor.default_value
            for k, v in row.items()
        }
        grind_cf = {
            k: v["default_value"]
            for row in grinding.conversion_factor.default_value
            for k, v in row.items()
        }
        coefficients = {
            "forced_rate": rate,
            "capacity_limit": limit,
            "electricity_gwh_per_t": grind_cf["electricity"],
            "diesel_gwh_per_t": apply_cf["diesel"],
            "delivery_tkm_per_t": apply_cf["truck_mileage"],
            "removal_tco2_per_t": -float(app.carbon_intensity_technology.default_value),
        }
        assert coefficients["removal_tco2_per_t"] == 0.0525
    model.write()
    # The solver expects these empty containers even in a conversion-only fixture.
    for subset in (
        "set_storage_technologies",
        "set_transport_technologies",
        "set_retrofitting_technologies",
    ):
        (model.output_path / "set_technologies" / subset).mkdir(exist_ok=True)
    return model.output_path, coefficients


def solve(dataset: Path, *, infeasible: bool = False) -> Path:
    """Use the standard CLI and require the expected solver outcome."""
    executable = ROOT.parent / ".conda/zen-solve/bin/zen-garden"
    result_root = OUTPUT / "solves" / dataset.name
    result_root.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [
            str(executable),
            "--config",
            str(dataset.parent / "config.yaml"),
            "--dataset",
            str(dataset),
            "--folder_output",
            str(result_root),
        ],
        text=True,
        capture_output=True,
    )
    log = completed.stdout + "\n" + completed.stderr
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / f"{dataset.name}.log").write_text(log)
    if infeasible:
        if "Optimization: infeasible" not in log or "infeasible_or_unbounded" in log:
            raise AssertionError(
                f"Expected a confirmed infeasible model; inspect {dataset.name}.log"
            )
    else:
        if completed.returncode != 0:
            raise RuntimeError(log[-8000:])
        bench = json.loads(
            (result_root / dataset.name / "benchmarking.json").read_text()
        )
        assert bench["solver_status"] == 2, bench
    return result_root / dataset.name


def check_results(result: Path, coefficients: dict) -> dict:
    """Read actual saved production-unit flows and carbon accounting."""
    python = ROOT.parent / ".conda/zen-solve/bin/python"
    payload = {"result_dir": str(result), "coeffs": coefficients, "node": NODE}
    path = result / "smoke_check_payload.json"
    path.write_text(json.dumps(payload))
    completed = subprocess.run(
        [str(python), str(HERE / "check_saved_results.py"), str(path)],
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stdout + completed.stderr)
    print(completed.stdout)
    return {
        "solver_status": 2,
        "annual_basalt_t": coefficients["forced_rate"] * 8760,
        "gross_removal_tco2": coefficients["forced_rate"]
        * 8760
        * coefficients["removal_tco2_per_t"],
    }


def check_disabled(result: Path) -> None:
    python = ROOT.parent / ".conda/zen-solve/bin/python"
    code = """
import sys
import xarray as xr
from pathlib import Path
with xr.open_dataset(Path(sys.argv[1])/'variables.nc') as ds:
    assert 'basalt_application' not in ds.coords['set_conversion_technologies'].values
    assert abs(float(ds['carbon_emissions_annual'].sum())) < 1e-10
    flow = ds['flow_conversion_output'].sel(
        set_conversion_technologies='basalt_grinding',
        set_output_carriers='ground_basalt',
    )
    assert abs(float(flow.sum())) < 1e-10
print('Disabled application: no grinding and no removal.')
"""
    subprocess.run([str(python), "-c", code, str(result)], check=True)


def main() -> None:
    check_variant_registration()
    dataset, coefficients = build_dataset("erw_enabled")
    summary = check_results(solve(dataset), coefficients)
    dataset, _ = build_dataset("erw_disabled", enabled=False)
    check_disabled(solve(dataset))
    dataset, _ = build_dataset("erw_above_land_limit", above_limit=True)
    solve(dataset, infeasible=True)
    summary.update(
        disabled_case="optimal; no activity or removal", land_limit_case="infeasible"
    )
    (OUTPUT / "validation_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print("All generated ERW checks passed, including the land-ceiling boundary.")


if __name__ == "__main__":
    main()
