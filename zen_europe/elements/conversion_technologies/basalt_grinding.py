"""Basalt grinding conversion technology."""

from __future__ import annotations

from typing import TYPE_CHECKING

from zen_creator import AssumptionInformation, Attribute, ConversionTechnology

from zen_europe.datasets.dataset_collections.basalt_erw_parameters import (
    BasaltErwParameters,
)

if TYPE_CHECKING:
    from zen_creator.model import Model


class BasaltGrinding(ConversionTechnology):
    """Electric grinding of purchased basalt to ground basalt."""

    name: str = "basalt_grinding"

    def __init__(self, model: Model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    def _parameters(self) -> BasaltErwParameters:
        return BasaltErwParameters(settings=self.settings, source_path=self.source_path)

    def _set_reference_carrier(self) -> Attribute:
        """Set the reference carrier to ground basalt."""
        return Attribute(
            name="reference_carrier", default_value=["ground_basalt"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """Set the inputs to purchased basalt and electricity."""
        return Attribute(
            name="input_carrier",
            default_value=["basalt", "electricity"],
            element=self,
        )

    def _set_output_carrier(self) -> Attribute:
        """Set the output to ground basalt."""
        return Attribute(
            name="output_carrier", default_value=["ground_basalt"], element=self
        )

    def _set_lifetime(self) -> Attribute:
        """Return the NETL economic-life proxy."""
        return self._parameters().get_grinding_lifetime(self)

    def _set_construction_time(self) -> Attribute:
        """No separate construction time is assigned."""
        attr = self.construction_time
        return attr.set_data(
            default_value=0,
            source=AssumptionInformation(
                description=(
                    "No separate construction time is assigned to basalt grinding."
                ),
            ),
        )

    def _set_conversion_factor(self) -> Attribute:
        """Return basalt and electricity use per tonne of ground basalt."""
        return self._parameters().get_grinding_conversion_factor(self)

    def _set_carbon_intensity_technology(self) -> Attribute:
        """Grinding itself carries no direct process emissions."""
        attr = self.carbon_intensity_technology
        return attr.set_data(
            default_value=0,
            unit="ton/tproduct",
            source=AssumptionInformation(
                description=(
                    "Grinding process emissions are zero. Electricity "
                    "emissions are accounted through the electricity system. "
                    "The removal credit is booked only at application. The "
                    "unit ton/tproduct matches cement and zen-garden's "
                    "emissions-[mass] convention."
                ),
            ),
        )

    def _set_capex_specific_conversion(self) -> Attribute:
        """Return the NETL total-plant-cost specific capital cost."""
        return self._parameters().get_grinding_capex(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """Return the NETL fixed annual plant cost."""
        return self._parameters().get_grinding_fixed_opex(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """No separate variable non-energy cost is assigned to grinding."""
        attr = self.opex_specific_variable
        return attr.set_data(
            default_value=0,
            unit="Euro/tproduct",
            source=AssumptionInformation(
                description=(
                    "No separate variable non-energy operating cost is "
                    "assigned to grinding. Electricity is paid through the "
                    "electricity carrier. Rock purchase is paid on the "
                    "basalt carrier."
                ),
            ),
        )

    def _set_max_load(self) -> Attribute:
        """Return the NETL maximum load factor."""
        return self._parameters().get_grinding_max_load(self)

    def _set_capacity_existing(self) -> Attribute:
        """No existing grinding capacity is assigned."""
        attr = self.capacity_existing
        return attr.set_data(
            default_value=0,
            source=AssumptionInformation(
                description="No existing capacity is assigned to basalt grinding.",
            ),
        )
