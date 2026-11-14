"""NETL screening costs for an igneous-rock ERW plant."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class NetlBasaltErwCosts(Dataset[pd.Series]):
    """Capital, fixed costs, basalt purchase price, and application cost."""

    name = "netl_basalt_erw_costs"
    MONEY_YEAR = 2023
    NAMEPLATE_T_PER_YEAR = 250_000.0
    TOTAL_PLANT_COST_USD = 26_001_000.0
    FIXED_LABOR_TAX_INSURANCE_USD_PER_YEAR = 3_121_279.0
    MAINTENANCE_MATERIAL_USD_PER_YEAR = 296_406.0
    ROCK_PRICE_USD_PER_T = 25.0
    APPLICATION_COST_USD_PER_T = 6.0
    LIFETIME_YEARS = 31.0
    MAX_LOAD = 0.85

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Enhanced Weathering: Techno-Economic and Life Cycle "
                "Screening Analysis"
            ),
            author=["National Energy Technology Laboratory"],
            publication="U.S. Department of Energy",
            publication_year=2025,
            url="https://www.osti.gov/servlets/purl/2531164",
            doi="10.2172/2531164",
            note=(
                "Case 1 igneous rock, May 2023 USD. Plant cost and annual O&M "
                "are from Exhibits 4-2 and 4-5; purchase and application costs "
                "from Sections 3.3 and 3.6. Maintenance material is treated as "
                "fixed O&M. The finer-grinding plant and 31-year economic life "
                "are engineering proxies for the selected basalt case."
            ),
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        return pd.Series(dtype=float)

    def get_money_year(self) -> int:
        """Dollar year of the published screening costs."""
        return self.MONEY_YEAR

    def get_nameplate_t_per_year(self) -> float:
        """Assumed nameplate rock throughput, tonnes per year."""
        return self.NAMEPLATE_T_PER_YEAR

    def get_installed_capacity_t_per_h(self) -> float:
        """Installed capacity as nameplate tonnes per hour."""
        return self.NAMEPLATE_T_PER_YEAR / 8760.0

    def get_total_plant_cost_usd(self) -> float:
        """Total plant cost investment boundary, USD."""
        return self.TOTAL_PLANT_COST_USD

    def get_fixed_opex_usd_per_year(self) -> float:
        """Annual fixed plant cost including maintenance material, USD/year."""
        return (
            self.FIXED_LABOR_TAX_INSURANCE_USD_PER_YEAR
            + self.MAINTENANCE_MATERIAL_USD_PER_YEAR
        )

    def get_rock_price_usd_per_t(self) -> float:
        """Basalt purchase price, USD per tonne."""
        return self.ROCK_PRICE_USD_PER_T

    def get_application_cost_usd_per_t(self) -> float:
        """Non-fuel material-application cost, USD per tonne."""
        return self.APPLICATION_COST_USD_PER_T

    def get_lifetime_years(self) -> float:
        """Economic project life used as a technical-life proxy."""
        return self.LIFETIME_YEARS

    def get_max_load(self) -> float:
        """Maximum load factor of the grinding plant."""
        return self.MAX_LOAD
