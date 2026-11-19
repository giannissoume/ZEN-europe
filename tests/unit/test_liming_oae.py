"""Normalization, accounting boundaries and geography of liming OAE."""

from types import SimpleNamespace

import pytest

from zen_europe.datasets.dataset_collections.liming_oae_parameters import (
    LimingOaeParameters,
)
from zen_europe.datasets.datasets.energy_system.marine_regions_eez import (
    MarineRegionsEez,
)
from zen_europe.elements.carriers.hydrated_lime import HydratedLime
from zen_europe.elements.carriers.limestone import Limestone
from zen_europe.elements.conversion_technologies.lime_ocean_application import (
    LimeOceanApplication,
)
from zen_europe.elements.conversion_technologies.lime_production_ccs import (
    LimeProductionCCS,
)


def test_production_normalization_and_capture_boundary(model):
    p = LimingOaeParameters(model.settings, model.source_path)
    cf = p.get_production_coefficients()
    r = 74.1 / 56.08
    assert cf["limestone"] == pytest.approx(1.94 / r)
    assert cf["natural_gas"] * 1000 == pytest.approx(3.76 / 3.6 / r)
    assert cf["electricity"] * 1e6 == pytest.approx(393 / r + 5.8)
    assert p.get_water_m3_per_t() == pytest.approx(2 * 0.321 / r)
    plant = LimeProductionCCS(model)
    gross = plant._set_carbon_intensity_technology().default_value
    assert gross == pytest.approx(0.786 / r)
    # Reuse the baseline dataset, not a separate OAE fuel-carbon coefficient.
    gas_factor = float(p.data["gas_carbon"].data.loc["natural_gas"])
    assert gas_factor == pytest.approx(0.20196)
    assert cf["carbon"] == pytest.approx(
        0.9 * (gross + gas_factor * cf["natural_gas"] * 1000)
    )
    assert cf["carbon"] == pytest.approx(0.6790466098785426)
    assert gross + gas_factor * cf["natural_gas"] * 1000 - cf[
        "carbon"
    ] == pytest.approx(0.07544962331983807)
    assert "gas_carbon" in p.data


def test_financial_and_service_normalizations(model):
    p = LimingOaeParameters(model.settings, model.source_path)

    def crf(i, n):
        return i * (1 + i) ** n / ((1 + i) ** n - 1)

    independent_plant = (
        (11.56 / crf(0.06, 20) + 19.51 / crf(0.085, 30) + 7.83 / crf(0.06, 40))
        * 8760
        / (74.1 / 56.08)
    )
    independent_hydrator = 3300000 / 15 * p.data["exchange"].get_dollar2euro(2025)
    assert p.get_capex_euro_per_tph() == pytest.approx(
        independent_plant + independent_hydrator
    )
    assert p.get_application_diesel_gwh_per_t() == pytest.approx(0.0005606596906666666)
    dollar = p.data["exchange"].get_dollar2euro(2023)
    inflation = p.data["inflation"].get_inflation_rate(2023, 2025)
    assert p.get_application_euro_per_t() == pytest.approx(
        (11250 / (24 * 30) + 2 * 11250 / 40000) * dollar * inflation
    )
    assert p.get_removal_tco2_per_t() == pytest.approx(1.5 * 44.01 / 74.1)
    # Real-price-year conversion changes EUR and USD components once.
    model.settings.time.price_year = 2024
    factor = p.data["inflation"].get_inflation_rate(2025, 2024)
    assert p.get_capex_euro_per_tph() == pytest.approx(
        (independent_plant + independent_hydrator) * factor
    )


