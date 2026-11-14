"""IPCC 2019 medium-temperature biochar persistence proxy."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class IpccBiocharPermanence(Dataset[pd.Series]):
    """Carbon remaining after 100 years for assumed medium-temperature pyrolysis."""

    name = "ipcc_biochar_permanence"
    RETAINED_FRACTION_100Y = 0.80

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "2019 Refinement, Volume 4, Chapter 2, Appendix 4: Method for "
                "Estimating the Change in Mineral Soil Organic Carbon Stocks "
                "from Biochar Amendments: Basis for Future Methodological "
                "Development"
            ),
            author=["IPCC"],
            publication="2019 Refinement to the 2006 IPCC Guidelines",
            publication_year=2019,
            url=(
                "https://www.ipcc-nggip.iges.or.jp/public/2019rf/pdf/"
                "4_Volume4/19R_V4_Ch02_Ap4_Biochar.pdf"
            ),
            note=(
                "Table 4Ap.2 (p. Ap4.3): 100-year retained-carbon fraction of "
                "0.80 for medium-temperature pyrolysis (450–600°C) in mineral "
                "cropland and grassland soils. Medium-temperature operation is "
                "assumed for the DEA straw-pyrolysis proxy."
            ),
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        return pd.Series(dtype=float)

    def get_retained_fraction(self) -> float:
        """Fraction of organic carbon remaining after 100 years."""
        return self.RETAINED_FRACTION_100Y
