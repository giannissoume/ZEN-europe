"""NETL screening costs and diesel for an igneous-rock ERW plant."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class NetlBasaltErwCosts(Dataset[pd.Series]):
    """Capital, fixed costs, purchase price, application cost, and tractor diesel."""

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
    # Exhibit 4-1 land needed; Section 3.10.1: tractor fuel depends on area.
    DIESEL_US_GALLON_PER_YEAR = 2_059.0
    LAND_HA = 1_190.0
    US_GALLON_LITER = 3.785411784
    APPLICATION_RATE_T_PER_HA_YEAR = 50.0

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
                "Case 1 igneous rock. Exhibit 4-2 reports total plant cost "
                "26,001 in $/1,000, so 26,001,000 USD, with cost basis "
                "May 2023. Fixed O&M labour, tax and insurance total "
                "3,121,279 USD/year. Maintenance material 296,406 USD/year "
                "is treated once as fixed annual plant cost under this "
                "proxy and is not charged again per tonne. Rock purchase "
                "25 USD/t and material application 6 USD/t exclude fuel. "
                "Diesel 2,059 US gal/year is divided by the Exhibit 4-1 "
                "land need of 1,190 ha; Section 3.10.1 states tractor fuel "
                "depends on area covered. The 31-year lifetime is the "
                "NETL economic project life, used as a technical-life "
                "proxy. The engineering case is finer than the selected "
                "field basalt; these are transferred cost proxies."
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

    def get_diesel_liter_per_t(self) -> float:
        """Tractor diesel, litres per tonne at 50 t/ha/year.

        Area intensity is 2,059 US gal/year over 1,190 ha. Dividing by the
        modeled 50 t/ha/year rate converts that area proxy to a per-tonne
        figure. The NETL 172,740 t/year application quantity is not used.
        """
        liter_per_ha = (
            self.DIESEL_US_GALLON_PER_YEAR * self.US_GALLON_LITER / self.LAND_HA
        )
        return liter_per_ha / self.APPLICATION_RATE_T_PER_HA_YEAR
