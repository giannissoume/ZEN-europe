from __future__ import annotations

from typing import TYPE_CHECKING

from zen_creator import AssumptionInformation, Attribute, ConversionTechnology

if TYPE_CHECKING:
    from zen_creator.model import Model


class BiocharToHardCoal(ConversionTechnology):
    """Energy-equivalent use of biochar as a hard-coal substitute."""

    name: str = "biochar_to_hard_coal"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_reference_carrier(self) -> Attribute:
        """Set the reference carrier to hard coal output."""
        return Attribute(
            name="reference_carrier", default_value=["hard_coal"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """Set the input carrier to biochar."""
        return Attribute(name="input_carrier", default_value=["biochar"], element=self)

    def _set_output_carrier(self) -> Attribute:
        """Set the output carrier to hard coal."""
        return Attribute(
            name="output_carrier", default_value=["hard_coal"], element=self
        )

    def _set_conversion_factor(self) -> Attribute:
        """Convert biochar to hard-coal-equivalent energy one-to-one."""
        attr = self.conversion_factor
        cf = [{"biochar": {"default_value": 1, "unit": "GWh/GWh"}}]
        return attr.set_data(
            default_value=cf,
            source=AssumptionInformation(
                description=(
                    "Biochar used as fuel is represented as an energy-equivalent "
                    "substitute for hard coal."
                ),
            ),
        )

    def _set_construction_time(self) -> Attribute:
        """No separate construction time is assigned to the substitution route."""
        attr = self.construction_time
        return attr.set_data(
            default_value=0,
            source=AssumptionInformation(
                description=(
                    "No separate construction time is assigned to biochar fuel "
                    "substitution."
                ),
            ),
        )

    def _set_lifetime(self) -> Attribute:
        """Set a long bookkeeping lifetime for the substitution route."""
        attr = self.lifetime
        return attr.set_data(
            default_value=100,
            source=AssumptionInformation(
                description=(
                    "The lifetime of biochar fuel substitution is manually "
                    "set to 100 years, effectively representing an "
                    "always-available allocation pathway rather than a "
                    "capital asset with a finite technical lifetime."
                ),
            ),
        )

    def _set_capex_specific_conversion(self) -> Attribute:
        """No separate capital cost is assigned to the substitution route."""
        attr = self.capex_specific_conversion
        return attr.set_data(
            default_value=0,
            unit="Euro/kW",
            source=AssumptionInformation(
                description=(
                    "No separate capital cost is assigned to biochar fuel "
                    "substitution."
                ),
            ),
        )

    def _set_opex_specific_fixed(self) -> Attribute:
        """No fixed operating cost is assigned to the substitution route."""
        attr = self.opex_specific_fixed
        return attr.set_data(
            default_value=0,
            unit="Euro/kW",
            source=AssumptionInformation(
                description=(
                    "No fixed operating cost is assigned to biochar fuel "
                    "substitution."
                ),
            ),
        )

    def _set_opex_specific_variable(self) -> Attribute:
        """No variable operating cost is assigned to the substitution route."""
        attr = self.opex_specific_variable
        return attr.set_data(
            default_value=0,
            unit="Euro/MWh",
            source=AssumptionInformation(
                description=(
                    "No variable operating cost is assigned to biochar fuel "
                    "substitution."
                ),
            ),
        )

    def _set_capacity_existing(self) -> Attribute:
        """No existing capacity is assigned to the substitution route."""
        attr = self.capacity_existing
        return attr.set_data(
            default_value=0,
            source=AssumptionInformation(
                description=(
                    "No existing capacity is assigned to biochar fuel substitution."
                ),
            ),
        )
