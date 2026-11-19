"""Source data for the liming OAE pathway."""

from pathlib import Path

import pandas as pd
from zen_creator import Dataset, MetaData


class IntermodalCharter(Dataset[pd.Series]):
    """Weekly Market Report Week 22, 6 June 2023."""

    name = "intermodal_charter"

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Weekly Market Report Week 22, 6 June 2023",
            author=["Intermodal"],
            publication="Intermodal",
            publication_year=2023,
            url="https://www.hellenicshippingnews.com/wp-content/uploads/2023/06/Intermodal-Report-Week-22-2023.pdf",
            note=(
                "Source values transcribed into the accompanying CSV. "
                "Page 3, Panamax 76K 3-year time-charter rate quoted 2 June 2023. A"
                " charter cost benchmark, not a ship lifetime or a complete OAE-service"
                " quote."
            ),
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path is required for liming source data.")
        return (
            Path(self.source_path)
            / "03-technology/oae_liming"
            / "intermodal_charter.csv"
        )

    def _set_data(self) -> pd.Series:
        data = pd.read_csv(self.path, index_col="parameter")["value"]
        return pd.to_numeric(data, errors="raise")

    def get_value(self, parameter: str) -> float:
        """Return a source coefficient in the units recorded in the CSV."""
        return float(self.data.loc[parameter])
