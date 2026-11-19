"""CDR assumptions loaded through config.yaml and models.yaml, before generation."""

import pandas as pd
import pytest
import yaml
from pydantic import ValidationError
from zen_creator import Dataset, DatasetCollection, Model
from zen_creator.utils.settings import ModelSet, Settings

from zen_europe.elements.carriers.basalt import Basalt
from zen_europe.elements.conversion_technologies.basalt_application import (
    BasaltApplication,
)
from zen_europe.elements.conversion_technologies.basalt_grinding import BasaltGrinding
from zen_europe.elements.conversion_technologies.biochar_application import (
    BiocharApplication,
)
from zen_europe.model_creator import DATA_PATH, create_model

DEFAULTS = {
    "biochar_cdr": {
        "delivery_km": 100,
        "eligible_arable_fraction": 1,
        "deployment_period_years": 25,
    },
    "basalt_erw": {
        "delivery_km": 100,
        "eligible_arable_fraction": 1,
        "application_t_per_ha_year": 20,
    },
    "liming_oae": {
        "delivery_km": 100,
        "eligible_area_fraction": 1,
        "production_max_load": 0.95,
        "limestone_euro_per_t": 20,
        "water_euro_per_m3": 6,
        "utility_price_year": 2025,
        "cargo_t": 40000,
        "access_days": 1,
        "loading_days": 1,
        "slurry_kwh_per_t": 2,
        "generator_efficiency": 0.4,
    },
}


def config_file(tmp_path, overrides):
    path = tmp_path / "config.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "source_path": str(DATA_PATH / "raw_data"),
                "settings": {
                    "region": {"set_nodes": ["CH", "DE"]},
                    "structure": {"energy_system": "", "set_sectors": []},
                    **overrides,
                },
            }
        )
    )
    return path


def load_settings(tmp_path, overrides, location):
    config = config_file(tmp_path, overrides if location == "config" else {})
    if location == "config":
        return Settings.load_from_yaml(config)
    models = tmp_path / "models.yaml"
    models.write_text(yaml.safe_dump({"models": {"custom": {"settings": overrides}}}))
    patch = ModelSet.load_from_yaml(models).settings_patch("custom")
    return Settings.load_from_yaml(config, patch=patch)


def attributes(config, settings):
    # Match independent CLI runs: source/collection singletons are per process.
    Dataset._registries.clear()
    DatasetCollection._registries.clear()
    model = Model.from_config(config, settings=settings)
    values, notes = {}, {}
    for name, element in (
        ("bcr", BiocharApplication(model)),
        ("erw", BasaltApplication(model)),
        ("grinding", BasaltGrinding(model)),
    ):
        for attr in (
            "conversion_factor",
            "carbon_intensity_technology",
            "opex_specific_variable",
            "capex_specific_conversion",
            "opex_specific_fixed",
            "lifetime",
            "max_load",
        ) + (("capacity_limit",) if name != "grinding" else ()):
            value = getattr(element, attr)
            key = f"{name}.{attr}"
            if attr == "conversion_factor":
                for entry in value.default_value:
                    for carrier, coefficient in entry.items():
                        values[f"{key}.{carrier}"] = coefficient["default_value"]
            else:
                values[key] = (
                    value.df.copy() if value.df is not None else value.default_value
                )
            if value.sources:
                notes[key] = value.sources[-1]
    values["basalt.price_import"] = Basalt(model).price_import.default_value
    return values, notes


def test_omitted_cdr_settings_keep_defaults(tmp_path):
    settings = Settings.load_from_yaml(config_file(tmp_path, {}))
    for category, expected in DEFAULTS.items():
        assert getattr(settings, category).model_dump() == expected


