"""Source data for the liming OAE pathway."""

from pathlib import Path

import pandas as pd
from zen_creator import Dataset, MetaData


class MitrakiLimeProduction(Dataset[pd.Series]):
    """Optimization of energy transition pathways in the lime industry."""

    name = "mitraki_lime_production"

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Optimization of energy transition pathways in the lime industry",
            author=["Mitraki et al."],
            publication="Journal of Cleaner Production",
            publication_year=2026,
            url="https://orbi.uliege.be/bitstream/2268/348969/1/Mitraki%20et%20al__manuscript%20lime.pdf",
            note=(
                "Source values transcribed into the accompanying CSV. "
                "NGOxy-CC PFR kiln: main Tables 1 and 4; supplement Tables S4, S7-S8"
                " and S10. Charges are annualized 2025 euros per tonne CaO; each"
                " annuity is reversed before model financing. The industrial inventory"
                " leaves 0.154 t/t CaO of unresolved material balance; no residual"
                " stream is modelled. Grid-connection upgrades and flue-gas"
                " pretreatment are excluded by the source (SI S4)."
            ),
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path is required for liming source data.")
        return (
            Path(self.source_path)
            / "03-technology/oae_liming"
            / "mitraki_lime_production.csv"
        )

    def _set_data(self) -> pd.Series:
        data = pd.read_csv(self.path, index_col="parameter")["value"]
        return pd.to_numeric(data, errors="raise")

    def get_value(self, parameter: str) -> float:
        """Return a source coefficient in the units recorded in the CSV."""
        return float(self.data.loc[parameter])
