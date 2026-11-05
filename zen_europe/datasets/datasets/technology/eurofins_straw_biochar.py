from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class EurofinsStrawBiochar(Dataset[pd.Series]):
    """Organic-carbon fraction of a measured straw biochar."""

    name = "eurofins_straw_biochar"
    ORGANIC_CARBON_FRACTION = 0.75

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Eurofins laboratory report for straw biochar",
            author=["Eurofins"],
            publication="Stiesdal SkyClean",
            publication_year=2022,
            url=(
                "https://stiesdalskyclean.com/wp-content/uploads/sites/3/"
                "2026/06/Straw-Eurofins-report.pdf"
            ),
            note=(
                "Report AR-22-FR-045377-01. Organic carbon is 75.3% of dry "
                "mass, rounded to 0.75 tC per t dry biochar. The measured "
                "straw biochar is a proxy for the modeled product and is not "
                "the same sample as the DEA pyrolysis sheet."
            ),
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        return pd.Series(dtype=float)

    def get_organic_carbon_fraction(self) -> float:
        """Dry-basis organic carbon, tC per t dry biochar."""
        return self.ORGANIC_CARBON_FRACTION
