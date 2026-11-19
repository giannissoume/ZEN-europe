"""Fixed gross CO2 removal ratio of the Beerling et al. field programme."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class BeerlingBasaltRemoval(Dataset[pd.Series]):
    """Field-programme CDR ratio transferred as a fixed application credit."""

    name = "beerling_basalt_removal"
    # 10.5 tCO2/ha over four years of 50 t/ha/year = 200 t/ha total.
    REMOVAL_TCO2_PER_T_BASALT = 0.0525

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Enhanced weathering in the US Corn Belt delivers carbon "
                "removal with agronomic benefits"
            ),
            author=["Beerling, D. J.", "and co-authors"],
            publication="Proceedings of the National Academy of Sciences",
            publication_year=2024,
            doi="10.1073/pnas.2319436121",
            note=(
                "Abstract and Fig. 1D: cumulative field-programme CDR potential "
                "of 10.5 tCO2/ha for 200 t basalt/ha over four years. The "
                "ratio, 0.0525 tCO2/t, supplies the unadjusted field potential. "
                "It is inferred from Ca/Mg loss assuming bicarbonate formation, "
                "not measured completed downstream storage. The paper excludes "
                "downstream efficiency changes; a separate cross-source chemical "
                "efficiency proxy is applied in the parameter collection."
            ),
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        return pd.Series(dtype=float)

    def get_removal_tco2_per_t_basalt(self) -> float:
        """Gross CO2 removal, tonnes of CO2 per tonne of basalt applied."""
        return self.REMOVAL_TCO2_PER_T_BASALT
