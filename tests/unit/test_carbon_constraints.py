"""Country selection in historical emissions used for carbon constraints."""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

import pandas as pd
import pytest
from zen_creator import EnergySystem

from zen_europe.datasets.dataset_collections.carbon_constraints import CarbonConstraints


@pytest.mark.parametrize("nodes", [["DE"], ["DE", "FR"], ["UK"], ["DE", "UK"]])
@pytest.mark.parametrize("kind", ["sector", "total"])
def test_historical_emissions_respect_selected_nodes(
    nodes: list[str], kind: str
) -> None:
    """UK emissions enter only when UK is selected, including UK-only models."""
    years = pd.Index([1990, 2024], name="year")
    country_emissions = {
        "DE": pd.Series([3.0, 2.0], index=years),
        "FR": pd.Series([1.0, 0.5], index=years),
        "UK": pd.Series([0.8, 0.4], index=years),
    }
    eea = Mock()
    uk = Mock()
    eea_nodes = [node for node in nodes if node != "UK"]
    if eea_nodes:
        eea_total = pd.DataFrame([country_emissions[node] for node in eea_nodes])
        eea.get_emissions_sectors.return_value = eea_total
        eea.get_emissions_total.return_value = eea_total.sum()
    uk.get_emissions_sectors.return_value = pd.DataFrame([country_emissions["UK"]])
    uk.get_emissions_total.return_value = country_emissions["UK"]
    constraints = object.__new__(CarbonConstraints)
    constraints._data = {"eea_ghg_inventory": eea, "desnz_ghg_inventory": uk}
    sectors = ["passenger_transport", "truck_transport"]
    energy_system = cast(
        EnergySystem,
        SimpleNamespace(
            config=SimpleNamespace(system=SimpleNamespace(set_nodes=nodes)),
            model=SimpleNamespace(sectors=dict.fromkeys(sectors)),
        ),
    )

    if kind == "sector":
        result = constraints.calculate_sector_emissions(energy_system)
        eea_method = eea.get_emissions_sectors
        uk_method = uk.get_emissions_sectors
    else:
        result = constraints.calculate_total_emissions(energy_system)
        eea_method = eea.get_emissions_total
        uk_method = uk.get_emissions_total

    expected = pd.DataFrame([country_emissions[node] for node in nodes]).sum()
    pd.testing.assert_series_equal(result, expected)
    if eea_nodes:
        arguments = (sectors, eea_nodes) if kind == "sector" else (eea_nodes,)
        eea_method.assert_called_once_with(*arguments)
    else:
        eea_method.assert_not_called()
    if "UK" in nodes:
        uk_method.assert_called_once_with(sectors)
    else:
        uk_method.assert_not_called()
