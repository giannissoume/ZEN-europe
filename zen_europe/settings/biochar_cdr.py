"""Configurable delivery and land-allowance assumptions for biochar_cdr."""

from typing import ClassVar

from pydantic import Field
from zen_creator.utils.settings import SettingsCategory


class BiocharCdrSettings(SettingsCategory):
    """Delivery and deployment assumptions; source values stay in datasets."""

    name: ClassVar[str] = "biochar_cdr"

    delivery_km: float = Field(default=100, ge=0, allow_inf_nan=False)
    eligible_arable_fraction: float = Field(default=1, ge=0, le=1)
    # Fixed annualization of the certification benchmark, not the model horizon.
    deployment_period_years: float = Field(default=25, gt=0, allow_inf_nan=False)
