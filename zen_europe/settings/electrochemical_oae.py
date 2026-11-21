"""Assumptions for the optional in-plant seawater mineralization pathway."""

from typing import ClassVar

from pydantic import Field
from zen_creator.utils.settings import SettingsCategory


class ElectrochemicalOaeSettings(SettingsCategory):
    """Rock delivery, plant deployment, monetary basis and discharge accounting."""

    name: ClassVar[str] = "electrochemical_oae"

    delivery_km: float = Field(default=100, ge=0, allow_inf_nan=False)
    first_available_year: int = Field(default=2030, ge=1)
    plant_lifetime_years: int = Field(default=20, gt=0)
    assumed_cost_year: int = Field(default=2025, ge=1)
    discharge_loss_fraction: float = Field(default=0, ge=0, le=1, allow_inf_nan=False)
