"""Source data for the liming OAE pathway."""

from pathlib import Path

import pandas as pd
from zen_creator import Dataset, MetaData


class PacificLimeHydrator(Dataset[pd.Series]):
    """Central Lime Project Final Investment Decision."""

    name = "pacific_lime_hydrator"

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Central Lime Project Final Investment Decision",
            author=["Pacific Lime and Cement"],
            publication="ASX announcement",
            publication_year=2025,
            url="https://announcements.asx.com.au/asxpdf/20250804/pdf/06mh4wtgdvgfb7.pdf",
            note=(
                "Source values transcribed into the accompanying CSV. "
                "Printed slide 19 (PDF p.25): incremental co-located hydration package."
                " The 15 tph is assumed to mean dry hydrate output; transfer to Europe"
                " is an engineering proxy."
            ),
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path is required for liming source data.")
        return (
            Path(self.source_path)
            / "03-technology/oae_liming"
            / "pacific_lime_hydrator.csv"
        )

    def _set_data(self) -> pd.Series:
        data = pd.read_csv(self.path, index_col="parameter")["value"]
        return pd.to_numeric(data, errors="raise")

    def get_value(self, parameter: str) -> float:
        """Return a source coefficient in the units recorded in the CSV."""
        return float(self.data.loc[parameter])
