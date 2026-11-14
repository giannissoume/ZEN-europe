from __future__ import annotations

import math

import pytest
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation
from zen_creator.model import Model
from zen_creator.utils.settings import ModelSet

from zen_europe.datasets.dataset_collections.biochar_application_parameters import (
    BiocharApplicationParameters,
)
from zen_europe.datasets.datasets.financial.dea import DEA
from zen_europe.datasets.datasets.financial.ECB import ECBInflation
from zen_europe.datasets.datasets.technology.dalgaard_application_diesel import (
    DalgaardApplicationDiesel,
)
from zen_europe.datasets.datasets.technology.eu_biochar_application_limit import (
    EuBiocharApplicationLimit,
)
from zen_europe.datasets.datasets.technology.eurofins_straw_biochar import (
    EurofinsStrawBiochar,
)
from zen_europe.datasets.datasets.technology.ipcc_biochar_permanence import (
    IpccBiocharPermanence,
)
from zen_europe.datasets.datasets.technology.teichmann_biochar_application_cost import (
    TeichmannBiocharApplicationCost,
)
from zen_europe.elements.carriers.biochar import Biochar
from zen_europe.elements.conversion_technologies.biochar_application import (
    BiocharApplication,
)
from zen_europe.elements.conversion_technologies.biochar_to_hard_coal import (
    BiocharToHardCoal,
)
from zen_europe.elements.conversion_technologies.pyrolysis import Pyrolysis
from zen_europe.elements.sectors.biochar_cdr import BiocharCDRSector
from zen_europe.model_creator import DATA_PATH
from zen_europe.utils.constants import Constants


def _conversion_factor_by_carrier(
    conversion_factor: list[dict[str, dict[str, float]]],
) -> dict[str, float]:
    return {
        carrier: values["default_value"]
        for entry in conversion_factor
        for carrier, values in entry.items()
    }


def _active_investment_periods(lifetime: float, interval_between_years: int) -> int:
    """Match ZEN-garden's floor(lifetime / interval) bookkeeping periods."""
    return int(math.floor(lifetime / interval_between_years))


def test_pyrolysis_uses_biochar_as_reference_carrier(model: Model) -> None:
    pyrolysis = Pyrolysis(model=model)

    assert pyrolysis.reference_carrier.default_value == ["biochar"]
    assert pyrolysis.output_carrier.default_value == ["biochar", "district_heat", "oil"]


def test_pyrolysis_conversion_factors_are_rebased_to_biochar(model: Model) -> None:
    factors = _conversion_factor_by_carrier(
        DEA(source_path=model.source_path).get_conversion_factor_pyrolysis()
    )

    assert factors == pytest.approx(
        {
            "biomass": 0.96 / 0.45,
            "electricity": 0.04 / 0.45,
            "district_heat": 0.24 / 0.45,
            "oil": 0.19 / 0.45,
        }
    )


def test_application_source_scalars(model: Model) -> None:
    source_path = model.source_path

    assert EurofinsStrawBiochar(source_path).get_organic_carbon_fraction() == 0.75
    assert IpccBiocharPermanence(source_path).get_retained_fraction() == 0.80
    assert DalgaardApplicationDiesel(source_path).get_diesel_liter_per_ton() == 0.6
    teichmann = TeichmannBiocharApplicationCost(source_path)
    assert teichmann.get_cost_eur_per_ton() == 6.23
    assert teichmann.get_cost_year() == 2012
    assert EuBiocharApplicationLimit(source_path).get_cumulative_limit_t_per_ha() == 50


def test_biochar_application_coefficients(model: Model) -> None:
    application = BiocharApplication(model=model)
    parameters = BiocharApplicationParameters(model.settings, model.source_path)
    biochar_mwh_per_ton = Constants.BIOCHAR_GWH_PER_TON * 1000

    conversion = application._set_conversion_factor()
    diesel = _conversion_factor_by_carrier(conversion.default_value)["diesel"]
    intensity = application._set_carbon_intensity_technology()
    cost = application._set_opex_specific_variable()
    inflation = ECBInflation(model.source_path).get_inflation_rate(
        base_year=2012, target_year=model.settings.time.price_year
    )

    assert diesel == pytest.approx(0.000864)
    assert diesel == pytest.approx(parameters.diesel_mwh_per_mwh_biochar())
    assert conversion.default_value[0]["diesel"]["unit"] == "GWh/GWh"
    assert intensity.default_value == pytest.approx(-0.3168)
    assert intensity.unit == "ton/MWh"
    assert -intensity.default_value * biochar_mwh_per_ton == pytest.approx(2.2)
    assert intensity.default_value == pytest.approx(
        -parameters.stored_co2_ton_per_mwh_biochar()
    )
    assert cost.default_value == pytest.approx(6.23 * inflation / biochar_mwh_per_ton)
    assert cost.unit == "Euro/MWh"


