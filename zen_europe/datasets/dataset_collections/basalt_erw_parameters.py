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
from zen_europe.datasets.datasets.technology.netl_basalt_erw_costs import (
    NetlBasaltErwCosts,
)
from zen_europe.utils.constants import Constants


class BasaltErwParameters(DatasetCollection):
    """Convert basalt ERW source values to the model's mass-based units."""

    name = "basalt_erw_parameters"
    DELIVERY_TKM_PER_T = 100.0
    APPLICATION_RATE_T_PER_HA_YEAR = 50.0

    def __init__(self, settings: Settings, source_path: Path | str):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _get_data(self) -> dict[str, Any]:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")
        return {
            "beerling_basalt_removal": BeerlingBasaltRemoval(self.source_path),
            "cobo_basalt_electricity": CoboBasaltElectricity(self.source_path),
            "netl_basalt_erw_costs": NetlBasaltErwCosts(self.source_path),
            "worldbank_arable_land": WorldBankArableLand(self.source_path),
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
    def _netl(self) -> NetlBasaltErwCosts:
        return cast(NetlBasaltErwCosts, self.data["netl_basalt_erw_costs"])

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

    def diesel_gwh_per_tproduct(self) -> float:
        """Application diesel, GWh per tonne of ground basalt."""
        return (
            self._netl.get_diesel_liter_per_t()
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
                    "One tonne of purchased basalt yields one tonne of ground "
                    "basalt. Electricity is the Cobo et al. (2026) field/base LCI "
                    "quotient of 0.1947445179009531 MWh/tCO2 and "
                    "69.9062230049315 t rock/tCO2, written per tonne of "
                    "basalt. NETL's finer 20 µm grinding electricity is not "
                    "used."
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
                    "Delivery is an assumed 100 km European scenario, equal to "
                    "100 tkm per tonne. It is not the workbook's 215 km case. "
                    "Truck energy and costs stay in the existing freight "
                    "representation. Application diesel is the NETL area "
                    "proxy: 2,059 US gal/year over 1,190 ha (Exhibit 4-1 land "
                    "need; Section 3.10.1 states tractor fuel depends on area "
                    "covered), converted to litres per hectare and divided by "
                    "50 t/ha/year. The heating value is the repository "
                    "constant of 10 kWh/L. The NETL 172,740 t/year line is "
                    "not used."
                ),
                metadata=self.metadata,
            ),
        )

    def get_carbon_intensity_technology(
        self, element: ConversionTechnology
    ) -> Attribute:
        """Fixed gross negative emissions of soil-applied basalt."""
        return element.carbon_intensity_technology.set_data(
            default_value=-self._beerling.get_removal_tco2_per_t_basalt(),
            unit="ton/tproduct",
            source=SourceInformation(
                description=(
                    "This field-program removal-potential ratio is transferred "
                    "to European deployment as a proxy. Credit is assigned in "
                    "the application year; subsequent weathering is not "
                    "tracked or credited. Immediate accounting can favour "
                    "late-horizon deployment. The fixed yield omits additional "
                    "long-term uptake; these approximations are not assumed to "
                    "cancel. The coefficient is 0.0525 tCO2 per tonne of "
                    "basalt from Beerling et al. (2024): 10.5 tCO2/ha over "
                    "200 t/ha. The attribute unit is ton/tproduct, matching "
                    "cement and zen-garden's emissions-[mass] convention; the "
                    "numeric value is tonnes of CO2 per tonne of basalt. It is "
                    "not the eventual 0.2514 tCO2/t potential, the factor "
                    "0.775 is not applied again, and no temperature "
                    "correction is added. Electricity, freight, and diesel "
                    "emissions are accounted through the existing model rather "
                    "than deducted again from this gross coefficient."
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
                    "NETL total plant cost of 26,001,000 USD (May 2023) is "
                    "divided by the assumed nameplate capacity of "
                    "250,000/8760 t/h. Owner overnight costs, as-spent "
                    "financing, fixed-charge rates, and annualized USD/tCO2 "
                    "costs are not added. ECB dollar-to-euro and inflation "
                    f"update the 2023 dollar basis to "
                    f"{self.settings.time.price_year}. The NETL plant is a "
                    "finer engineering case than the selected field basalt; "
                    "this is a transferred cost proxy."
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
                    "NETL fixed labour, tax and insurance of 3,121,279 USD/year "
                    "plus maintenance material of 296,406 USD/year are treated "
                    "once as fixed annual plant cost and divided by "
                    "250,000/8760 t/h. Maintenance material is not charged "
                    "again per tonne. ECB conversion matches the capital cost."
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
                    "The 31-year lifetime is transferred from the NETL "
                    "economic project life as a proxy. It is not a technical "
                    "life reported for the plant and it is not the "
                    "weathering horizon."
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
                    "Maximum load 0.85 limits throughput of a nameplate "
                    "250,000 t/year plant to 212,500 t/year. It is not used "
                    "to shrink the specific capital or fixed costs."
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
                    "NETL material-application cost of 6 USD/t excludes fuel "
                    "and transport. Using it at 50 t/ha is a per-tonne proxy, "
                    "not a NETL field rate. ECB conversion matches the plant "
                    "costs."
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
                    "NETL rock purchase price of 25 USD/t, converted with ECB "
                    "dollar-to-euro and inflation. Purchase cost is kept "
                    "separate from plant investment and application cost. "
                    "Upstream quarry emissions are excluded by the model "
                    "boundary."
                ),
                metadata=self.metadata,
            ),
        )

    def get_application_capacity_limit(
        self, element: ConversionTechnology
    ) -> Attribute:
        """Annual application ceiling from arable land at 50 t/ha/year."""
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
                    "Capacity limit is country arable land from World Bank "
                    "AG.LND.ARBL.HA (2023) times 50 t/ha/year, divided by "
                    "8760 hours so that with max_load 1 the annual "
                    "throughput cannot exceed that product. All reported "
                    "arable area is treated as eligible. No cumulative soil "
                    "stock is tracked. BCR and ERW may coexist; there is no "
                    "shared exclusive-hectare constraint."
                ),
                metadata=self.metadata,
            ),
        )
