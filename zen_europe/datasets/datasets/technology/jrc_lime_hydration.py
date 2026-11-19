"""Source data for the liming OAE pathway."""

from pathlib import Path

import pandas as pd
from zen_creator import Dataset, MetaData


class JrcLimeHydration(Dataset[pd.Series]):
    """JRC hydration-water requirement for the lime industry."""

    name = "jrc_lime_hydration"

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Best Available Techniques Reference Document for the Production of"
                " Cement, Lime and Magnesium Oxide"
            ),
            author=["European Commission JRC"],
            publication="European Commission",
            publication_year=2013,
            url="https://bureau-industrial-transformation.jrc.ec.europa.eu/sites/default/files/2019-11/CLM_Published_def_0.pdf",
            note=(
                "Source values transcribed into the accompanying CSV. "
                "Section 2.2.6.4.1, printed p.198 (PDF p.226): water addition about"
                " twice stoichiometric. Excess evaporates; it does not increase dry"
                " product output."
            ),
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path is required for liming source data.")
        return (
            Path(self.source_path)
            / "03-technology/oae_liming"
            / "jrc_lime_hydration.csv"
        )

    def _set_data(self) -> pd.Series:
        data = pd.read_csv(self.path, index_col="parameter")["value"]
        return pd.to_numeric(data, errors="raise")

    def get_value(self, parameter: str) -> float:
        """Return a source coefficient in the units recorded in the CSV."""
        return float(self.data.loc[parameter])
