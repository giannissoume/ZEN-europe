"""Prepare attributes for the bundled in-plant seawater mineralization pathway."""

import pandas as pd
from zen_creator import (
    AssumptionInformation,
    Attribute,
    Dataset,
    DatasetCollection,
    SourceInformation,
)
from zen_creator.utils.settings import Settings

from zen_europe.datasets.datasets.energy_system.marine_regions_eez import (
    MarineRegionsEez,
)
from zen_europe.datasets.datasets.financial.ECB import ECBDollar2Euro, ECBInflation
from zen_europe.datasets.datasets.technology.chen_seawater_mineralization import (
    ChenSeawaterMineralization,
)
from zen_europe.utils.constants import Constants


class ElectrochemicalOaeParameters(DatasetCollection):
    """Normalize Chen's first-of-a-kind package on purchased olivine input."""

    name = "electrochemical_oae_parameters"

    def _get_data(self) -> dict[str, Dataset]:
        return {
            "plant": ChenSeawaterMineralization(self.source_path),
            "exchange": ECBDollar2Euro(self.source_path),
            "inflation": ECBInflation(self.source_path),
        }

    def _value(self, parameter: str) -> float:
        return self.data["plant"].get_value(parameter)

    def _dollar_factor(self, settings: Settings) -> float:
        year = settings.electrochemical_oae.assumed_cost_year
        return self.data["exchange"].get_dollar2euro(year) * self.data[
            "inflation"
        ].get_inflation_rate(year, settings.time.price_year)

    def get_nameplate_tph(self) -> float:
        """Return rated throughput before the annual uptime derating."""
        return (
            self._value("annual_removal")
            * self._value("rock_requirement")
            / (Constants.HOURS_PER_YEAR * self._value("uptime"))
        )

    def get_conversion_factor(self, element) -> Attribute:
        rock = self._value("rock_requirement")
        hydrogen_kg_per_t = (
            self._value("annual_hydrogen") * 1000 / self._value("annual_removal") / rock
        )
        factors = {
            "electricity": (
                self._value("electricity_requirement") / rock / 1000,
                "GWh/tproduct",
            ),
            "truck_mileage": (
                element.settings.electrochemical_oae.delivery_km,
                "tkm/tproduct",
            ),
            "hydrogen": (
                hydrogen_kg_per_t * Constants.HYDROGEN_KWH_PER_KG / 1e6,
                "GWh/tproduct",
            ),
        }
        return element.conversion_factor.set_data(
            default_value=[
                {carrier: {"default_value": value, "unit": unit}}
                for carrier, (value, unit) in factors.items()
            ],
            source=SourceInformation(
                description=(
                    "Apply Chen's aggregate first-of-a-kind package to in-plant "
                    "carbonation. Use olivine for alkaline rock and charge delivery."
                ),
                metadata=self.data["plant"].metadata,
            ),
        )

    def get_carbon_intensity(self, element) -> Attribute:
        loss = element.settings.electrochemical_oae.discharge_loss_fraction
        return element.carbon_intensity_technology.set_data(
            default_value=-(1 - loss) / self._value("rock_requirement"),
            unit="ton/tproduct",
            source=SourceInformation(
                description=(
                    "Invert Chen et al.'s engineering requirement of 1.5 t rock/tCO₂ "
                    "to calculate removal per tonne of olivine input. La Plante et "
                    "al., Case 2a, supports in-plant atmospheric uptake. "
                    f"Assume a post-discharge loss fraction of {loss:g}. "
                    "Isometric v1.1 §8.3.3 accounts for discharge losses separately."
                ),
                metadata=self.data["plant"].metadata,
            ),
        )

    def get_capacity_limit(self, element) -> Attribute:
        nodes = element.model.config.system.set_nodes
        first_year = element.settings.electrochemical_oae.first_available_year
        limits = pd.Series(
            {
                (node, year): (
                    float("inf")
                    if node in MarineRegionsEez.COUNTRIES and year >= first_year
                    else 0.0
                )
                for node in nodes
                for year in element.settings.time.years
            },
            name="capacity_limit",
        ).rename_axis(["node", "year"])
        return element.capacity_limit.set_data(
            df=limits,
            default_value=0,
            unit=element.power_unit,
            source=AssumptionInformation(
                description=(
                    f"Coastal model countries are eligible from {first_year}. "
                    "Deployment assumes suitable sites and treated discharge."
                )
            ),
        )

    def _cost(
        self, attribute: Attribute, value: float, unit: str, settings: Settings
    ) -> Attribute:
        year = settings.electrochemical_oae.assumed_cost_year
        return attribute.set_data(
            default_value=value * self._dollar_factor(settings),
            unit=unit,
            source=SourceInformation(
                description=(
                    f"Chen's first-of-a-kind estimate in assumed USD{year}, "
                    "converted to the model price year using ECB data. "
                    "Generic alkaline rock represents purchased olivine."
                ),
                metadata=self.metadata,
            ),
        )

    def get_price_import(self, element) -> Attribute:
        return self._cost(
            element.price_import,
            self._value("rock_price"),
            "Euro/tproduct",
            element.settings,
        )

    def get_capex(self, element) -> Attribute:
        return self._cost(
            element.capex_specific_conversion,
            self._value("installed_cost") / self.get_nameplate_tph(),
            "Euro/(tproduct/h)",
            element.settings,
        )

    def get_fixed_opex(self, element) -> Attribute:
        return self._cost(
            element.opex_specific_fixed,
            self._value("fixed_opex_fraction")
            * self._value("installed_cost")
            / self.get_nameplate_tph(),
            "Euro/(tproduct/h)",
            element.settings,
        )

    def get_max_load(self, element) -> Attribute:
        return element.max_load.set_data(
            default_value=self._value("uptime"),
            source=SourceInformation(
                description="Use published plant uptime as the maximum load proxy.",
                metadata=self.data["plant"].metadata,
            ),
        )
