"""Application diesel, retained-carbon credit, and non-fuel service cost."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from zen_creator import Attribute, ConversionTechnology, DatasetCollection
from zen_creator.datasets.datasets.metadata import SourceInformation
from zen_creator.utils.settings import Settings

from zen_europe.datasets.datasets.financial.ECB import ECBInflation
from zen_europe.datasets.datasets.technology.dalgaard_application_diesel import (
    DalgaardApplicationDiesel,
)
from zen_europe.datasets.datasets.technology.eurofins_straw_biochar import (
    EurofinsStrawBiochar,
)
from zen_europe.datasets.datasets.technology.teichmann_biochar_application_cost import (
    TeichmannBiocharApplicationCost,
)
from zen_europe.datasets.datasets.technology.woolf_biochar_permanence import (
    WoolfBiocharPermanence,
)
from zen_europe.utils.constants import Constants


class BiocharApplicationParameters(DatasetCollection):
    """Convert the biochar-application literature values to model units."""

    name = "biochar_application_parameters"
    CO2_PER_CARBON = 44 / 12

    def __init__(self, settings: Settings, source_path: Path | str):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _get_data(self) -> dict[str, Any]:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")
        return {
            "eurofins_straw_biochar": EurofinsStrawBiochar(self.source_path),
            "woolf_biochar_permanence": WoolfBiocharPermanence(self.source_path),
            "dalgaard_application_diesel": DalgaardApplicationDiesel(self.source_path),
            "teichmann_biochar_application_cost": TeichmannBiocharApplicationCost(
                self.source_path
            ),
            "ecb_inflation": ECBInflation(self.source_path),
        }

    @property
    def _biochar_mwh_per_ton(self) -> float:
        return Constants.BIOCHAR_GWH_PER_TON * 1000

    @property
    def _eurofins(self) -> EurofinsStrawBiochar:
        return cast(EurofinsStrawBiochar, self.data["eurofins_straw_biochar"])

    @property
    def _woolf(self) -> WoolfBiocharPermanence:
        return cast(WoolfBiocharPermanence, self.data["woolf_biochar_permanence"])

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
            * self._woolf.get_retained_fraction()
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
        """Diesel consumption of biochar application."""
        return element.conversion_factor.set_data(
            default_value=[
                {
                    "diesel": {
                        "default_value": self.diesel_mwh_per_mwh_biochar(),
                        "unit": "GWh/GWh",
                    }
                }
            ],
            source=SourceInformation(
                description=(
                    "Biochar application consumes diesel for loading and "
                    "spreading. Dalgaard et al. report 0.6 L diesel per tonne "
                    "for manure loading and spreading. That estimate is "
                    "transferred to dry biochar as an agricultural-operation "
                    "proxy and is not a measurement of biochar application. "
                    "It is converted with the repository diesel heating value "
                    "of 10 kWh/L and the biochar heating value of 25 GJ/t."
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
                    "The removal coefficient is an organic-carbon fraction of "
                    "0.75, from the Eurofins dry-basis measurement of 75.3% "
                    "rounded to 0.75, times a 100-year retained fraction of "
                    "0.82, times 44/12. The Eurofins straw biochar is a proxy "
                    "for the modeled product. The retained fraction is Woolf "
                    "et al. Table 3 for high-temperature pyrolysis at 15°C; "
                    "the published 1000-year value of 0.25 is not used. The "
                    "credit is applied only when biochar is sent to soil. "
                    "Later decay is not simulated, no soil-application limit "
                    "is imposed, and this coefficient is not a complete "
                    "life-cycle net-removal estimate. The result is converted "
                    "from tonnes of CO2 per dry tonne with the biochar heating "
                    "value of 25 GJ/t."
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
                    "€6.23/t biochar from Teichmann, applied here per dry "
                    "tonne as a modeling assumption. The source does not "
                    "distinguish fresh and dry biochar mass. The cost excludes "
                    "fuel and covers loading, wetting, local tractor movement "
                    "and spreading. No separate distribution-transport cost is "
                    "modeled; local handling and movement may be embedded in "
                    "this application-service proxy. Incorporation is assumed "
                    "to occur during ordinary scheduled tillage. ECB inflation "
                    f"updates the 2012 price basis to "
                    f"{self.settings.time.price_year} and does not change the "
                    "underlying equipment assumptions. The cost is converted "
                    "per MWh with the biochar heating value of 25 GJ/t."
                ),
                metadata=self.metadata,
            ),
        )
