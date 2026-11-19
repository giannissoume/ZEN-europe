"""Source data for the liming OAE pathway."""

from pathlib import Path

import pandas as pd
from zen_creator import Dataset, MetaData


class DesnzIndustryOpex(Dataset[pd.Series]):
    """Refresh of industry technology modelling assumptions."""

    name = "desnz_industry_opex"

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Refresh of industry technology modelling assumptions",
            author=["Department for Energy Security and Net Zero"],
            publication="UK Government",
            publication_year=2026,
            url="https://assets.publishing.service.gov.uk/media/6a3bf9c530b491f55b3c4925/refresh-industry-technology-modelling-assumptions.pdf",
            note=(
                "Source values transcribed into the accompanying CSV. "
                "PDF p.23: fixed OPEX convention of 2.5% of CAPEX/year where detailed"
                " data are unavailable; applied to the complete lime-production"
                " package."
            ),
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path is required for liming source data.")
        return (
            Path(self.source_path)
            / "03-technology/oae_liming"
            / "desnz_industry_opex.csv"
        )

    def _set_data(self) -> pd.Series:
        data = pd.read_csv(self.path, index_col="parameter")["value"]
        return pd.to_numeric(data, errors="raise")

    def get_value(self, parameter: str) -> float:
        """Return a source coefficient in the units recorded in the CSV."""
        return float(self.data.loc[parameter])
