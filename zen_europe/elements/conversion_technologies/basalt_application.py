"""Basalt field-application conversion technology."""

from __future__ import annotations

from typing import TYPE_CHECKING

from zen_creator import AssumptionInformation, Attribute, ConversionTechnology

from zen_europe.datasets.dataset_collections.basalt_erw_parameters import (
    BasaltErwParameters,
)

if TYPE_CHECKING:
    from zen_creator.model import Model


class BasaltApplication(ConversionTechnology):
    """Terminal application of ground basalt with a fixed removal credit."""

    name: str = "basalt_application"

    def __init__(self, model: Model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    def _parameters(self) -> BasaltErwParameters:
        return BasaltErwParameters(settings=self.settings, source_path=self.source_path)

    def _set_reference_carrier(self) -> Attribute:
        """Set the reference carrier to applied ground basalt."""
        return Attribute(
            name="reference_carrier", default_value=["ground_basalt"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """Set the inputs to ground basalt, freight, and diesel."""
        return Attribute(
            name="input_carrier",
            default_value=["ground_basalt", "truck_mileage", "diesel"],
            element=self,
        )

    def _set_output_carrier(self) -> Attribute:
        """Basalt application is represented as a terminal sink."""
        return Attribute(name="output_carrier", default_value=[], element=self)

    def _set_conversion_factor(self) -> Attribute:
        """Return freight and diesel use per tonne applied."""
        return self._parameters().get_application_conversion_factor(self)

    def _set_carbon_intensity_technology(self) -> Attribute:
        """Credit the fixed gross field-programme removal ratio."""
        return self._parameters().get_carbon_intensity_technology(self)

    def _set_construction_time(self) -> Attribute:
        """No separate construction time is assigned."""
        attr = self.construction_time
        return attr.set_data(
            default_value=0,
            source=AssumptionInformation(
                description=(
                    "No separate construction time is assigned to basalt "
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
                    "The 100-year service lifetime is a bookkeeping "
                    "assumption that keeps the application service available "
                    "across the model time steps. It is not a weathering "
                    "lifetime."
                ),
            ),
        )

    def _set_capex_specific_conversion(self) -> Attribute:
        """No separate capital cost is assigned to application."""
        attr = self.capex_specific_conversion
        return attr.set_data(
            default_value=0,
            unit="Euro/(tproduct/h)",
            source=AssumptionInformation(
                description=(
                    "No separate capital cost is assigned to basalt "
                    "application. Plant capital is on grinding."
                ),
            ),
        )

    def _set_opex_specific_fixed(self) -> Attribute:
        """No fixed operating cost is assigned to application."""
        attr = self.opex_specific_fixed
        return attr.set_data(
            default_value=0,
            unit="Euro/(tproduct/h)",
            source=AssumptionInformation(
                description=(
                    "No fixed operating cost is assigned to basalt application."
                ),
            ),
        )

    def _set_opex_specific_variable(self) -> Attribute:
        """Return the non-fuel application-service cost."""
        return self._parameters().get_application_opex(self)

    def _set_capacity_limit(self) -> Attribute:
        """Limit annual application by the configured country land allowance."""
        return self._parameters().get_application_capacity_limit(self)

    def _set_capacity_existing(self) -> Attribute:
        """No existing application capacity is assigned."""
        attr = self.capacity_existing
        return attr.set_data(
            default_value=0,
            source=AssumptionInformation(
                description=("No existing capacity is assigned to basalt application."),
            ),
        )
