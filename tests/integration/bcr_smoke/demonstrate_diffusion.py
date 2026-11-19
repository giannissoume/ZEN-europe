"""Regress BCR diffusion separation with zero and legitimate initial capacity."""

import json
import shutil
import subprocess
from pathlib import Path

import build_and_run as b
import yaml

root = b.ROOT
out = Path(__file__).resolve().parent / "outputs/diffusion"
b.OUT = out
b.OUTPUT = out
source, _ = b.build("diffusion_seed", force=False)


def modify(path, fn):
    d = yaml.safe_load(path.read_text())
    fn(d)
    path.write_text(yaml.safe_dump(d, sort_keys=False))


summary = []
for name, limit in [
    ("unused_service", 50),
    ("zero_service", 0),
    ("below_seed", 49),
    ("endogenous_service", None),
    ("seeded_pyrolysis", 50),
]:
    ds = out / "generated" / name
    shutil.copytree(source, ds, dirs_exist_ok=True)
    modify(
        ds / "system.yaml",
        lambda d: d.update(optimized_years=2, interval_between_years=4),
    )
    (ds / "set_carriers/hard_coal/demand_yearly_variation.csv").write_text(
        "node,2026,2030\nCH,0,1\n"
    )
    modify(
        ds / "set_carriers/diesel/attributes.yaml",
        lambda d: d.update(availability_import={"default_value": 0, "unit": "MW"}),
    )
    t = ds / "set_technologies/set_conversion_technologies"
    modify(
        t / "pyrolysis/attributes.yaml",
        lambda d: d.update(max_diffusion_rate={"default_value": 0.13, "unit": "1"}),
    )
    if limit is not None:
        (t / "biochar_application/capacity_limit.csv").write_text(
            f"node,capacity_limit\nCH,{limit}\n"
        )
    if name == "seeded_pyrolysis":
        # Synthetic installed pyrolysis: 1 MW built in 2025. Later fuel demand
        # exceeds it, so an optimal result must include legitimate new investment.
        (t / "pyrolysis/capacity_existing.csv").write_text(
            "node,year_construction,capacity_existing\nCH,2025,1\n"
        )
        (ds / "set_carriers/hard_coal/demand_yearly_variation.csv").write_text(
            "node,2026,2030\nCH,0,1.4\n"
        )
        modify(
            t / "biochar_application/attributes.yaml",
            lambda d: d.update(
                capacity_lower_limit={"default_value": 50, "unit": "MW"}
            ),
        )
    result = b.solve(ds, infeasible=name != "seeded_pyrolysis")
    summary.append(
        dict(
            case=name,
            result=str(result),
            infeasible=name != "seeded_pyrolysis",
        )
    )
(out / "cases.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary))

subprocess.run(
    [
        str(root.parent / ".conda/zen-solve/bin/python"),
        str(Path(__file__).with_name("check_diffusion.py")),
        str(out),
    ],
    check=True,
)
