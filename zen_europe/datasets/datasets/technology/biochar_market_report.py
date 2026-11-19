from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator import Attribute, ConversionTechnology, SourceInformation
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.utils.constants import Constants
from zen_europe.utils.utils import (
    calculate_capacity_addition_from_cumulative,
    convert_country_names,
    format_capacity_existing,
)


class BiocharMarketReport(Dataset[pd.DataFrame]):
    """Biochar production capacity from the European Biochar Market Report."""

    name = "biochar_market_report"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("European Biochar Market Report 2025 2026"),
            author=["Biochar Europe"],
            publication="Biochar Europe",
            publication_year=2026,
            url="https://www.biochareurope.eu/resource/market-report-2025-2026",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.DataFrame:
        """
        Annual biochar production capacity by region, in tonnes/year.

        Values for 2019-2020 are from the 2023-2024 report. Values for
        2021-2026 are estimated from the 2025-2026 report's chart
        (printed p. 49, PDF p. 47).
        """
        biochar_capacity = {
            2019: {
                "Germany": 7000,
                "Austria and Switzerland": 2500,
                "Nordics": 2000,
                "other countries": 2500,
            },
            2020: {
                "Germany": 8500,
                "Austria and Switzerland": 2000,
                "Nordics": 5500,
                "other countries": 4500,
            },
            2021: {
                "Germany": 13000,
                "Austria and Switzerland": 4500,
                "Nordics": 9000,
                "other countries": 8500,
            },
            2022: {
                "Germany": 17000,
                "Austria and Switzerland": 9500,
                "Nordics": 13500,
                "other countries": 13000,
            },
            2023: {
                "Germany": 19500,
                "Austria and Switzerland": 12000,
                "Nordics": 21000,
                "other countries": 22500,
            },
            2024: {
                "Germany": 21500,
                "Austria and Switzerland": 12000,
                "Nordics": 25500,
                "other countries": 25000,
            },
            2025: {
                "Germany": 21500,
                "Austria and Switzerland": 14500,
                "Nordics": 27500,
                "other countries": 27500,
            },
            2026: {
                "Germany": 21500,
                "Austria and Switzerland": 20500,
                "Nordics": 30500,
                "other countries": 32500,
            },
        }
        # Split each regional total equally among the selected countries.
        countries_nordics = ["Denmark", "Finland", "Sweden"]
        countries_austria_switzerland = ["Austria", "Switzerland"]
        countries_other = ["France", "Spain", "United Kingdom"]

        data = pd.DataFrame(biochar_capacity)
        for country in countries_nordics:
            data.loc[country, :] = data.loc["Nordics"] / len(countries_nordics)
        for country in countries_austria_switzerland:
            data.loc[country, :] = data.loc["Austria and Switzerland"] / len(
                countries_austria_switzerland
            )
        for country in countries_other:
            data.loc[country, :] = data.loc["other countries"] / len(countries_other)
        data = data.drop(["Nordics", "Austria and Switzerland", "other countries"])

        data.index = pd.Index(
            convert_country_names(data.index.to_series()).values, name="node"
        )

        return data

    # -------- methods ------------------------
    def get_capacity_existing(self, element: ConversionTechnology) -> Attribute:
        """
        Convert annual biochar production capacity to GW of biochar output.

        Use production capacity rather than actual annual production.
        """
        attr = element.capacity_existing
        addition = calculate_capacity_addition_from_cumulative(self.data, element)
        data = addition * Constants.BIOCHAR_GWH_PER_TON / 8760  # GW
        capacity_existing = data
        capacity_existing = capacity_existing.stack()
        capacity_existing = format_capacity_existing(capacity_existing)
        return attr.set_data(
            default_value=0,
            df=capacity_existing,
            unit="GW",
            source=SourceInformation(
                description=(
                    "Existing pyrolysis capacity is based on regional chart estimates "
                    "from the Biochar Market Report, split equally among the selected "
                    "countries. Annual biochar capacity is converted to GW using "
                    "25 GJ/t and 8760 h/year. The report covers plants intended for "
                    "carbon removal; model output can supply soil application or fuel "
                    "substitution."
                ),
                metadata=self.metadata,
            ),
        )
