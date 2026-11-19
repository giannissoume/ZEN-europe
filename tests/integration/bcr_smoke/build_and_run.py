"""Isolated BCR accounting checks; synthetic boundaries, diffusion disabled."""

import json
import math
import subprocess
from pathlib import Path

import pandas as pd
import yaml
from zen_creator import AssumptionInformation, Dataset, DatasetCollection, Model
from zen_creator.elements.carriers.carrier import GenericCarrier

from zen_europe.model_creator import DATA_PATH

ROOT = DATA_PATH.parent
HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
OUTPUT = OUT


def write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False))


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


def build(name, app=True, force=True, above=False, coapplication=False):
    Dataset._registries.clear()
    DatasetCollection._registries.clear()
    cfg = yaml.safe_load((DATA_PATH / "zen_europe_config.yaml").read_text())
    cfg["source_path"] = str(DATA_PATH / "raw_data")
    cfg["settings"] = {
        "time": {
            "reference_year": 2026,
            "last_year": 2026,
            "interval_between_years": 1,
        },
        "region": {"set_nodes": ["CH"]},
        "investment": {"use_existing_capacities": False, "use_diffusion_rates": False},
        "structure": {
            "energy_system": "",
            "set_sectors": [],
            "set_carriers": ["biochar", "biochar_for_application"],
            "set_conversion_technologies": [
                "pyrolysis",
                "biochar_to_hard_coal",
                "biochar_to_application",
            ]
            + (["biochar_application"] if app else []),
        },
    }
    if coapplication:
        cfg["settings"]["structure"]["set_carriers"] += ["basalt", "ground_basalt"]
        cfg["settings"]["structure"]["set_conversion_technologies"] += [
            "basalt_grinding",
            "basalt_application",
        ]
    cfg["system"] = {
        "total_hours_per_year": 8760,
        "unaggregated_time_steps_per_year": 8760,
        "aggregated_time_steps_per_year": 1,
        "conduct_time_series_aggregation": True,
        "use_rolling_horizon": False,
    }
    cfg["solver"] = {
        "name": "gurobi",
        "save_parameters": True,
        "run_diagnostics": True,
        "solver_options": {"DualReductions": 0},
    }
    cfg["analysis"] = {"overwrite_output": True, "earliest_year_of_data": 2026}
    path = OUT / "generation" / f"{name}.yaml"
    write_yaml(path, cfg)
    m = Model.from_config(path)
    m.name = name
    m.output_folder = OUT / "generated"
    src = AssumptionInformation(
        description=(
            "BCR accounting fixture: synthetic imports/demand/coproduct "
            "outlets, no existing capacity or diffusion; not deployment validation."
        )
    )
    m.energy_system.set_nodes.set_data(
        df=pd.DataFrame(
            {"lon": [8.2], "lat": [46.8]}, index=pd.Index(["CH"], name="node")
        ),
        source=src,
    )
    m.energy_system.set_edges.set_data(
        df=pd.DataFrame(
            columns=["node_from", "node_to"], index=pd.Index([], name="edge")
        ),
        source=src,
    )
    for name_c, price, ci in [
        ("biomass", 10, 0),
        ("electricity", 50, 0.1),
        ("diesel", 80, 0.267),
        ("truck_mileage", 0.1, 0.0001),
        ("oil", 0, 0),
        ("district_heat", 0, 0),
        ("hard_coal", 0, 0),
    ]:
        freight = name_c == "truck_mileage"
        power = "tkm/h" if freight else "MW"
        energy = "tkm" if freight else "MWh"
        c = GenericCarrier(name_c, m, power_unit=power)
        if name_c in ("biomass", "electricity", "diesel", "truck_mileage"):
            c.availability_import.set_data(
                default_value=math.inf, unit=power, source=src
            )
            c.price_import.set_data(
                default_value=price, unit=f"Euro/{energy}", source=src
            )
            c.carbon_intensity_carrier_import.set_data(
                default_value=ci, unit=f"ton/{energy}", source=src
            )
        if name_c in ("oil", "district_heat"):
            c.availability_export.set_data(
                default_value=math.inf, unit=power, source=src
            )
            c.availability_export_yearly.set_data(
                default_value=math.inf, unit=energy, source=src
            )
        if name_c == "hard_coal":
            c.demand.set_data(default_value=1, unit="MW", source=src)
        m.elements[name_c] = c
    m.build()
    rate = 0
    if app:
        a = m.elements["biochar_application"]
        rate = (
            float(a.capacity_limit.df.loc["CH"]) * 1.01
            if above
            else (1.0 if force else 0)
        )
        if coapplication:
            rate = float(a.capacity_limit.df.loc["CH"])
            erw = m.elements["basalt_application"]
            erw.capacity_lower_limit.set_data(
                default_value=float(erw.capacity_limit.df.loc["CH"]),
                unit="tproduct/h",
                source=src,
            )
            erw.min_full_load_hours_fraction.set_data(default_value=1, source=src)
        a.capacity_lower_limit.set_data(default_value=rate, unit="MW", source=src)
        a.min_full_load_hours_fraction.set_data(
            default_value=1 if force else 0, source=src
        )
    m.write()
    for s in (
        "set_storage_technologies",
        "set_transport_technologies",
        "set_retrofitting_technologies",
    ):
        (m.output_path / "set_technologies" / s).mkdir(exist_ok=True)
    return m.output_path, rate


if __name__ == "__main__":
    summary = []
    for name, app, force, above, coapplication in [
        ("mixed", True, True, False, False),
        ("zero", True, False, False, False),
        ("disabled", False, False, False, False),
        ("above", True, True, True, False),
        ("coapplication_limits", True, True, False, True),
    ]:
        ds, rate = build(name, app, force, above, coapplication)
        res = solve(ds, infeasible=above)
        summary.append(
            {
                "name": name,
                "result": str(res),
                "application": app,
                "coapplication": coapplication,
                "rate_mw": rate,
                "infeasible": above,
            }
        )
    (OUT / "cases.json").write_text(json.dumps(summary, indent=2))
    subprocess.run(
        [
            str(ROOT.parent / ".conda/zen-solve/bin/python"),
            str(HERE / "check_results.py"),
            str(OUT / "cases.json"),
        ],
        check=True,
    )
    print("BCR checks passed: four optimal cases and one expected infeasible case.")
