from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class WoolfBiocharPermanence(Dataset[pd.Series]):
    """Retained fraction of biochar carbon from Woolf et al. (2021)."""

    name = "woolf_biochar_permanence"
    RETAINED_FRACTION_100Y = 0.82
    UNUSED_RETAINED_FRACTION_1000Y = 0.25

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Greenhouse Gas Inventory Model for Biochar Additions to Soil",
            author=[
                "Woolf, D.",
                "Lehmann, J.",
                "Ogle, S.",
                "Kishimoto-Mo, A. W.",
                "McConkey, B.",
                "Baldock, J.",
            ],
            publication="Environmental Science & Technology",
            publication_year=2021,
            doi="10.1021/acs.est.1c02425",
            note=(
                "Table 3, high-temperature class (at least 600°C) at 15°C "
                "soil temperature: 100-year retained fraction 0.82 (standard "
                "error 0.028). The same cell at 1000 years is 0.25 (standard "
                "error 0.073) and is not used. The high-temperature class is "
                "an assumption for the DEA slow-pyrolysis sheet, which does "
                "not state a peak temperature. No H/Corg measurement is used."
            ),
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        return pd.Series(dtype=float)

    def get_retained_fraction(self) -> float:
        """Fraction of organic carbon remaining after 100 years."""
        return self.RETAINED_FRACTION_100Y
