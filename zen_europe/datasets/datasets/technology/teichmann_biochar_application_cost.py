from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class TeichmannBiocharApplicationCost(Dataset[pd.Series]):
    """Non-fuel equipment and labour cost of biochar application."""

    name = "teichmann_biochar_application_cost"
    COST_EUR_PER_TON = 6.23
    COST_YEAR = 2012

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "An Economic Assessment of Soil Carbon Sequestration with "
                "Biochar in Germany"
            ),
            author=["Teichmann, I."],
            publication="DIW Berlin",
            publication_year=2015,
            url=(
                "https://www.econstor.eu/dspace/bitstream/10419/110324/1/"
                "825836247.pdf"
            ),
            note=(
                "Equipment-and-labour cost of 6.23 Euro per tonne in 2012, "
                "excluding fuel. The source does not distinguish fresh and "
                "dry biochar mass. The model applies the figure per dry "
                "tonne as a modeling assumption."
            ),
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        return pd.Series(dtype=float)

    def get_cost_eur_per_ton(self) -> float:
        """Non-fuel application cost, Euro per tonne in the source year."""
        return self.COST_EUR_PER_TON

    def get_cost_year(self) -> int:
        """Price year of the published cost."""
        return self.COST_YEAR
