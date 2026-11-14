"""CDR efficiency for enhanced weathering from Cobo et al. (2026)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class CoboWeatheringEfficiency(Dataset[pd.Series]):
    """Chemical CDR efficiency used as a downstream accounting proxy."""

    name = "cobo_weathering_efficiency"
    CDR_EFFICIENCY = 0.775

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Delayed Climate Benefits and Toxicity Risks Could Hinder "
                "the Sustainable Deployment of Enhanced Weathering"
            ),
            author=["Cobo et al. (2026)"],
            publication="Environmental Science & Technology",
            publication_year=2026,
            doi="10.1021/acs.est.6c08993",
            note=(
                "Supplement Section 3.1 (p. 10): CDR efficiency w = 0.775 "
                "accounts for CO2 release during bicarbonate-carbonate "
                "adjustment. Transferred to the Beerling field potential "
                "as a fixed proxy; it does not represent removal timing "
                "or a time-specific retention fraction."
            ),
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        return pd.Series(dtype=float)

    def get_cdr_efficiency(self) -> float:
        """Fraction of stoichiometric uptake credited after adjustment."""
        return self.CDR_EFFICIENCY
