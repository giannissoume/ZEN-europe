from __future__ import annotations

from typing import TYPE_CHECKING

from zen_creator import AssumptionInformation, Attribute, ConversionTechnology

from zen_europe.datasets.dataset_collections.biochar_application_parameters import (
    BiocharApplicationParameters,
)

if TYPE_CHECKING:
    from zen_creator.model import Model


class BiocharApplication(ConversionTechnology):
    """Agricultural biochar application with durable carbon retention."""

    name: str = "biochar_application"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    def _parameters(self) -> BiocharApplicationParameters:
        return BiocharApplicationParameters(
            settings=self.settings, source_path=self.source_path
        )

    def _set_reference_carrier(self) -> Attribute:
        """Set the reference carrier to applied biochar."""
        return Attribute(
            name="reference_carrier", default_value=["biochar"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """Set the inputs to biochar, application diesel, and delivery freight."""
        return Attribute(
            name="input_carrier",
            default_value=["biochar", "diesel", "truck_mileage"],
            element=self,
        )

    def _set_output_carrier(self) -> Attribute:
        """Biochar application is represented as a terminal sink."""
        return Attribute(name="output_carrier", default_value=[], element=self)

    def _set_conversion_factor(self) -> Attribute:
        """Return field diesel and delivery freight per dry biochar applied."""
        return self._parameters().get_conversion_factor(self)

    def _set_carbon_intensity_technology(self) -> Attribute:
        """Credit durably retained biochar carbon."""
        return self._parameters().get_carbon_intensity_technology(self)

    def _set_construction_time(self) -> Attribute:
        """No separate construction time is assigned to biochar application."""
        attr = self.construction_time
        return attr.set_data(
            default_value=0,
            source=AssumptionInformation(
                description=(
                    "No separate construction time is assigned to biochar "
                    "application."
                ),
            ),
        )

    def _set_lifetime(self) -> Attribute:
        """Keep the application service available across model time steps."""
        attr = self.lifetime
        return attr.set_data(
            default_value=100,
            source=AssumptionInformation(
                description=(
                    "The 100-year service lifetime is a bookkeeping assumption "
                    "that keeps the application service available across the "
                    "model time steps. It does not describe biochar carbon "
                    "persistence."
                ),
            ),
        )

    def _set_capex_specific_conversion(self) -> Attribute:
        """No separate capital cost is assigned to biochar application."""
        attr = self.capex_specific_conversion
        return attr.set_data(
            default_value=0,
            unit="Euro/kW",
            source=AssumptionInformation(
                description=(
                    "No separate capital cost is assigned to biochar application."
                ),
            ),
        )

    def _set_opex_specific_fixed(self) -> Attribute:
        """No fixed operating cost is assigned to biochar application."""
        attr = self.opex_specific_fixed
        return attr.set_data(
            default_value=0,
            unit="Euro/kW",
            source=AssumptionInformation(
                description=(
                    "No fixed operating cost is assigned to biochar application."
                ),
            ),
        )

    def _set_opex_specific_variable(self) -> Attribute:
        """Return non-fuel application-service cost per unit of biochar."""
        return self._parameters().get_opex_specific_variable(self)

    def _set_capacity_existing(self) -> Attribute:
        """No existing capacity is assigned to biochar application."""
        attr = self.capacity_existing
        return attr.set_data(
            default_value=0,
            source=AssumptionInformation(
                description=(
                    "No existing capacity is assigned to biochar application."
                ),
            ),
        )

    def _set_capacity_limit(self) -> Attribute:
        """Limit application with the country's annualized arable-area allowance."""
        return self._parameters().get_capacity_limit(self)