def test_geography_and_national_allowance(model):
    areas = MarineRegionsEez(model.source_path).data
    assert len(areas) == 28
    assert (areas > 0).sum() == 22
    assert areas.sum() == 5019521
    assert areas.loc["EL"] == 482936
    assert areas.loc["UK"] == 727260
    model.config = SimpleNamespace(system=SimpleNamespace(set_nodes=["DE", "CH", "SI"]))
    p = LimingOaeParameters(model.settings, model.source_path)
    app = LimeOceanApplication(model)
    prod = LimeProductionCCS(model)
    cap = app._set_capacity_limit()
    assert list(cap.df.index) == ["DE", "CH", "SI"]
    assert cap.df.loc["DE"] == pytest.approx(56831 * 40 / 8760)
    assert cap.df.loc["CH"] == 0
    assert prod._set_capacity_limit().df.loc["CH"] == 0
    model.settings.liming_oae.eligible_area_fraction = 0.1
    assert p.get_capacity_limit(app).df.loc["DE"] == pytest.approx(56831 * 4 / 8760)
    with pytest.raises(ValueError, match="Unsupported"):
        p.data["areas"].get_area_km2(["XX"])


def test_carrier_and_removal_boundaries(model):
    assert Limestone(model)._set_availability_import().default_value == float("inf")
    assert Limestone(model)._set_carbon_intensity_carrier_import().default_value == 0
    assert HydratedLime(model)._set_availability_import().default_value == 0
    app = LimeOceanApplication(model)
    assert app._set_output_carrier().default_value == []
    assert app._set_carbon_intensity_technology().default_value == pytest.approx(
        -0.8908906882591094
    )
    assert app._set_capex_specific_conversion().default_value == 0
    assert app._set_opex_specific_fixed().default_value == 0
    assert app._set_lifetime().default_value == 100
    assert LimeProductionCCS(model)._set_lifetime().default_value == 20


def test_oae_source_notes_follow_configured_assumptions(model):
    """Generated provenance must describe the scenario actually calculated."""
    cfg = model.settings.liming_oae
    cfg.delivery_km = 175
    cfg.cargo_t = 35000
    cfg.access_days = 2
    cfg.loading_days = 3
    cfg.slurry_kwh_per_t = 4
    cfg.generator_efficiency = 0.5
    cfg.water_euro_per_m3 = 8
    cfg.limestone_euro_per_t = 25
    cfg.utility_price_year = 2024
    cfg.eligible_area_fraction = 0.25
    cfg.production_max_load = 0.9
    model.config = SimpleNamespace(system=SimpleNamespace(set_nodes=["DE", "CH"]))
    p = LimingOaeParameters(model.settings, model.source_path)
    app = LimeOceanApplication(model)
    plant = LimeProductionCCS(model)
    limestone = Limestone(model)

    conversion = app.conversion_factor
    note = conversion.sources[-1].description
    for expected in ("175 km", "35000-t", "2 access/return days", "4 kWh/t", "50%"):
        assert expected in note
    inputs = {
        k: v["default_value"]
        for item in conversion.default_value
        for k, v in item.items()
    }
    hourly_fuel = 1.408 * 11.63
    assert inputs["truck_mileage"] == 175
    assert inputs["diesel"] == pytest.approx(
        (hourly_fuel / 30 + hourly_fuel * 24 * 2 / 35000 + 0.004 / 0.5) / 1000
    )
    charter = app.opex_specific_variable
    for expected in ("3 loading days", "2 access days", "35000-t"):
        assert expected in charter.sources[-1].description
    assert charter.default_value == pytest.approx(
        (11250 / (24 * 30) + 11250 * 5 / 35000) * p._dollar_factor(2023)
    )
    water = plant.opex_specific_variable
    assert "8 EUR2024/m3" in water.sources[-1].description
    assert water.default_value == pytest.approx(
        p.get_water_m3_per_t() * 8 * p._euro_factor(2024)
    )
    assert "25 EUR2024/t" in limestone.price_import.sources[-1].description
    assert limestone.price_import.default_value == pytest.approx(
        25 * p._euro_factor(2024)
    )
    assert "fraction of 0.25" in app.capacity_limit.sources[-1].description
    assert app.capacity_limit.df.loc["DE"] == pytest.approx(56831 * 40 * 0.25 / 8760)
    assert "90%" in plant.max_load.sources[-1].description
    assert plant.max_load.default_value == 0.9
