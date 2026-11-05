from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class DalgaardApplicationDiesel(Dataset[pd.Series]):
    """Diesel use transferred from manure spreading to biochar application."""

    name = "dalgaard_application_diesel"
    DIESEL_LITER_PER_TON = 0.6

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "A model for fossil energy use in Danish agriculture used to "
                "compare organic and conventional farming"
            ),
            author=["Dalgaard, T.", "Halberg, N.", "Porter, J. R."],
            publication="Agriculture, Ecosystems & Environment",
            publication_year=2001,
            doi="10.1016/S0167-8809(00)00297-8",
            url="https://orgprints.org/id/file/59472",
            note=(
                "0.6 L diesel per tonne is the manure loading-and-spreading "
                "estimate. It is transferred to dry biochar as an "
                "agricultural-operation proxy and is not a measurement of "
                "biochar application."
            ),
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        return pd.Series(dtype=float)

    def get_diesel_liter_per_ton(self) -> float:
        """Diesel use, litres per tonne of dry biochar."""
        return self.DIESEL_LITER_PER_TON
