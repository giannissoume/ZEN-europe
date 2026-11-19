"""Unit tests for the simplified basalt ERW pathway."""

from __future__ import annotations

import math

import pytest
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation
from zen_creator.model import Model

from zen_europe.datasets.dataset_collections.basalt_erw_parameters import (
    BasaltErwParameters,
)
from zen_europe.datasets.datasets.financial.ECB import ECBDollar2Euro, ECBInflation
from zen_europe.datasets.datasets.technology.beerling_basalt_removal import (
    BeerlingBasaltRemoval,
)
from zen_europe.datasets.datasets.technology.cobo_basalt_electricity import (
    CoboBasaltElectricity,
)
from zen_europe.datasets.datasets.technology.cobo_weathering_efficiency import (
    CoboWeatheringEfficiency,
)
from zen_europe.datasets.datasets.technology.dalgaard_application_diesel import (
    DalgaardApplicationDiesel,
)
from zen_europe.datasets.datasets.technology.netl_basalt_erw_costs import (
    NetlBasaltErwCosts,
)
from zen_europe.elements.carriers.basalt import Basalt
from zen_europe.elements.carriers.ground_basalt import GroundBasalt
from zen_europe.elements.conversion_technologies.basalt_application import (
    BasaltApplication,
)
from zen_europe.elements.conversion_technologies.basalt_grinding import BasaltGrinding
from zen_europe.elements.sectors.basalt_erw import BasaltErwSector
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
    return int(math.floor(lifetime / interval_between_years))


def test_source_scalars(model: Model) -> None:
    source_path = model.source_path
    beerling = BeerlingBasaltRemoval(source_path)
    electricity = CoboBasaltElectricity(source_path)
    netl = NetlBasaltErwCosts(source_path)

    assert beerling.get_removal_tco2_per_t_basalt() == 0.0525
    assert CoboWeatheringEfficiency(source_path).get_cdr_efficiency() == 0.775
    assert electricity.get_electricity_mwh_per_t_basalt() == pytest.approx(
        0.1947445179009531 / 69.9062230049315
    )
    assert netl.get_total_plant_cost_usd() == 26_001_000
    assert netl.get_fixed_opex_usd_per_year() == 3_121_279 + 296_406
    assert netl.get_rock_price_usd_per_t() == 25
    assert netl.get_application_cost_usd_per_t() == 6
    assert netl.get_lifetime_years() == 31
    assert netl.get_max_load() == 0.85
    assert DalgaardApplicationDiesel(source_path).get_diesel_liter_per_ton() == 0.6


def test_grinding_and_application_coefficients(model: Model) -> None:
    parameters = BasaltErwParameters(model.settings, model.source_path)
    grinding = BasaltGrinding(model=model)
    application = BasaltApplication(model=model)
    money = ECBDollar2Euro(model.source_path).get_dollar2euro(2023) * (
        ECBInflation(model.source_path).get_inflation_rate(
            2023, model.settings.time.price_year
        )
    )
    capacity = 250_000 / 8760

    grind_cf = _conversion_factor_by_carrier(
        grinding._set_conversion_factor().default_value
    )
    assert grind_cf["basalt"] == 1.0
    assert grind_cf["electricity"] == pytest.approx(
        parameters.electricity_gwh_per_tproduct()
    )
    assert grinding._set_conversion_factor().default_value[1]["electricity"][
        "unit"
    ] == ("GWh/tproduct")

    apply_cf = _conversion_factor_by_carrier(
        application._set_conversion_factor().default_value
    )
    assert apply_cf["truck_mileage"] == 100.0
    assert apply_cf["diesel"] == pytest.approx(parameters.diesel_gwh_per_tproduct())
    assert apply_cf["diesel"] == pytest.approx(
        0.6 * Constants.DIESEL_KWH_PER_LITER / 1_000_000
    )

    assert apply_cf["diesel"] == pytest.approx(6e-6)

    intensity = application._set_carbon_intensity_technology()
    assert intensity.default_value == pytest.approx(-0.0525 * 0.775)
    assert intensity.default_value == pytest.approx(-0.0406875)
    assert intensity.unit == "ton/tproduct"
    assert -1000 * intensity.default_value == pytest.approx(40.6875)

    assert grinding._set_capex_specific_conversion().default_value == pytest.approx(
        26_001_000 / capacity * money
    )
    assert grinding._set_opex_specific_fixed().default_value == pytest.approx(
        (3_121_279 + 296_406) / capacity * money
    )
    assert grinding._set_max_load().default_value == 0.85
    assert grinding._set_lifetime().default_value == 31
    assert application._set_opex_specific_variable().default_value == pytest.approx(
        6 * money
    )


