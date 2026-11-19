"""Configurable delivery and land-allowance assumptions for basalt_erw."""

from typing import ClassVar

from pydantic import Field
from zen_creator.utils.settings import SettingsCategory


class BasaltErwSettings(SettingsCategory):
    """Delivery and deployment assumptions; source values stay in datasets."""

    name: ClassVar[str] = "basalt_erw"

    delivery_km: float = Field(default=100, ge=0, allow_inf_nan=False)
    eligible_arable_fraction: float = Field(default=1, ge=0, le=1)
    # Deployment proxy motivated by Dupla et al.; not physical soil capacity.
    application_t_per_ha_year: float = Field(default=20, ge=0, allow_inf_nan=False)
