"""Generate actual OAE elements and solve small ordinary ZEN-garden cases.

Service imports and storage economics are synthetic fixture boundaries.
OAE coefficients, coastal limits and the storage credit use production code.
No solver equations or installed dependencies are modified.
"""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import pandas as pd
import yaml
from zen_creator import AssumptionInformation, Dataset, DatasetCollection, Model
from zen_creator.elements.carriers.carrier import GenericCarrier
from zen_creator.elements.conversion_technologies.conversion_technology import (
    GenericConversionTechnology,
)

from zen_europe.datasets.dataset_collections.liming_oae_parameters import (
    LimingOaeParameters,
)
from zen_europe.elements.conversion_technologies.carbon_storage import CarbonStorage
from zen_europe.model_creator import DATA_PATH

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTPUT = HERE / "outputs"


def write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def build(
    name,
    *,
    node="DE",
    force=True,
    storage=True,
    above_limit=False,
    application=True,
    gas_route="fossil",
):
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
        "region": {"set_nodes": [node]},
        "structure": {
            "energy_system": "",
            "set_sectors": [],
            "set_carriers": ["limestone", "hydrated_lime", "carbon"],
            "set_conversion_technologies": (
                ["lime_production_ccs"]
                + (["lime_ocean_application"] if application else [])
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
    config["solver"] = {
        "name": "gurobi",
        "run_diagnostics": True,
        "save_parameters": True,
        "solver_options": {"DualReductions": 0, "Threads": 2},
    }
    config["analysis"] = {"overwrite_output": True, "earliest_year_of_data": 2026}
    path = OUTPUT / "generation" / (name + ".yaml")
    write_yaml(path, config)
    model = Model.from_config(path)
    model.name = name
    model.output_folder = OUTPUT / "generation"
    source = AssumptionInformation(description="Synthetic small OAE test boundary.")
    model.energy_system.set_nodes.set_data(
        df=pd.DataFrame(
            {"lon": [8.2], "lat": [50.0]}, index=pd.Index([node], name="node")
        ),
        source=source,
    )
    model.energy_system.set_edges.set_data(
        df=pd.DataFrame(
            columns=["node_from", "node_to"], index=pd.Index([], name="edge")
        ),
        source=source,
    )
    gas_ci = 0.20196 if gas_route == "fossil" else 0
    for name_c, power, energy, price, ci in (
        ("electricity", "GW", "GWh", 50000, 0.1),
        ("diesel", "GW", "GWh", 80000, 0.267),
        ("truck_mileage", "tkm/h", "tkm", 0.1, 0.0001),
        ("natural_gas", "GW", "GWh", 40000, gas_ci),
    ):
        c = GenericCarrier(name_c, model, power_unit=power)
        c.availability_import.set_data(
            default_value=math.inf, unit=power, source=source
        )
        c.price_import.set_data(
            default_value=price, unit=f"Euro/{energy}", source=source
        )
        carbon_unit = f"ton/{energy}"
        # Electricity/diesel/NG import intensities below are expressed per MWh.
        c.carbon_intensity_carrier_import.set_data(
            default_value=ci,
            unit=carbon_unit if name_c == "truck_mileage" else "ton/MWh",
            source=source,
        )
        if name_c == "electricity":
            c.demand.set_data(default_value=0.000001, unit="GW", source=source)
        model.elements[name_c] = c
    # An ordinary conversion sink with the real CarbonStorage credit method.
    sink = GenericConversionTechnology("fixture_storage", model, power_unit="tCO2/h")
    sink.reference_carrier.set_data(default_value=["carbon"], source=source)
    sink.input_carrier.set_data(default_value=["carbon"], source=source)
    sink.output_carrier.set_data(default_value=[], source=source)
    sink.conversion_factor.set_data(default_value=[], source=source)
    sink.lifetime.set_data(default_value=100, source=source)
    CarbonStorage._set_carbon_intensity_technology(sink)
    sink.opex_specific_variable.set_data(
        default_value=10, unit="Euro/tCO2", source=source
    )
    sink.capacity_limit.set_data(
        default_value=math.inf if storage else 0, unit="tCO2/h", source=source
    )
    model.elements[sink.name] = sink
    if gas_route == "synthetic":
        from zen_europe.datasets.datasets.technology.methanation_goetz import (
            MethanationGoetz,
        )

        # Use baseline carbon/methane normalization; hydrogen is a priced service.
        from zen_europe.elements.conversion_technologies.methanation import Methanation

        reference = Methanation(model)
        cf = (
            MethanationGoetz(model.source_path)
            .get_conversion_factor_methanation(reference)
            .default_value
        )
        synth = GenericConversionTechnology(
            "fixture_methanation", model, power_unit="MW"
        )
        synth.reference_carrier.set_data(default_value=["natural_gas"], source=source)
        synth.input_carrier.set_data(
            default_value=["carbon", "hydrogen"], source=source
        )
        synth.output_carrier.set_data(default_value=["natural_gas"], source=source)
        synth.conversion_factor.set_data(default_value=cf, source=source)
        synth.lifetime.set_data(default_value=100, source=source)
        h = GenericCarrier("hydrogen", model, power_unit="MW")
        h.availability_import.set_data(default_value=math.inf, unit="MW", source=source)
        h.price_import.set_data(default_value=50, unit="Euro/MWh", source=source)
        model.elements[h.name] = h
        model.elements[synth.name] = synth
        model.elements["natural_gas"].availability_import.set_data(
            default_value=0, unit="GW", source=source
        )
    model.build()
    p = LimingOaeParameters(model.settings, model.source_path)
    coeff = p.get_production_coefficients()
    coeff.update(
        removal=p.get_removal_tco2_per_t(),
        diesel=p.get_application_diesel_gwh_per_t(),
        process=0.786 / (74.1 / 56.08),
        gas_ci=gas_ci,
        production_fixed_opex=p.get_capex_euro_per_tph() * 0.025,
        production_variable_opex=p.get_water_m3_per_t() * 6,
        application_variable_opex=p.get_application_euro_per_t(),
    )
    app = model.elements.get("lime_ocean_application")
    if force and app is not None:
        rate = float(app.capacity_limit.df.loc[node]) * 1.01 if above_limit else 1.0
        app.capacity_lower_limit.set_data(
            default_value=rate, unit="tproduct/h", source=source
        )
        app.min_full_load_hours_fraction.set_data(default_value=1.0, source=source)
    else:
        rate = 0
    coeff.update(
        forced_rate=rate,
        node=node,
        gas_route=gas_route,
        storage=storage,
        application=application,
    )
    model.write()
    for subset in (
        "set_storage_technologies",
        "set_transport_technologies",
        "set_retrofitting_technologies",
    ):
        (model.output_path / "set_technologies" / subset).mkdir(exist_ok=True)
    return model.output_path, coeff


def solve(dataset, coeff, *, infeasible=False):
    executable = ROOT.parent / ".conda/zen-solve/bin/zen-garden"
    result = OUTPUT / "solves" / dataset.name
    result.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [
            str(executable),
            "--config",
            str(dataset.parent / "config.yaml"),
            "--dataset",
            str(dataset),
            "--folder_output",
            str(result),
        ],
        capture_output=True,
        text=True,
    )
    log = completed.stdout + "\n" + completed.stderr
    (OUTPUT / (dataset.name + ".log")).write_text(log)
    if infeasible:
        assert (
            "Optimization: infeasible" in log and "infeasible_or_unbounded" not in log
        ), log[-5000:]
        return {"case": dataset.name, "condition": "infeasible"}
    assert completed.returncode == 0, log[-5000:]
    saved = result / dataset.name
    bench = json.loads((saved / "benchmarking.json").read_text())
    assert bench["solver_status"] == 2, bench
    payload = OUTPUT / (dataset.name + "-check.json")
    payload.write_text(json.dumps(dict(result=str(saved), coefficients=coeff)))
    check = subprocess.run(
        [
            str(ROOT.parent / ".conda/zen-solve/bin/python"),
            str(HERE / "check_results.py"),
            str(payload),
        ],
        capture_output=True,
        text=True,
    )
    assert check.returncode == 0, check.stdout + check.stderr
    print(check.stdout, flush=True)
    return json.loads(check.stdout)


def main():
    cases = [
        ("forced_fossil", {}),
        ("zero_application", {"force": False}),
        ("no_application", {"force": False, "application": False}),
        ("forced_synthetic", {"gas_route": "synthetic"}),
        ("forced_biogenic", {"gas_route": "biogenic"}),
        ("no_storage", {"storage": False, "infeasible": True}),
        ("landlocked", {"node": "CH", "force": False}),
        ("above_marine_allowance", {"above_limit": True, "infeasible": True}),
    ]
    report = []
    for name, kwargs in cases:
        infeasible = kwargs.pop("infeasible", False)
        print("Checking", name, flush=True)
        dataset, coeff = build(name, **kwargs)
        report.append(solve(dataset, coeff, infeasible=infeasible))
        (OUTPUT / "results.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
