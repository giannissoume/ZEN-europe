"""World Bank arable land area by country."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from zen_creator import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.settings.cache import get_active_cache_settings
from zen_europe.utils.utils import convert_ISO3_to_ISO2

_CACHE_DIRECTORY = ("01-energy_system", "worldbank_arable_land")


class WorldBankArableLand(Dataset[pd.DataFrame]):
    """Arable land in hectares for the modeled NUTS0 countries."""

    name = "worldbank_arable_land"
    URL = (
        "https://api.worldbank.org/v2/country/all/indicator/AG.LND.ARBL.HA"
        "?format=json&per_page=32767"
    )
    CACHE_FILE = "worldbank_arable_land.csv"
    YEAR = 2023
    TIMEOUT = 60

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Arable land (hectares)",
            author=["World Bank"],
            publication="World Development Indicators",
            publication_year=datetime.now().year,
            url="https://data.worldbank.org/indicator/AG.LND.ARBL.HA",
            note=(
                "Indicator AG.LND.ARBL.HA, based on FAO data. The "
                f"{self.YEAR} value is used. Country codes are mapped with "
                "GRC→EL and GBR→UK. All reported arable area is treated as "
                "eligible for basalt application: a permissive proxy, not a "
                "mapped suitability estimate."
            ),
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            return None
        path = self.source_path.joinpath(*_CACHE_DIRECTORY)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _set_data(self) -> pd.DataFrame:
        """Arable land in hectares, indexed by node, with years as columns."""
        cache_path = self._cache_path()
        overwrite = get_active_cache_settings().overwrite_worldbank_arable_land
        if cache_path is not None and cache_path.exists() and not overwrite:
            data = pd.read_csv(cache_path, index_col="node")
            data.columns = data.columns.astype(int)
            data.columns.name = "year"
            return data

        data = self._download()
        if cache_path is not None:
            data.to_csv(cache_path)
        return data

    def _cache_path(self) -> Path | None:
        return None if self.source_path is None else self.path / self.CACHE_FILE

    def _download(self) -> pd.DataFrame:
        response = requests.get(self.URL, timeout=self.TIMEOUT)
        response.raise_for_status()
        header, observations = response.json()
        if int(header["pages"]) != 1:
            raise ValueError(
                f"The World Bank API returned {header['pages']} pages, but only "
                "the first one is read. Raise per_page in the request URL."
            )

        df = pd.DataFrame(observations)
        df["node"] = convert_ISO3_to_ISO2(df["countryiso3code"])
        df["year"] = df["date"].astype(int)
        df = df.dropna(subset=["node", "value"])
        data = df.pivot(index="node", columns="year", values="value").astype(float)
        return data.sort_index(axis=1)

    def get_arable_land_ha(
        self, nodes: list[str], year: int | None = None
    ) -> pd.Series:
        """Arable land in hectares for the given NUTS0 nodes."""
        year = self.YEAR if year is None else year
        missing = [node for node in nodes if node not in self.data.index]
        if missing:
            raise ValueError(
                f"No arable-land data for the nodes {missing}. "
                f"Available nodes: {list(self.data.index)}"
            )
        if year not in self.data.columns:
            raise ValueError(
                f"No arable-land data for year {year}. "
                f"Available years: {list(self.data.columns)}"
            )
        values = self.data.loc[nodes, year]
        if values.isna().any():
            empty = values[values.isna()].index.tolist()
            raise ValueError(
                f"Arable-land data for year {year} is missing for {empty}."
            )
        values.name = "arable_land_ha"
        return values
