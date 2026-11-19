"""Check saved BCR flows, source-derived costs and complete emissions balances."""

import json
import sys
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(sys.argv[1]).resolve().parent


def scalar(a):
    v = float(a.squeeze())
    assert np.isfinite(v), (a.name, v)
    return v


def close(a, b):
    assert np.isclose(a, b, rtol=1e-7, atol=1e-8), (a, b)


summary = []
for c in json.loads((ROOT / "cases.json").read_text()):
    if c["infeasible"]:
        continue
    r = Path(c["result"])
    assert json.loads((r / "benchmarking.json").read_text())["solver_status"] == 2
    d = xr.open_dataset(r / "variables.nc")
    p = xr.open_dataset(r / "parameters.nc")
    coapp = c.get("coapplication", False)
    assert set(d.set_conversion_technologies.values) == {
        "pyrolysis",
        "biochar_to_hard_coal",
        "biochar_to_application",
    } | ({"biochar_application"} if c["application"] else set()) | (
        {"basalt_grinding", "basalt_application"} if coapp else set()
    )
    carriers = {
        "biochar",
        "biochar_for_application",
        "biomass",
        "electricity",
        "oil",
        "district_heat",
        "hard_coal",
    } | ({"diesel", "truck_mileage"} if c["application"] else set())
    if coapp:
        carriers.update({"basalt", "ground_basalt"})
    assert set(d.set_carriers.values) == carriers

    def f(direction, t, k, d=d):
        return scalar(
            d["flow_conversion_" + direction].sel(
                set_conversion_technologies=t,
                **{"set_" + direction + "_carriers": k},
                set_nodes="CH",
            )
        )

    def v(k, t, d=d):
        return scalar(d[k].sel(set_technologies=t, set_location="CH"))

    hours = scalar(p.time_steps_operation_duration)
    close(hours, 8760)
    app = (
        f("input", "biochar_application", "biochar_for_application") * 1000
        if c["application"]
        else 0
    )
    close(app, c["rate_mw"])
    fuel = f("input", "biochar_to_hard_coal", "biochar") * 1000
    close(fuel, 1)
    out = f("output", "pyrolysis", "biochar") * 1000
    close(out, app + fuel)
    close(f("input", "biochar_to_application", "biochar") * 1000, app)
    close(f("output", "biochar_to_application", "biochar_for_application") * 1000, app)
    close(v("cost_capex_overnight", "biochar_to_application"), 0)
    close(v("cost_opex_yearly", "biochar_to_application"), 0)
    close(scalar(d.flow_export.sel(set_carriers="biochar_for_application")), 0)
    close(scalar(p.availability_import.sel(set_carriers="biochar_for_application")), 0)
    close(scalar(p.availability_export.sel(set_carriers="biochar_for_application")), 0)
    close(f("output", "biochar_to_hard_coal", "hard_coal") * 1000, fuel)
    for k, frac in [("biomass", 0.96 / 0.45), ("electricity", 0.04 / 0.45)]:
        close(f("input", "pyrolysis", k) * 1000, out * frac)
    for k, frac in [("oil", 0.19 / 0.45), ("district_heat", 0.24 / 0.45)]:
        close(f("output", "pyrolysis", k) * 1000, out * frac)
        close(scalar(d.flow_export.sel(set_carriers=k)) * 1000, out * frac)
    close((1 + 0.19 / 0.45 + 0.24 / 0.45) / (0.96 / 0.45 + 0.04 / 0.45), 0.88)
    imports = {
        "biochar": 0,
        "biochar_for_application": 0,
        "biomass": out * 0.96 / 0.45 / 1000,
        "electricity": out * 0.04 / 0.45 / 1000,
        "hard_coal": 0,
        "oil": 0,
        "district_heat": 0,
    }
    if c["application"]:
        close(f("input", "biochar_application", "diesel") * 1000, app * 0.000864)
        close(f("input", "biochar_application", "truck_mileage") * 1e6, app * 14.4)
        imports.update(diesel=app * 0.000864 / 1000, truck_mileage=app * 14.4 / 1e6)
        close(v("cost_capex_overnight", "biochar_application"), 0)
        close(
            v("cost_opex_yearly", "biochar_application") * 1e6,
            app * hours * (6.23 * 1.3175551998230455 / (25 / 3.6)),
        )
    basalt = 0.0
    basalt_price = 0.0
    if coapp:
        basalt = f("input", "basalt_application", "ground_basalt") * 1000
        land_bcr = (
            scalar(
                p.capacity_limit.sel(
                    set_technologies="biochar_application", set_location="CH"
                )
            )
            * 1000
        )
        land_erw = (
            scalar(
                p.capacity_limit.sel(
                    set_technologies="basalt_application", set_location="CH"
                )
            )
            * 1000
        )
        close(app, land_bcr)
        close(basalt, land_erw)
        close(basalt, app / (25 / 3.6) * 10)
        close(f("output", "basalt_grinding", "ground_basalt") * 1000, basalt)
        close(f("input", "basalt_grinding", "basalt") * 1000, basalt)
        close(f("input", "basalt_application", "diesel"), basalt * 6e-6)
        close(f("input", "basalt_application", "truck_mileage"), basalt * 100 / 1e6)
        imports.update(basalt=basalt / 1000, ground_basalt=0)
        imports["electricity"] += (
            basalt * (0.1947445179009531 / 69.9062230049315) / 1000
        )
        imports["diesel"] += basalt * 6e-6
        imports["truck_mileage"] += basalt * 100 / 1e6
        # Saved price is used only to reconcile unchanged ERW procurement;
        # the source reconstruction is covered by the independent ERW review.
        basalt_price = scalar(p.price_import.sel(set_carriers="basalt")) * 1000
    for k, value in imports.items():
        close(scalar(d.flow_import.sel(set_carriers=k)), value)
    close(scalar(d.flow_export.sel(set_carriers="biochar")), 0)
    close(scalar(p.availability_import.sel(set_carriers="biochar")), 0)
    close(scalar(p.availability_export.sel(set_carriers="biochar")), 0)
    cap = v("capacity", "pyrolysis") * 1000
    close(cap, out)
    # Independent source-scenario means: low/high endpoints interpolate linearly,
    # reference follows intermediate DEA years; cost basis is already EUR2025.
    capex = (
        ((1 + (1 + (0.9 - 1) / 25) + (1 + (0.65 - 1) / 25)) / 3) * 1000 * 0.88 / 0.45
    )
    fom = (
        (
            (
                0.125
                + (0.11875 + (0.1125 - 0.11875) / 25)
                + (0.1375 + (0.1 - 0.1375) / 25)
            )
            / 3
        )
        * 1000
        * 0.88
        / 0.45
    )
    close(v("cost_capex_overnight", "pyrolysis") * 1e6, cap * 1000 * capex)
    close(v("cost_opex_yearly", "pyrolysis") * 1e6, cap * 1000 * fom)
    close(v("cost_capex_overnight", "biochar_to_hard_coal"), 0)
    close(v("cost_opex_yearly", "biochar_to_hard_coal"), 0)
    operational = hours * (
        out * 0.04 / 0.45 * 0.1 + app * 0.000864 * 0.267 + app * 14.4 * 0.0001
    )
    operational += (
        hours
        * basalt
        * ((0.1947445179009531 / 69.9062230049315) * 0.1 + 0.006 * 0.267 + 100 * 0.0001)
    )
    gross = app * hours * 0.3168 + basalt * hours * 0.0406875
    close(scalar(d.carbon_emissions_carrier_total) * 1e6, operational)
    close(scalar(d.carbon_emissions_technology_total) * 1e6, -gross)
    total = scalar(d.carbon_emissions_annual) * 1e6
    close(total, operational - gross)
    close(
        scalar(d.cost_carrier_total) * 1e6,
        hours
        * (
            out * 0.96 / 0.45 * 10
            + out * 0.04 / 0.45 * 50
            + app * 0.000864 * 80
            + app * 14.4 * 0.1
            + basalt
            * (
                basalt_price
                + (0.1947445179009531 / 69.9062230049315) * 50
                + 0.006 * 80
                + 100 * 0.1
            )
        ),
    )
    summary.append(
        dict(
            case=c["name"],
            applied_mwh=app * hours,
            pyrolysis_mwh=out * hours,
            gross_removal_t=gross,
            net_emissions_t=total,
            residual_t=total - operational + gross,
        )
    )
print(json.dumps(summary, indent=2))
(ROOT / "checked.json").write_text(json.dumps(summary, indent=2))