@pytest.mark.parametrize("location", ["config", "models"])
@pytest.mark.parametrize(
    "category,field,value,affected,factor,note",
    [
        (
            "biochar_cdr",
            "delivery_km",
            200,
            "bcr.conversion_factor.truck_mileage",
            2,
            "200 km",
        ),
        (
            "basalt_erw",
            "delivery_km",
            200,
            "erw.conversion_factor.truck_mileage",
            2,
            "200 km",
        ),
        (
            "biochar_cdr",
            "delivery_km",
            0,
            "bcr.conversion_factor.truck_mileage",
            0,
            "0 km",
        ),
        (
            "basalt_erw",
            "delivery_km",
            0,
            "erw.conversion_factor.truck_mileage",
            0,
            "0 km",
        ),
        (
            "biochar_cdr",
            "eligible_arable_fraction",
            0.5,
            "bcr.capacity_limit",
            0.5,
            "fraction of 0.5",
        ),
        (
            "basalt_erw",
            "eligible_arable_fraction",
            0.5,
            "erw.capacity_limit",
            0.5,
            "fraction is 0.5",
        ),
        (
            "biochar_cdr",
            "eligible_arable_fraction",
            0,
            "bcr.capacity_limit",
            0,
            "fraction of 0",
        ),
        (
            "basalt_erw",
            "eligible_arable_fraction",
            0,
            "erw.capacity_limit",
            0,
            "fraction is 0",
        ),
        (
            "biochar_cdr",
            "deployment_period_years",
            50,
            "bcr.capacity_limit",
            0.5,
            "50-year",
        ),
        (
            "basalt_erw",
            "application_t_per_ha_year",
            10,
            "erw.capacity_limit",
            0.5,
            "10 t/ha/year",
        ),
        (
            "basalt_erw",
            "application_t_per_ha_year",
            0,
            "erw.capacity_limit",
            0,
            "0 t/ha/year",
        ),
    ],
)
def test_loaded_override_changes_only_intended_attribute(
    tmp_path, location, category, field, value, affected, factor, note
):
    config = config_file(tmp_path, {})
    before, before_notes = attributes(config, Settings.load_from_yaml(config))
    settings = load_settings(tmp_path, {category: {field: value}}, location)
    after, after_notes = attributes(config, settings)
    assert getattr(getattr(settings, category), field) == value
    assert after.keys() == before.keys()
    for key, old in before.items():
        expected = old * factor if key == affected else old
        if isinstance(expected, pd.Series):
            pd.testing.assert_series_equal(after[key], expected)
        else:
            assert after[key] == pytest.approx(expected), key
    source_key = (
        affected.rsplit(".", 1)[0] if "conversion_factor" in affected else affected
    )
    source = after_notes[source_key]
    assert note in source.description
    # The literature justification stays attached when assumptions change.
    assert source.metadata == before_notes[source_key].metadata
    if affected == "erw.capacity_limit":
        assert "Dupla" in source.description
        assert "not a demonstrated" in source.description
    if affected == "bcr.capacity_limit":
        assert "certification benchmark" in source.description
        assert "fixed" in source.description


@pytest.mark.parametrize("location", ["config", "models"])
@pytest.mark.parametrize(
    "category,field,value",
    [
        ("biochar_cdr", "delivery_km", -1),
        ("basalt_erw", "delivery_km", -1),
        ("biochar_cdr", "eligible_arable_fraction", -0.01),
        ("biochar_cdr", "eligible_arable_fraction", 1.01),
        ("basalt_erw", "eligible_arable_fraction", -0.01),
        ("basalt_erw", "eligible_arable_fraction", 1.01),
        ("biochar_cdr", "deployment_period_years", 0),
        ("biochar_cdr", "deployment_period_years", -1),
        ("basalt_erw", "application_t_per_ha_year", -1),
        ("biochar_cdr", "delivery_km", "invalid"),
        ("basalt_erw", "application_t_per_ha_year", "invalid"),
    ],
)
def test_invalid_assumptions_fail_during_loading(
    tmp_path, location, category, field, value
):
    with pytest.raises(ValidationError, match=field):
        load_settings(tmp_path, {category: {field: value}}, location)


def test_variant_overrides_base_config_and_preserves_other_fields(tmp_path):
    config = config_file(
        tmp_path,
        {
            "biochar_cdr": {"delivery_km": 150, "deployment_period_years": 40},
            "basalt_erw": {"delivery_km": 150, "application_t_per_ha_year": 12},
        },
    )
    models = tmp_path / "models.yaml"
    models.write_text(
        yaml.safe_dump(
            {
                "models": {
                    "parent": {"settings": {"biochar_cdr": {"delivery_km": 175}}},
                    "custom": {
                        "extends": "parent",
                        "settings": {
                            "biochar_cdr": {"delivery_km": 200},
                            "basalt_erw": {
                                "delivery_km": 250,
                                "eligible_arable_fraction": 0.5,
                            },
                        },
                    },
                }
            }
        )
    )
    # Exercise the production entry point as well as the Settings loader.
    model = create_model(config=config, models=models, model_name="custom", write=False)
    assert model.settings.biochar_cdr.model_dump() == {
        "delivery_km": 200,
        "deployment_period_years": 40,
        "eligible_arable_fraction": 1,
    }
    assert model.settings.basalt_erw.model_dump() == {
        "delivery_km": 250,
        "application_t_per_ha_year": 12,
        "eligible_arable_fraction": 0.5,
    }