def test_biochar_to_hard_coal_is_energy_equivalent(model: Model) -> None:
    substitution = BiocharToHardCoal(model=model)

    assert substitution.reference_carrier.default_value == ["hard_coal"]
    assert substitution.input_carrier.default_value == ["biochar"]
    assert substitution.output_carrier.default_value == ["hard_coal"]
    factors = _conversion_factor_by_carrier(
        substitution._set_conversion_factor().default_value
    )
    assert factors["biochar"] == 1
    assert substitution.carbon_intensity_technology.default_value == 0


def test_biochar_cdr_sector_contains_bcr_elements() -> None:
    sector = BiocharCDRSector()

    assert sector.name == "biochar_cdr"
    assert Pyrolysis in sector.elements
    assert Biochar in sector.elements
    assert BiocharToHardCoal in sector.elements
    assert BiocharApplication in sector.elements


@pytest.mark.parametrize("interval_between_years", [2, 4])
def test_biochar_service_routes_remain_active_for_time_resolutions(
    model: Model, interval_between_years: int
) -> None:
    application = BiocharApplication(model=model)
    substitution = BiocharToHardCoal(model=model)

    for technology in (application, substitution):
        lifetime = technology._set_lifetime().default_value
        assert lifetime == 100
        assert _active_investment_periods(lifetime, interval_between_years) > 0


def test_biochar_application_cites_its_sources(model: Model) -> None:
    application = BiocharApplication(model=model)
    expected_names = {
        "eurofins_straw_biochar",
        "ipcc_biochar_permanence",
        "dalgaard_application_diesel",
        "teichmann_biochar_application_cost",
        "ecb_inflation",
        "worldbank_arable_land",
        "eu_biochar_application_limit",
    }

    for setter in (
        application._set_conversion_factor,
        application._set_carbon_intensity_technology,
        application._set_opex_specific_variable,
    ):
        source = setter().sources[-1]
        assert isinstance(source, SourceInformation)
        assert isinstance(source.metadata, dict)
        names = {
            metadata.name
            for metadata in source.metadata.values()
            if isinstance(metadata, MetaData)
        }
        assert names == expected_names


def test_application_comparison_removes_only_the_application_technology() -> None:
    model_set = ModelSet.load_from_yaml(DATA_PATH / "models.yaml")

    assert model_set.settings_patch("bcr") == {}
    assert model_set.settings_patch("bcr_without_application") == {
        "structure": {"remove_technologies": ["biochar_application"]}
    }


def test_biochar_application_delivery_units(model: Model) -> None:
    application = BiocharApplication(model=model)
    conversion = application._set_conversion_factor()
    factors = _conversion_factor_by_carrier(conversion.default_value)
    assert application.input_carrier.default_value == [
        "biochar",
        "diesel",
        "truck_mileage",
    ]
    # One dry tonne has 25/3.6 MWh and requires exactly 100 tkm.
    assert factors["truck_mileage"] == pytest.approx(14.4)
    assert factors["truck_mileage"] * (25 / 3.6) == pytest.approx(100)
    assert factors["diesel"] == pytest.approx(0.000864)
    assert "truck_transport" in BiocharCDRSector.required_sectors
    assert "passenger_transport" in BiocharCDRSector.required_sectors


@pytest.mark.parametrize(
    "reference_year,last_year,interval",
    [(2026, 2050, 4), (2030, 2050, 2), (2040, 2050, 1)],
)
def test_biochar_land_cap_reuses_area_without_excluding_erw(
    model: Model, reference_year: int, last_year: int, interval: int
) -> None:
    from types import SimpleNamespace

    from zen_europe.datasets.dataset_collections.basalt_erw_parameters import (
        BasaltErwParameters,
    )
    from zen_europe.datasets.datasets.energy_system.worldbank_arable_land import (
        WorldBankArableLand,
    )

    model.settings.time.reference_year = reference_year
    model.settings.time.last_year = last_year
    model.settings.time.interval_between_years = interval
    model.config = SimpleNamespace(system=SimpleNamespace(set_nodes=["CH", "DE"]))
    application = BiocharApplication(model=model)
    area = WorldBankArableLand(model.source_path).get_arable_land_ha(
        ["CH", "DE"], year=2024
    )
    land = application._set_capacity_limit()
    assert land.unit == "MW"
    assert land.df.to_dict() == pytest.approx((area * 2 * (25 / 3.6) / 8760).to_dict())
    # Convert the generated MW ceiling back to annual mass per hectare.
    annual_t_per_ha = land.df * 8760 / (25 / 3.6) / area
    assert annual_t_per_ha.to_dict() == pytest.approx({"CH": 2.0, "DE": 2.0})
    assert (annual_t_per_ha * 25).to_dict() == pytest.approx({"CH": 50.0, "DE": 50.0})
    assert application.max_load.default_value == 1
    # BCR reads the shared area but does not consume it or change ERW's ceiling.
    from zen_europe.elements.conversion_technologies.basalt_application import (
        BasaltApplication,
    )

    erw = BasaltApplication(model=model)
    limit = BasaltErwParameters(
        model.settings, model.source_path
    ).get_application_capacity_limit(erw)
    assert limit.df.to_dict() == pytest.approx((area * 20 / 8760).to_dict())
