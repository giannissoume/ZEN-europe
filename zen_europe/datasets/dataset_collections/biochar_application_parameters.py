"""Biochar application inputs, retained-carbon credit, costs, and land ceiling."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from zen_creator import Attribute, ConversionTechnology, DatasetCollection
from zen_creator.datasets.datasets.metadata import SourceInformation
from zen_creator.utils.settings import Settings

from zen_europe.datasets.datasets.energy_system.worldbank_arable_land import (
    WorldBankArableLand,
)
from zen_europe.datasets.datasets.financial.ECB import ECBInflation
from zen_europe.datasets.datasets.technology.dalgaard_application_diesel import (
    DalgaardApplicationDiesel,
)
from zen_europe.datasets.datasets.technology.eu_biochar_application_limit import (
    EuBiocharApplicationLimit,
)
from zen_europe.datasets.datasets.technology.eurofins_straw_biochar import (
    EurofinsStrawBiochar,
)
from zen_europe.datasets.datasets.technology.ipcc_biochar_permanence import (
    IpccBiocharPermanence,
)
from zen_europe.datasets.datasets.technology.teichmann_biochar_application_cost import (
    TeichmannBiocharApplicationCost,
)
from zen_europe.utils.constants import Constants


class BiocharApplicationParameters(DatasetCollection):
    """Convert the biochar-application literature values to model units."""

    name = "biochar_application_parameters"
    CO2_PER_CARBON = 44 / 12
    DELIVERY_TKM_PER_TON = 100.0
    ELIGIBLE_ARABLE_FRACTION = 1.0
    # Fixed deployment assumption; independent of the simulated horizon or spacing.
    DEPLOYMENT_PROGRAMME_YEARS = 25.0

    def __init__(self, settings: Settings, source_path: Path | str):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _get_data(self) -> dict[str, Any]:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")
        return {
            "eurofins_straw_biochar": EurofinsStrawBiochar(self.source_path),
            "ipcc_biochar_permanence": IpccBiocharPermanence(self.source_path),
            "dalgaard_application_diesel": DalgaardApplicationDiesel(self.source_path),
            "teichmann_biochar_application_cost": TeichmannBiocharApplicationCost(
                self.source_path
            ),
            "ecb_inflation": ECBInflation(self.source_path),
            "worldbank_arable_land": WorldBankArableLand(self.source_path),
            "eu_biochar_application_limit": EuBiocharApplicationLimit(self.source_path),
        }

    @property
    def _biochar_mwh_per_ton(self) -> float:
        return Constants.BIOCHAR_GWH_PER_TON * 1000

    @property
    def _eurofins(self) -> EurofinsStrawBiochar:
        return cast(EurofinsStrawBiochar, self.data["eurofins_straw_biochar"])

    @property
    def _ipcc(self) -> IpccBiocharPermanence:
        return cast(IpccBiocharPermanence, self.data["ipcc_biochar_permanence"])

    @property
    def _dalgaard(self) -> DalgaardApplicationDiesel:
        return cast(DalgaardApplicationDiesel, self.data["dalgaard_application_diesel"])

    @property
    def _teichmann(self) -> TeichmannBiocharApplicationCost:
        return cast(
            TeichmannBiocharApplicationCost,
            self.data["teichmann_biochar_application_cost"],
        )

    @property
    def _ecb(self) -> ECBInflation:
        return cast(ECBInflation, self.data["ecb_inflation"])

    def diesel_mwh_per_mwh_biochar(self) -> float:
        """Diesel energy per MWh of dry biochar applied."""
        diesel_mwh_per_ton = (
            self._dalgaard.get_diesel_liter_per_ton()
            * Constants.DIESEL_KWH_PER_LITER
            / 1000
        )
        return diesel_mwh_per_ton / self._biochar_mwh_per_ton

    def stored_co2_ton_per_mwh_biochar(self) -> float:
        """Retained CO2, tonnes per MWh of dry biochar applied."""
        stored_co2_per_ton = (
            self._eurofins.get_organic_carbon_fraction()
            * self._ipcc.get_retained_fraction()
            * self.CO2_PER_CARBON
        )
        return stored_co2_per_ton / self._biochar_mwh_per_ton

    def cost_eur_per_mwh_biochar(self) -> float:
        """Inflated non-fuel service cost, Euro per MWh of dry biochar."""
        inflation = self._ecb.get_inflation_rate(
            base_year=self._teichmann.get_cost_year(),
            target_year=self.settings.time.price_year,
        )
        return (
            self._teichmann.get_cost_eur_per_ton()
            * inflation
            / self._biochar_mwh_per_ton
        )

    def get_conversion_factor(self, element: ConversionTechnology) -> Attribute:
        """Field diesel and regional freight per unit of applied dry biochar."""
        return element.conversion_factor.set_data(
            default_value=[
                {
                    "diesel": {
                        "default_value": self.diesel_mwh_per_mwh_biochar(),
                        "unit": "GWh/GWh",
                    }
                },
                {
                    "truck_mileage": {
                        "default_value": self.DELIVERY_TKM_PER_TON
                        / self._biochar_mwh_per_ton,
                        "unit": "tkm/MWh",
                    }
                },
            ],
            source=SourceInformation(
                description=(
                    "Dalgaard et al. (2001), Table 2 manure loading and spreading "
                    "is used as a proxy at 0.6 L diesel/t dry biochar. Delivery is "
                    "assumed to be 100 km, supplied by the existing freight sector. "
                    "Inputs are converted to the biochar reference using 10 kWh/L "
                    "diesel and 25 GJ/t biochar."
                ),
                metadata=self.metadata,
            ),
        )

    def get_carbon_intensity_technology(
        self, element: ConversionTechnology
    ) -> Attribute:
        """Negative emission credit of soil-applied biochar."""
        return element.carbon_intensity_technology.set_data(
            default_value=-self.stored_co2_ton_per_mwh_biochar(),
            unit="ton/MWh",
            source=SourceInformation(
                description=(
                    "Eurofins organic carbon of 0.75 times IPCC 100-year retention "
                    "of 0.80 times 44/12 gives 2.2 tCO2/t dry biochar. "
                    "Medium-temperature pyrolysis is assumed. The credit is "
                    "converted at 25 GJ/t and assigned only to soil application."
                ),
                metadata=self.metadata,
            ),
        )

    def get_opex_specific_variable(self, element: ConversionTechnology) -> Attribute:
        """Non-fuel application-service cost."""
        return element.opex_specific_variable.set_data(
            default_value=self.cost_eur_per_mwh_biochar(),
            unit="Euro/MWh",
            source=SourceInformation(
                description=(
                    "Teichmann (2015), Table 34 gives 6.23 Euro/t (2012), used here "
                    "as a non-fuel application-cost proxy per dry tonne. Costs are "
                    "adjusted to the model price year with ECB inflation and "
                    "converted at 25 GJ/t. Diesel and delivery are accounted "
                    "separately; incorporation uses routine tillage."
                ),
                metadata=self.metadata,
            ),
        )

    def get_capacity_limit(self, element: ConversionTechnology) -> Attribute:
        """Annualized land ceiling expressed in biochar-reference MW."""
        land = cast(WorldBankArableLand, self.data["worldbank_arable_land"])
        allowance = cast(
            EuBiocharApplicationLimit, self.data["eu_biochar_application_limit"]
        )
        annual_t_per_ha = (
            allowance.get_cumulative_limit_t_per_ha() / self.DEPLOYMENT_PROGRAMME_YEARS
        )
        nodes = list(element.model.config.system.set_nodes)
        limit = (
            land.get_arable_land_ha(nodes)
            * self.ELIGIBLE_ARABLE_FRACTION
            * annual_t_per_ha
            * self._biochar_mwh_per_ton
            / Constants.HOURS_PER_YEAR
        )
        limit.name = "capacity_limit"
        limit.index.name = "node"
        return element.capacity_limit.set_data(
            df=limit,
            unit="MW",
            source=SourceInformation(
                description=(
                    "The EU cumulative ceiling of 50 t/ha is annualized over an "
                    "assumed fixed 25-year programme and multiplied by World Bank "
                    f"arable area ({land.YEAR}). Historical applications are zero "
                    "and all arable land is eligible, including in non-EU countries. "
                    "The "
                    "allowance is converted at 25 GJ/t and 8760 h/year. Cumulative "
                    "stocks are not tracked; ERW has a separate allowance on the "
                    "same land."
                ),
                metadata=self.metadata,
            ),
        )