@pytest.mark.parametrize("location", ["config", "models"])
@pytest.mark.parametrize(
    "category,field",
    [(category, field) for category, fields in DEFAULTS.items() for field in fields],
)
@pytest.mark.parametrize(
    "value", [float("inf"), float("-inf"), float("nan")], ids=["inf", "-inf", "nan"]
)
def test_nonfinite_assumptions_fail_during_loading(
    tmp_path, location, category, field, value
):
    with pytest.raises(ValidationError, match=field) as exc:
        load_settings(tmp_path, {category: {field: value}}, location)
    assert exc.value.errors()[0]["loc"][-1] == field


def test_custom_cdr_example_inherits_european_model(tmp_path):
    """Add the example only to a temporary copy of the established variants."""
    original = yaml.safe_load((DATA_PATH / "models.yaml").read_text())
    original["models"].update(yaml.safe_load("""
custom_cdr:
  extends: bcr_erw
  settings:
    biochar_cdr:
      delivery_km: 200
      eligible_arable_fraction: 0.5
      deployment_period_years: 50
    basalt_erw:
      delivery_km: 200
      eligible_arable_fraction: 0.5
      application_t_per_ha_year: 10
"""))
    models_path = tmp_path / "models.yaml"
    models_path.write_text(yaml.safe_dump(original))
    variants = ModelSet.load_from_yaml(models_path)
    config = DATA_PATH / "zen_europe_config.yaml"
    parent = Settings.load_from_yaml(config, patch=variants.settings_patch("bcr_erw"))
    child = Settings.load_from_yaml(config, patch=variants.settings_patch("custom_cdr"))

    assert child.structure.model_dump() == parent.structure.model_dump()
    assert child.biochar_cdr.model_dump() == {
        "delivery_km": 200,
        "eligible_arable_fraction": 0.5,
        "deployment_period_years": 50,
    }
    assert child.basalt_erw.model_dump() == {
        "delivery_km": 200,
        "eligible_arable_fraction": 0.5,
        "application_t_per_ha_year": 10,
    }
    parent_model = Model.from_config(config, settings=parent)
    child_model = Model.from_config(config, settings=child)
    assert child_model.elements.keys() == parent_model.elements.keys()
    assert child_model.carriers.keys() == parent_model.carriers.keys()
    assert {
        "pyrolysis",
        "biochar_to_hard_coal",
        "biochar_to_application",
        "biochar_application",
        "basalt_grinding",
        "basalt_application",
    } <= child_model.elements.keys()


@pytest.mark.parametrize("location", ["config", "models"])
def test_oae_finite_overrides_and_permitted_zeros(tmp_path, location):
    overrides = {
        "delivery_km": 0,
        "eligible_area_fraction": 0,
        "production_max_load": 0.9,
        "limestone_euro_per_t": 0,
        "water_euro_per_m3": 0,
        "utility_price_year": 2024,
        "cargo_t": 20000,
        "access_days": 0,
        "loading_days": 0,
        "slurry_kwh_per_t": 0,
        "generator_efficiency": 0.5,
    }
    settings = load_settings(tmp_path, {"liming_oae": overrides}, location)
    assert settings.liming_oae.model_dump() == overrides


@pytest.mark.parametrize("location", ["config", "models"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("delivery_km", -1),
        ("eligible_area_fraction", -0.1),
        ("eligible_area_fraction", 1.1),
        ("production_max_load", 0),
        ("production_max_load", 1.1),
        ("limestone_euro_per_t", -1),
        ("water_euro_per_m3", -1),
        ("cargo_t", 0),
        ("access_days", -1),
        ("loading_days", -1),
        ("slurry_kwh_per_t", -1),
        ("generator_efficiency", 0),
        ("generator_efficiency", 1.1),
    ],
)
def test_oae_existing_range_constraints_are_preserved(tmp_path, location, field, value):
    with pytest.raises(ValidationError, match=field):
        load_settings(tmp_path, {"liming_oae": {field: value}}, location)
