"""Normalize basalt ERW literature values into model attributes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pandas as pd
from zen_creator import Attribute, ConversionTechnology, DatasetCollection
from zen_creator.datasets.datasets.metadata import SourceInformation
from zen_creator.utils.settings import Settings

from zen_europe.datasets.datasets.energy_system.worldbank_arable_land import (
    WorldBankArableLand,
)
from zen_europe.datasets.datasets.financial.ECB import ECBDollar2Euro, ECBInflation
from zen_europe.datasets.datasets.technology.beerling_basalt_removal import (
    BeerlingBasaltRemoval,
)
from zen_europe.datasets.datasets.technology.cobo_basalt_electricity import (
    CoboBasaltElectricity,
)
from zen_europe.datasets.datasets.technology.cobo_weathering_efficiency import (
    CoboWeatheringEfficiency,
)
from zen_europe.datasets.datasets.technology.dalgaard_application_diesel import (
    DalgaardApplicationDiesel,
)
from zen_europe.datasets.datasets.technology.dupla_basalt_accumulation import (
    DuplaBasaltAccumulation,
)
from zen_europe.datasets.datasets.technology.netl_basalt_erw_costs import (
    NetlBasaltErwCosts,
)
from zen_europe.utils.constants import Constants


class BasaltErwParameters(DatasetCollection):
    """Convert basalt ERW source values to the model's mass-based units."""

    name = "basalt_erw_parameters"
    DELIVERY_TKM_PER_T = 100.0
    APPLICATION_RATE_T_PER_HA_YEAR = 20.0

    def __init__(self, settings: Settings, source_path: Path | str):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _get_data(self) -> dict[str, Any]:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")
        return {
            "beerling_basalt_removal": BeerlingBasaltRemoval(self.source_path),
            "cobo_basalt_electricity": CoboBasaltElectricity(self.source_path),
            "cobo_weathering_efficiency": CoboWeatheringEfficiency(self.source_path),
            "netl_basalt_erw_costs": NetlBasaltErwCosts(self.source_path),
            "dalgaard_application_diesel": DalgaardApplicationDiesel(self.source_path),
            "worldbank_arable_land": WorldBankArableLand(self.source_path),
            "dupla_basalt_accumulation": DuplaBasaltAccumulation(self.source_path),
            "ecb_dollar_to_euro": ECBDollar2Euro(self.source_path),
            "ecb_inflation": ECBInflation(self.source_path),
        }

    @property
    def _beerling(self) -> BeerlingBasaltRemoval:
        return cast(BeerlingBasaltRemoval, self.data["beerling_basalt_removal"])

    @property
    def _electricity(self) -> CoboBasaltElectricity:
        return cast(CoboBasaltElectricity, self.data["cobo_basalt_electricity"])

    @property
    def _efficiency(self) -> CoboWeatheringEfficiency:
        return cast(CoboWeatheringEfficiency, self.data["cobo_weathering_efficiency"])

    @property
    def _netl(self) -> NetlBasaltErwCosts:
        return cast(NetlBasaltErwCosts, self.data["netl_basalt_erw_costs"])

    @property
    def _dalgaard(self) -> DalgaardApplicationDiesel:
        return cast(DalgaardApplicationDiesel, self.data["dalgaard_application_diesel"])

    @property
    def _arable(self) -> WorldBankArableLand:
        return cast(WorldBankArableLand, self.data["worldbank_arable_land"])

    @property
    def _dollar2euro(self) -> ECBDollar2Euro:
        return cast(ECBDollar2Euro, self.data["ecb_dollar_to_euro"])

    @property
    def _inflation(self) -> ECBInflation:
        return cast(ECBInflation, self.data["ecb_inflation"])

    def _usd_to_price_year_euro(self) -> float:
        money_year = self._netl.get_money_year()
        return self._dollar2euro.get_dollar2euro(money_year) * (
            self._inflation.get_inflation_rate(
                money_year, self.settings.time.price_year
            )
        )

    def electricity_gwh_per_tproduct(self) -> float:
        """Grinding electricity, GWh per tonne of ground basalt."""
        return self._electricity.get_electricity_mwh_per_t_basalt() / 1000.0

    def removal_tco2_per_t_basalt(self) -> float:
        """Efficiency-adjusted removal, excluding operational emissions."""
        return (
            self._beerling.get_removal_tco2_per_t_basalt()
            * self._efficiency.get_cdr_efficiency()
        )

    def diesel_gwh_per_tproduct(self) -> float:
        """Application diesel, GWh per tonne of ground basalt."""
        return (
            self._dalgaard.get_diesel_liter_per_ton()
            * Constants.DIESEL_KWH_PER_LITER
            / 1_000_000.0
        )

    def get_grinding_conversion_factor(
        self, element: ConversionTechnology
    ) -> Attribute:
        """Basalt and electricity inputs of grinding."""
        return element.conversion_factor.set_data(
            default_value=[
                {
                    "basalt": {
                        "default_value": 1.0,
                        "unit": "tproduct/tproduct",
                    }
                },
                {
                    "electricity": {
                        "default_value": self.electricity_gwh_per_tproduct(),
                        "unit": "GWh/tproduct",
                    }
                },
            ],
            source=SourceInformation(
                description=(
                    "Crushing and grinding electricity is derived from the Cobo et "
                    "al. (2026) field-basalt inventory, expressed per tonne of "
                    "rock. One tonne of purchased basalt yields one tonne of ground "
                    "basalt."
                ),
                metadata=self.metadata,
            ),
        )

    def get_application_conversion_factor(
        self, element: ConversionTechnology
    ) -> Attribute:
        """Freight and diesel inputs of application."""
        return element.conversion_factor.set_data(
            default_value=[
                {
                    "truck_mileage": {
                        "default_value": self.DELIVERY_TKM_PER_T,
                        "unit": "tkm/tproduct",
                    }
                },
                {
                    "diesel": {
                        "default_value": self.diesel_gwh_per_tproduct(),
                        "unit": "GWh/tproduct",
                    }
                },
            ],
            source=SourceInformation(
                description=(
                    "Delivery is assumed to be 100 km and is supplied by the "
                    "existing freight sector. Loading and spreading use the "
                    "Dalgaard et al. (2001), Table 2 manure-operation proxy of 0.6 "
                    "L diesel per tonne, converted at 10 kWh/L."
                ),
                metadata=self.metadata,
            ),
        )

    def get_carbon_intensity_technology(
        self, element: ConversionTechnology
    ) -> Attribute:
        """Fixed gross negative emissions of soil-applied basalt."""
        return element.carbon_intensity_technology.set_data(
            default_value=-self.removal_tco2_per_t_basalt(),
            unit="ton/tproduct",
            source=SourceInformation(
                description=(
                    "Beerling et al. (2024) field potential of 10.5/200 tCO2/t "
                    "is multiplied by the Cobo et al. (2026) efficiency of "
                    "0.775, giving 0.0406875 tCO2/t. This combined proxy is "
                    "credited immediately; subsequent uptake is not tracked. "
                    "Operational emissions are accounted separately through "
                    "the electricity, diesel and freight inputs."
                ),
                metadata=self.metadata,
            ),
        )

    def get_grinding_capex(self, element: ConversionTechnology) -> Attribute:
        """Specific capital cost of grinding on the nameplate capacity."""
        capacity = self._netl.get_installed_capacity_t_per_h()
        specific = (
            self._netl.get_total_plant_cost_usd()
            / capacity
            * self._usd_to_price_year_euro()
        )
        return element.capex_specific_conversion.set_data(
            default_value=specific,
            unit="Euro/(tproduct/h)",
            source=SourceInformation(
                description=(
                    "NETL total plant cost is divided by the assumed nameplate "
                    "capacity of 250,000/8760 t/h and converted from 2023 USD to "
                    "the model price year using ECB data. The finer-grinding plant "
                    "is used as an engineering proxy; no annualized capital charge "
                    "is added."
                ),
                metadata=self.metadata,
            ),
        )

    def get_grinding_fixed_opex(self, element: ConversionTechnology) -> Attribute:
        """Specific fixed operating cost of grinding."""
        capacity = self._netl.get_installed_capacity_t_per_h()
        specific = (
            self._netl.get_fixed_opex_usd_per_year()
            / capacity
            * self._usd_to_price_year_euro()
        )
        return element.opex_specific_fixed.set_data(
            default_value=specific,
            unit="Euro/(tproduct/h)",
            source=SourceInformation(
                description=(
                    "NETL annual labour, tax and insurance costs plus maintenance "
                    "material are divided by the assumed nameplate capacity of "
                    "250,000/8760 t/h. Maintenance material is treated as fixed "
                    "O&M. Costs are converted from 2023 USD using ECB data."
                ),
                metadata=self.metadata,
            ),
        )

    def get_grinding_lifetime(self, element: ConversionTechnology) -> Attribute:
        """Lifetime of the grinding plant."""
        return element.lifetime.set_data(
            default_value=self._netl.get_lifetime_years(),
            unit="1",
            source=SourceInformation(
                description=(
                    "The NETL economic project life of 31 years is used as a "
                    "technical-lifetime proxy for grinding."
                ),
                metadata=self.metadata,
            ),
        )

    def get_grinding_max_load(self, element: ConversionTechnology) -> Attribute:
        """Maximum load of the grinding plant."""
        return element.max_load.set_data(
            default_value=self._netl.get_max_load(),
            unit="1",
            source=SourceInformation(
                description=(
                    "The NETL capacity factor of 0.85 is used as maximum load. "
                    "Applied to the assumed nameplate of 250,000 t/year, this "
                    "allows up to 212,500 t/year."
                ),
                metadata=self.metadata,
            ),
        )

    def get_application_opex(self, element: ConversionTechnology) -> Attribute:
        """Non-fuel application-service cost."""
        cost = (
            self._netl.get_application_cost_usd_per_t() * self._usd_to_price_year_euro()
        )
        return element.opex_specific_variable.set_data(
            default_value=cost,
            unit="Euro/tproduct",
            source=SourceInformation(
                description=(
                    "NETL field application costs of 6 USD/t exclude fuel and "
                    "delivery. The per-tonne cost is used as a proxy at the "
                    "selected application rate and converted from 2023 USD using "
                    "ECB data."
                ),
                metadata=self.metadata,
            ),
        )

    def get_basalt_price_import(self, element) -> Attribute:
        """Purchase price of imported basalt."""
        price = self._netl.get_rock_price_usd_per_t() * self._usd_to_price_year_euro()
        return element.price_import.set_data(
            default_value=price,
            unit="Euro/tproduct",
            source=SourceInformation(
                description=(
                    "The NETL rock purchase price of 25 USD/t is converted from "
                    "2023 USD using ECB data. Preparation and delivery are "
                    "accounted separately; upstream quarry emissions are excluded."
                ),
                metadata=self.metadata,
            ),
        )

    def get_application_capacity_limit(
        self, element: ConversionTechnology
    ) -> Attribute:
        """Annual application allowance from arable land at 20 t/ha/year."""
        nodes = list(element.model.config.system.set_nodes)
        arable_ha = self._arable.get_arable_land_ha(nodes)
        limit = (
            arable_ha * self.APPLICATION_RATE_T_PER_HA_YEAR / Constants.HOURS_PER_YEAR
        )
        limit.name = "capacity_limit"
        limit.index.name = "node"
        return element.capacity_limit.set_data(
            df=cast(pd.Series, limit),
            unit="tproduct/h",
            source=SourceInformation(
                description=(
                    f"World Bank arable area ({self._arable.YEAR}) is multiplied by "
                    "an assumed allowance of 20 t/ha/year and divided by 8760. "
                    "The lower loading is motivated by repeated-application "
                    "risks discussed by Dupla et al. (2023), not a demonstrated "
                    "soil or regulatory limit. All arable land is eligible; "
                    "cumulative stocks are not tracked. Biochar has a separate "
                    "allowance on the same land."
                ),
                metadata=self.metadata,
            ),
        )
