"""Source data for the liming OAE pathway."""

from pathlib import Path

import pandas as pd
from zen_creator import Dataset, MetaData


class StreflerMarineAllowance(Dataset[pd.Series]):
    """Ocean liming can help achieve the Paris climate target."""

    name = "strefler_marine_allowance"

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Ocean liming can help achieve the Paris climate target",
            author=["Strefler et al."],
            publication="Environmental Research Letters",
            publication_year=2025,
            url="https://doi.org/10.1088/1748-9326/adf12c",
            note=(
                "Source values transcribed into the accompanying CSV. "
                "Section 3.3, printed pp.5-6: 20 g/m3 and 2 m receiving layer. Annual"
                " reuse and full eligible area are deployment assumptions, not"
                " ecological capacity."
            ),
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path is required for liming source data.")
        return (
            Path(self.source_path)
            / "03-technology/oae_liming"
            / "strefler_marine_allowance.csv"
        )

    def _set_data(self) -> pd.Series:
        data = pd.read_csv(self.path, index_col="parameter")["value"]
        return pd.to_numeric(data, errors="raise")

    def get_value(self, parameter: str) -> float:
        """Return a source coefficient in the units recorded in the CSV."""
        return float(self.data.loc[parameter])
