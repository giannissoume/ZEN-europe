"""Assumptions for the optional liming OAE pathway."""

from typing import ClassVar

from pydantic import Field
from zen_creator.utils.settings import SettingsCategory


class LimingOaeSettings(SettingsCategory):
    """Production, delivery and marine-service assumptions."""

    name: ClassVar[str] = "liming_oae"

    delivery_km: float = Field(default=100, ge=0, allow_inf_nan=False)
    eligible_area_fraction: float = Field(default=1, ge=0, le=1)
    production_max_load: float = Field(default=0.95, gt=0, le=1)
    limestone_euro_per_t: float = Field(default=20, ge=0, allow_inf_nan=False)
    water_euro_per_m3: float = Field(default=6, ge=0, allow_inf_nan=False)
    utility_price_year: int = 2025
    cargo_t: float = Field(default=40000, gt=0, allow_inf_nan=False)
    access_days: float = Field(default=1, ge=0, allow_inf_nan=False)
    loading_days: float = Field(default=1, ge=0, allow_inf_nan=False)
    slurry_kwh_per_t: float = Field(default=2, ge=0, allow_inf_nan=False)
    generator_efficiency: float = Field(default=0.4, gt=0, le=1)
