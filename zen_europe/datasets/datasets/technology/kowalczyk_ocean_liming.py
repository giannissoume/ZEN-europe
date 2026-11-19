"""Source data for the liming OAE pathway."""

from pathlib import Path

import pandas as pd
from zen_creator import Dataset, MetaData


class KowalczykOceanLiming(Dataset[pd.Series]):
    """Ocean liming calculations."""

    name = "kowalczyk_ocean_liming"

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Ocean liming calculations",
            author=["Kowalczyk et al."],
            publication="Environmental Research Letters",
            publication_year=2024,
            url="https://oceanrep.geomar.de/60524/3/erlad5192supp1.xlsx",
            note=(
                "Source values transcribed into the accompanying CSV. "
                "Distribution worksheet D25, D35-D36: discharge rate rounded to 30 t/h"
                " and ship fuel inventory. The 1.5 mol CO2/mol Ca(OH)2 midpoint is used"
                " as gross uptake; marine delays are omitted."
            ),
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path is required for liming source data.")
        return (
            Path(self.source_path)
            / "03-technology/oae_liming"
            / "kowalczyk_ocean_liming.csv"
        )

    def _set_data(self) -> pd.Series:
        data = pd.read_csv(self.path, index_col="parameter")["value"]
        return pd.to_numeric(data, errors="raise")

    def get_value(self, parameter: str) -> float:
        """Return a source coefficient in the units recorded in the CSV."""
        return float(self.data.loc[parameter])