def test_basalt_carrier_purchase_and_ground_basalt_no_import(model: Model) -> None:
    basalt = Basalt(model=model)
    ground = GroundBasalt(model=model)
    money = ECBDollar2Euro(model.source_path).get_dollar2euro(2023) * (
        ECBInflation(model.source_path).get_inflation_rate(
            2023, model.settings.time.price_year
        )
    )

    assert basalt._set_availability_import().default_value == pytest.approx(math.inf)
    assert basalt._set_price_import().default_value == pytest.approx(25 * money)
    assert basalt._set_carbon_intensity_carrier_import().default_value == 0
    assert ground._set_availability_import().default_value == 0


def test_sector_registration_and_dependencies() -> None:
    sector = BasaltErwSector()

    assert sector.name == "basalt_erw"
    assert sector.required_sectors == [
        "electricity",
        "truck_transport",
        "passenger_transport",
    ]
    assert BasaltGrinding in sector.elements
    assert BasaltApplication in sector.elements
    assert Basalt in sector.elements
    assert GroundBasalt in sector.elements


@pytest.mark.parametrize("interval_between_years", [2, 4])
def test_application_service_remains_active(
    model: Model, interval_between_years: int
) -> None:
    lifetime = BasaltApplication(model=model)._set_lifetime().default_value
    assert lifetime == 100
    assert _active_investment_periods(lifetime, interval_between_years) > 0


def test_application_land_ceiling(model: Model) -> None:
    """Capacity limit is arable hectares × 20 t/ha/year ÷ 8760."""
    from types import SimpleNamespace

    model.config = SimpleNamespace(system=SimpleNamespace(set_nodes=["CH", "DE"]))
    application = BasaltApplication(model=model)
    parameters = BasaltErwParameters(model.settings, model.source_path)
    limit = application._set_capacity_limit()
    arable = parameters._arable.get_arable_land_ha(["CH", "DE"], year=2024)

    assert limit.unit == "tproduct/h"
    assert list(limit.df.index) == ["CH", "DE"]
    assert limit.df.loc["CH"] == pytest.approx(
        arable.loc["CH"] * 20.0 / Constants.HOURS_PER_YEAR
    )
    assert limit.df.loc["DE"] == pytest.approx(
        arable.loc["DE"] * 20.0 / Constants.HOURS_PER_YEAR
    )
    assert limit.df.loc["CH"] < limit.df.loc["DE"]
    # Forced smoke rate of 1 t/h stays below the CH ceiling.
    assert 1.0 < limit.df.loc["CH"]


def test_application_cites_sources(model: Model) -> None:
    application = BasaltApplication(model=model)
    expected = {
        "beerling_basalt_removal",
        "cobo_basalt_electricity",
        "cobo_weathering_efficiency",
        "netl_basalt_erw_costs",
        "dalgaard_application_diesel",
        "worldbank_arable_land",
        "dupla_basalt_accumulation",
        "ecb_dollar_to_euro",
        "ecb_inflation",
    }
    source = application._set_carbon_intensity_technology().sources[-1]
    assert isinstance(source, SourceInformation)
    names = {
        metadata.name
        for metadata in source.metadata.values()
        if isinstance(metadata, MetaData)
    }
    assert names == expected


@pytest.mark.parametrize("area", [-1.0, float("inf"), float("-inf")])
def test_erw_rejects_invalid_arable_area(model, area):
    from types import SimpleNamespace

    model.config = SimpleNamespace(system=SimpleNamespace(set_nodes=["CH"]))
    parameters = BasaltErwParameters(model.settings, model.source_path)
    parameters._arable.data.loc["CH", 2024] = area
    with pytest.raises(ValueError, match="finite nonnegative arable"):
        parameters.get_application_capacity_limit(BasaltApplication(model))


@pytest.mark.parametrize("missing", ["country", "year", "value"])
def test_erw_rejects_missing_arable_data(model, missing):
    from types import SimpleNamespace

    model.config = SimpleNamespace(system=SimpleNamespace(set_nodes=["CH"]))
    parameters = BasaltErwParameters(model.settings, model.source_path)
    data = parameters._arable.data
    if missing == "country":
        parameters._arable.data = data.drop(index="CH")
    elif missing == "year":
        parameters._arable.data = data.drop(columns=2024)
    else:
        data.loc["CH", 2024] = float("nan")
    with pytest.raises(ValueError, match="arable-land|Arable-land"):
        parameters.get_application_capacity_limit(BasaltApplication(model))
