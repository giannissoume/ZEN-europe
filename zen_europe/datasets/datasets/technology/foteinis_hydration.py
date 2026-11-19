"""Source data for the liming OAE pathway."""

from pathlib import Path

import pandas as pd
from zen_creator import Dataset, MetaData


class FoteinisHydration(Dataset[pd.Series]):
    """Life cycle assessment of ocean liming."""

    name = "foteinis_hydration"

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Life cycle assessment of ocean liming",
            author=["Foteinis et al."],
            publication="Journal of Cleaner Production",
            publication_year=2022,
            url="https://doi.org/10.1016/j.jclepro.2022.133309",
            note=(
                "Source values transcribed into the accompanying CSV. "
                "Section 2.3, PDF p.7: 5.8 kWh per tonne hydrated lime. This is added"
                " to the selected quicklime-production inventory."
            ),
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path is required for liming source data.")
        return (
            Path(self.source_path)
            / "03-technology/oae_liming"
            / "foteinis_hydration.csv"
        )

    def _set_data(self) -> pd.Series:
        data = pd.read_csv(self.path, index_col="parameter")["value"]
        return pd.to_numeric(data, errors="raise")

    def get_value(self, parameter: str) -> float:
        """Return a source coefficient in the units recorded in the CSV."""
        return float(self.data.loc[parameter])
