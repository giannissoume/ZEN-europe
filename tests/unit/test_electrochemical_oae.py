"""Check engineering normalization, accounting and activation of the new plant."""

from math import inf

import pytest
from pydantic import ValidationError
from zen_creator import Model
from zen_creator.utils.settings import ModelSet, Settings

from zen_europe.datasets.dataset_collections.electrochemical_oae_parameters import (
    ElectrochemicalOaeParameters,
)
from zen_europe.elements.carriers.olivine import Olivine
from zen_europe.elements.conversion_technologies.seawater_mineralization import (
    SeawaterMineralization,
)
from zen_europe.elements.sectors.electrochemical_oae import ElectrochemicalOaeSector
from zen_europe.model_creator import DATA_PATH
from zen_europe.settings.electrochemical_oae import ElectrochemicalOaeSettings
from zen_europe.utils.constants import Constants


def factors(plant):
    return {
        name: (attr["default_value"], attr["unit"])
        for entry in plant.conversion_factor.default_value
        for name, attr in entry.items()
    }


def variant(name, **settings_patch):
    config = DATA_PATH / "zen_europe_config.yaml"
    models = ModelSet.load_from_yaml(DATA_PATH / "models.yaml")
    settings = Settings.load_from_yaml(
        config, patch=models.settings_patch(name) | settings_patch
    )
    return Model.from_config(config, settings=settings)


def test_operating_package_and_carrier_boundary(model):
    plant = SeawaterMineralization(model)
    rock = Olivine(model)
    cf = factors(plant)
    assert cf.keys() == {"electricity", "truck_mileage", "hydrogen"}
    assert cf["electricity"][0] == pytest.approx(250000 / 150000 / 1000)
    assert cf["electricity"][1] == "GWh/tproduct"
    assert cf["truck_mileage"] == (100, "tkm/tproduct")
    assert cf["hydrogen"][0] * 1e6 / Constants.HYDROGEN_KWH_PER_KG == pytest.approx(
        2800000 / 150000
    )
    assert cf["hydrogen"][1] == "GWh/tproduct"
    assert plant.carbon_intensity_technology.default_value == pytest.approx(
        -100000 / 150000
    )
    assert plant.carbon_intensity_technology.unit == "ton/tproduct"
    assert plant.power_unit == rock.power_unit == "tproduct/h"
    assert plant.reference_carrier.default_value == ["olivine"]
    assert plant.input_carrier.default_value == [
        "olivine",
        "electricity",
        "truck_mileage",
    ]
    assert plant.output_carrier.default_value == ["hydrogen"]
    assert plant.max_load.default_value == 0.9
    assert plant.lifetime.default_value == 20
    assert plant.capacity_existing.default_value == 0
    assert plant.capacity_investment_existing.default_value == 0
    assert plant.construction_time.default_value == 0
    assert plant.max_diffusion_rate.default_value == inf
    assert plant.opex_specific_variable.default_value == 0
    assert rock.availability_import.default_value == inf
    assert rock.availability_import_yearly.default_value == inf
    assert rock.availability_export.default_value == 0
    assert rock.availability_export_yearly.default_value == 0
    assert rock.demand.default_value == 0
    assert rock.carbon_intensity_carrier_import.default_value == 0


