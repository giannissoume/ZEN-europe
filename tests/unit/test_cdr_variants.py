"""Check the declared combinations of the added CDR pathways."""

import pytest
from zen_creator import Model
from zen_creator.utils.settings import ModelSet, Settings

from zen_europe.model_creator import DATA_PATH
from zen_europe.settings.structure import StructureSettings

VARIANTS = {
    "baseline": (False, False, False, False),
    "bcr": (True, False, False, False),
    "erw_only": (False, True, False, False),
    "oae_only": (False, False, True, False),
    "bcr_erw": (True, True, False, False),
    "bcr_oae": (True, False, True, False),
    "erw_oae": (False, True, True, False),
    "bcr_erw_oae": (True, True, True, False),
    "electrochemical_oae_only": (False, False, False, True),
    "bcr_erw_oae_electrochemical": (True, True, True, True),
}


def test_declared_cdr_variants_and_defaults():
    variants = ModelSet.load_from_yaml(DATA_PATH / "models.yaml")
    assert variants.names == list(VARIANTS)
    assert "basalt_erw" not in StructureSettings().set_sectors
    assert "liming_oae" not in StructureSettings().set_sectors
    assert "electrochemical_oae" not in StructureSettings().set_sectors


@pytest.mark.parametrize("name,enabled", VARIANTS.items())
def test_cdr_application_combination(name, enabled):
    variants = ModelSet.load_from_yaml(DATA_PATH / "models.yaml")
    settings = Settings.load_from_yaml(
        DATA_PATH / "zen_europe_config.yaml", patch=variants.settings_patch(name)
    )
    model = Model.from_config(DATA_PATH / "zen_europe_config.yaml", settings=settings)
    bcr, erw, oae, electrochemical = enabled
    for technology, active in (
        ("biochar_application", bcr),
        ("basalt_application", erw),
        ("lime_ocean_application", oae),
        ("basalt_grinding", erw),
        ("lime_production_ccs", oae),
        ("seawater_mineralization", electrochemical),
    ):
        assert (technology in model.elements) == active, (name, technology)
    # Controls retain the common biomass/fuel pathway and baseline carbon system.
    for element in (
        "pyrolysis",
        "biochar",
        "biochar_to_hard_coal",
        "DAC",
        "carbon_storage",
    ):
        assert element in model.elements, (name, element)
    for carrier, active in (
        ("basalt", erw),
        ("ground_basalt", erw),
        ("limestone", oae),
        ("hydrated_lime", oae),
        ("olivine", electrochemical),
    ):
        assert (carrier in model.carriers) == active, (name, carrier)
    assert sum(c.name == "diesel" for c in model.carriers.values()) == 1
