"""Trace-element risks from repeated basalt applications."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class DuplaBasaltAccumulation(Dataset[pd.Series]):
    """Supporting evidence for the assumed basalt application allowance."""

    name = "dupla_basalt_accumulation"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Potential accumulation of toxic trace elements in soils "
                "during enhanced rock weathering"
            ),
            author=["Dupla, X.", "Möller, B.", "Baveye, P. C.", "Grand, S."],
            publication="European Journal of Soil Science",
            publication_year=2023,
            doi="10.1111/ejss.13343",
            url="https://doi.org/10.1111/ejss.13343",
            note=(
                "Sections 3.1-3.2 (pp. 6-7) discuss trace-element accumulation "
                "under repeated basalt applications. Used to motivate a lower "
                "deployment allowance; the model's 20 t/ha/year is an "
                "assumption, not a threshold established by this study."
            ),
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        return pd.Series(dtype=float)
