"""First-of-a-kind seawater mineralization estimates from Chen et al."""

from pathlib import Path

import pandas as pd
from zen_creator import Dataset, MetaData


class ChenSeawaterMineralization(Dataset[pd.Series]):
    """Published operating and cost package for a 100 ktCO₂/year plant."""

    name = "chen_seawater_mineralization"

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Seawater Electrolysis Enables Multipathway Climate Change Mitigation "
                "through Atmospheric Carbon Dioxide Removal, Renewable Hydrogen "
                "Production, and Cement and Concrete Decarbonization"
            ),
            author=["Chen et al."],
            publication="Journal of the American Chemical Society",
            publication_year=2026,
            doi="10.1021/jacs.6c13870",
            url="https://doi.org/10.1021/jacs.6c13870",
            note=(
                "Section 5 first-of-a-kind engineering estimates. Sections 3.1–3.2 "
                "describe carbonation arrangements, electrode operation and acid "
                "neutralization. The monetary year is unspecified."
            ),
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError(
                "source_path is required for seawater mineralization data."
            )
        return (
            Path(self.source_path)
            / "03-technology/electrochemical_oae"
            / "chen_seawater_mineralization.csv"
        )

    def _set_data(self) -> pd.Series:
        data = pd.read_csv(self.path, index_col="parameter")["value"]
        return pd.to_numeric(data, errors="raise")

    def get_value(self, parameter: str) -> float:
        """Return a source estimate in the units recorded in the CSV."""
        return float(self.data.loc[parameter])
