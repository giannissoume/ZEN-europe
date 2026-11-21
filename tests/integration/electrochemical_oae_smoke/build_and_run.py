"""Run compact seawater mineralization cases with the standard ZEN-garden CLI."""

import argparse
import json
import math
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

TECHNOLOGY = "seawater_mineralization"
HOURS = 8760
HYDROGEN_MW = 0.6216
POWER_DEMAND_MW = 0.001
POWER_PRICE = 50
POWER_CI = 0.1
FREIGHT_PRICE = 0.1
FREIGHT_CI = 0.0001


@dataclass
class Case:
    name: str
    years: tuple[int, ...]
    active_years: tuple[int, ...] = ()
    investment_years: tuple[int, ...] = ()
    node: str = "DE"
    enabled: bool = True
    infeasible: bool = False
    fuel_cell_mw: float = 0


def build(case: Case, work: Path) -> Path:
    import pandas as pd
    import yaml
    from zen_creator import AssumptionInformation, Model
    from zen_creator.elements.carriers.carrier import GenericCarrier

    from zen_europe.model_creator import DATA_PATH

    source = AssumptionInformation(
        description="Synthetic electricity, freight and industrial hydrogen offtake."
    )
    config = yaml.safe_load((DATA_PATH / "zen_europe_config.yaml").read_text())
    config["source_path"] = str(DATA_PATH / "raw_data")
    first, *rest = case.years
    config["settings"] = {
        "time": {
            "reference_year": first,
            "last_year": case.years[-1],
            "interval_between_years": rest[0] - first if rest else 1,
        },
        "region": {"set_nodes": [case.node]},
        "investment": {"use_diffusion_rates": False, "use_construction_times": False},
        "structure": {
            "energy_system": "",
            "set_sectors": [],
            "set_carriers": ["hydrogen"] + (["olivine"] if case.enabled else []),
            "set_conversion_technologies": (
                ([TECHNOLOGY] if case.enabled else [])
                + (["fuel_cell"] if case.fuel_cell_mw or not case.enabled else [])
            ),
        },
    }
    config["system"] = {
        "total_hours_per_year": HOURS,
        "unaggregated_time_steps_per_year": HOURS,
        "aggregated_time_steps_per_year": 1,
        "conduct_time_series_aggregation": True,
        "use_rolling_horizon": False,
    }
    config["solver"] = {"name": "highs", "save_parameters": True}
    config["analysis"] = {"overwrite_output": True, "earliest_year_of_data": first}
    work.mkdir(parents=True, exist_ok=True)
    path = work / "fixture.yaml"
    path.write_text(yaml.safe_dump(config))

    model = Model.from_config(path)
    model.name = case.name
    model.output_folder = work / "generated"
    model.energy_system.set_nodes.set_data(
        df=pd.DataFrame(
            {"lon": [8.2], "lat": [50.0]}, index=pd.Index([case.node], name="node")
        ),
        source=source,
    )
    model.energy_system.set_edges.set_data(
        df=pd.DataFrame(
            columns=["node_from", "node_to"], index=pd.Index([], name="edge")
        ),
        source=source,
    )
    for name, energy, price, ci in (
        ("electricity", "MWh", POWER_PRICE, POWER_CI),
        ("truck_mileage", "tkm", FREIGHT_PRICE, FREIGHT_CI),
    ):
        unit = "MW" if energy == "MWh" else "tkm/h"
        carrier = GenericCarrier(name, model, power_unit=unit)
        carrier.availability_import.set_data(
            default_value=math.inf, unit=unit, source=source
        )
        carrier.price_import.set_data(
            default_value=price, unit=f"Euro/{energy}", source=source
        )
        carrier.carbon_intensity_carrier_import.set_data(
            default_value=ci, unit=f"ton/{energy}", source=source
        )
        model.elements[name] = carrier
    model.elements["electricity"].demand.set_data(
        default_value=POWER_DEMAND_MW, unit="MW", source=source
    )
    hydrogen = model.elements["hydrogen"]
    hydrogen.demand.set_data(
        default_value=HYDROGEN_MW,
        yearly_variations_df=pd.Series(
            [int(year in case.active_years) for year in model.settings.time.years],
            index=pd.Index(model.settings.time.years, name="year"),
            name="demand",
        ),
        unit="MW",
        source=source,
    )
    hydrogen.price_shed_demand.set_data(default_value=math.inf, source=source)
    if case.fuel_cell_mw:
        sink = model.elements["fuel_cell"]
        sink.capacity_lower_limit.set_data(
            default_value=case.fuel_cell_mw, unit="MW", source=source
        )
        sink.min_full_load_hours_fraction.set_data(default_value=1, source=source)
    model.build()
    model.write()
    for subset in (
        "set_conversion_technologies",
        "set_storage_technologies",
        "set_transport_technologies",
        "set_retrofitting_technologies",
    ):
        (model.output_path / "set_technologies" / subset).mkdir(
            parents=True, exist_ok=True
        )
    return model.output_path


def main():
    from zen_europe.model_creator import DATA_PATH

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--solver-cli", type=Path, default=shutil.which("zen-garden"))
    args = parser.parse_args()
    if args.solver_cli is None:
        parser.error("Install zen-garden or provide --solver-cli.")
    cases = (
        Case("disabled", (2030,), enabled=False),
        Case("zero", (2030,)),
        Case("coastal", (2030,), (2030,), (2030,)),
        Case("fuel_cell_offtake", (2030,), investment_years=(2030,), fuel_cell_mw=0.2),
        Case("landlocked", (2030,), (2030,), node="CH", infeasible=True),
        Case("too_early", (2029,), (2029,), infeasible=True),
        Case("multiyear", (2029, 2030, 2031), (2030, 2031), (2030,)),
        Case("replacement", (2030, 2050), (2030, 2050), (2030, 2050)),
    )
    for case in cases:
        work = args.output.resolve() / case.name
        dataset = build(case, work)
        result = work / "solved"
        result.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(
            [
                str(args.solver_cli),
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
        log = completed.stdout + completed.stderr
        (work / "solve.log").write_text(log)
        if case.infeasible:
            assert "Optimization: infeasible" in log, log[-6000:]
            assert "infeasible_or_unbounded" not in log, log[-6000:]
            print(f"{case.name}: infeasible", flush=True)
            continue
        assert completed.returncode == 0, log[-6000:]
        assert re.search(r"Model status\s*:\s*Optimal", log), log[-6000:]
        payload = work / "check.json"
        payload.write_text(
            json.dumps(
                {
                    "case": asdict(case),
                    "result": str(result / case.name),
                    "source": str(DATA_PATH / "raw_data"),
                }
            )
        )
        subprocess.run(
            [
                str(args.solver_cli.parent / "python"),
                str(Path(__file__).with_name("check_results.py")),
                str(payload),
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
