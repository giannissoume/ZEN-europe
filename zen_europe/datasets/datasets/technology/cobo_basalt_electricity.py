"""Grinding electricity of the selected field basalt LCI column."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class CoboBasaltElectricity(Dataset[pd.Series]):
    """Electricity per tonne of field basalt from the Cobo et al. (2026) workbook."""

    name = "cobo_basalt_electricity"
    # Sheet "2. LCIs year 0", Basalt / field trials / Beerling 2024 / Base.
    ELECTRICITY_MWH_PER_TCO2 = 0.1947445179009531
    ROCK_T_PER_TCO2 = 69.9062230049315

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Delayed Climate Benefits and Toxicity Risks Could Hinder "
                "the Sustainable Deployment of Enhanced Weathering"
            ),
            author=["Cobo et al. (2026) workbook contributors"],
            publication="Environmental Science & Technology",
            doi="10.1021/acs.est.6c08993",
            url="https://zenodo.org/records/19073284",
            publication_year=2026,
            note=(
                "Workbook EW datasets_v17.03.26.xlsx. Sheet '2. LCIs year 0', "
                "Basalt, Experimental (field trials), "
                "Beerling et al. 2024, Base column. Electricity is "
                f"{self.ELECTRICITY_MWH_PER_TCO2} MWh per tCO2 and rock is "
                f"{self.ROCK_T_PER_TCO2} t per tCO2. The quotient is "
                "electricity per tonne of basalt for the selected p80 "
                "267 µm field case. It is independent of the fixed "
                "0.0525 tCO2/t application credit. NETL's finer 20 µm "
                "grinding electricity is not used."
            ),
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        return pd.Series(dtype=float)

    def get_electricity_mwh_per_t_basalt(self) -> float:
        """Grinding electricity, MWh per tonne of basalt."""
        return self.ELECTRICITY_MWH_PER_TCO2 / self.ROCK_T_PER_TCO2