def test_costs_and_price_years(model):
    p = ElectrochemicalOaeParameters(model.source_path)
    annual_rock = 150000
    nameplate = annual_rock / (8760 * 0.90)
    assert p.get_nameplate_tph() == pytest.approx(nameplate)
    exchange = p.data["exchange"].data["euro2dollar"]
    inflation = p.data["inflation"].data["inflation_rate"]

    for usd_year, euro_year, factor in (
        (2025, 2025, 1 / exchange.loc[2025]),
        (2025, 2024, 1 / (exchange.loc[2025] * inflation.loc[2024])),
        (2024, 2025, inflation.loc[2024] / exchange.loc[2024]),
    ):
        model.settings.electrochemical_oae.assumed_cost_year = usd_year
        model.settings.time.price_year = euro_year
        plant = SeawaterMineralization(model)
        rock = Olivine(model)
        capex = plant.capex_specific_conversion
        fixed = plant.opex_specific_fixed
        assert capex.default_value == pytest.approx(8672400 * factor)
        assert capex.default_value * nameplate == pytest.approx(165000000 * factor)
        assert fixed.default_value == pytest.approx(260172 * factor)
        assert fixed.default_value * nameplate == pytest.approx(4950000 * factor)
        assert capex.unit == fixed.unit == "Euro/(tproduct/h)"
        assert rock.price_import.default_value == pytest.approx(25 * factor)
        assert rock.price_import.unit == "Euro/tproduct"
        assert capex.df is None and capex.yearly_variations_df is None
        assert fixed.df is None and fixed.yearly_variations_df is None
        assert rock.price_import.yearly_variations_df is None


def test_configured_assumptions_are_local_to_each_model():
    base = variant("electrochemical_oae_only")
    loss = variant(
        "electrochemical_oae_only",
        electrochemical_oae={
            "discharge_loss_fraction": 1,
            "first_available_year": 2032,
            "plant_lifetime_years": 23,
        },
    )
    zero_delivery = variant(
        "electrochemical_oae_only", electrochemical_oae={"delivery_km": 0}
    )
    t = base.elements["seawater_mineralization"]
    t_loss = loss.elements[t.name]
    t_zero_delivery = zero_delivery.elements[t.name]
    assert t_loss.carbon_intensity_technology.default_value == 0
    assert factors(t_loss) == factors(t)
    assert t_loss.lifetime.default_value == 23
    assert t_loss.capacity_limit.df.loc[("DE", 2030)] == 0
    assert t_loss.capacity_limit.df.loc[("DE", 2032)] == inf
    assert factors(t_zero_delivery) == factors(t) | {
        "truck_mileage": (0, "tkm/tproduct")
    }
    assert (
        t_zero_delivery.carbon_intensity_technology.default_value
        == t.carbon_intensity_technology.default_value
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("first_available_year", 0),
        ("plant_lifetime_years", 0),
        ("assumed_cost_year", 0),
        ("delivery_km", -1),
        ("delivery_km", inf),
        ("delivery_km", -inf),
        ("delivery_km", float("nan")),
        ("discharge_loss_fraction", -0.1),
        ("discharge_loss_fraction", 1.1),
        ("discharge_loss_fraction", inf),
        ("discharge_loss_fraction", -inf),
        ("discharge_loss_fraction", float("nan")),
    ],
)
def test_invalid_settings(field, value):
    with pytest.raises(ValidationError, match=field):
        ElectrochemicalOaeSettings(**{field: value})


def test_28_node_capacity_and_existing_hydrogen_references():
    assert ElectrochemicalOaeSettings().model_dump() == {
        "delivery_km": 100,
        "first_available_year": 2030,
        "plant_lifetime_years": 20,
        "assumed_cost_year": 2025,
        "discharge_loss_fraction": 0,
    }
    assert set(ElectrochemicalOaeSector.required_sectors) == {
        "electricity",
        "truck_transport",
        "hydrogen",
    }
    base = variant("baseline")
    enabled = variant("electrochemical_oae_only")
    plant = enabled.elements["seawater_mineralization"]
    limits = plant.capacity_limit.df.unstack("year")
    landlocked = ["AT", "CH", "CZ", "HU", "LU", "SK"]
    assert len(limits) == 28
    assert (limits.loc[landlocked] == 0).all().all()
    assert (limits.loc[:, :2029] == 0).all().all()
    assert (limits.drop(landlocked).loc[:, 2030:] == inf).all().all()
    assert set(enabled.elements) - set(base.elements) == {"olivine", plant.name}
    assert base.elements["electrolysis"].reference_carrier.default_value == ["hydrogen"]
    assert enabled.elements["electrolysis"].reference_carrier.default_value == [
        "hydrogen"
    ]
    assert plant.reference_carrier.default_value == ["olivine"]
