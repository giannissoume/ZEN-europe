"""EU cumulative biochar application ceiling used as a deployment proxy."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class EuBiocharApplicationLimit(Dataset[pd.Series]):
    """Published cumulative certification ceiling, not an annual soil limit."""

    name = "eu_biochar_application_limit"
    CUMULATIVE_LIMIT_T_PER_HA = 50.0

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Certification methodologies for permanent carbon removals "
                "activities, C(2026) 553 final"
            ),
            author=["European Commission"],
            publication="Commission delegated act of 3 February 2026",
            publication_year=2026,
            url=(
                "https://eur-lex.europa.eu/legal-content/EN/TXT/"
                "?uri=PI_COM:C(2026)553"
            ),
            note=(
                "Annex 1.1.2.2.1(a): cumulative certification ceiling of 50 "
                "t/ha, including historical applications. The model interprets "
                "this on the dry-mass basis of Qbiochar in Annex 2.2.3, "
                "equation 44."
            ),
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        return pd.Series(dtype=float)

    def get_cumulative_limit_t_per_ha(self) -> float:
        """Cumulative biochar application ceiling, tonnes per hectare."""
        return self.CUMULATIVE_LIMIT_T_PER_HA
