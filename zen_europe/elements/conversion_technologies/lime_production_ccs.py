"""Integrated oxyfuel calcination, capture and dry hydration."""

from zen_creator import AssumptionInformation, Attribute, ConversionTechnology

from zen_europe.datasets.dataset_collections.liming_oae_parameters import (
    LimingOaeParameters,
)


class LimeProductionCCS(ConversionTechnology):
    """Produce dry hydrate with capture following the baseline CCS convention."""

    name = "lime_production_ccs"

    def __init__(self, model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    def _parameters(self) -> LimingOaeParameters:
        return LimingOaeParameters(self.settings, self.source_path)

    def _set_reference_carrier(self) -> Attribute:
        """Use dry hydrated lime as the reference."""
        return Attribute(
            name="reference_carrier", default_value=["hydrated_lime"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """Set the input flows."""
        return Attribute(
            name="input_carrier",
            default_value=["limestone", "natural_gas", "electricity"],
            element=self,
        )

    def _set_output_carrier(self) -> Attribute:
        """Set the output flows."""
        return Attribute(
            name="output_carrier",
            default_value=["hydrated_lime", "carbon"],
            element=self,
        )

    def _set_conversion_factor(self) -> Attribute:
        """Return the source-normalized flow coefficients."""
        return self._parameters().get_production_conversion_factor(self)

    def _set_carbon_intensity_technology(self) -> Attribute:
        """Charge gross process CO2; storage credits the captured output."""
        return self._parameters().get_production_carbon_intensity(self)

    def _set_lifetime(self) -> Attribute:
        """Use the aggregate plant lifetime."""
        return self._parameters().get_production_lifetime(self)

    def _set_construction_time(self) -> Attribute:
        """No separate construction delay."""
        return self.construction_time.set_data(
            default_value=0,
            source=AssumptionInformation(description="No separate construction delay."),
        )

    def _set_capacity_existing(self) -> Attribute:
        """No existing OAE capacity is assigned."""
        return self.capacity_existing.set_data(
            default_value=0,
            source=AssumptionInformation(
                description="No existing OAE capacity is assigned."
            ),
        )

    def _set_capacity_limit(self) -> Attribute:
        """Restrict production to coastal nodes."""
        return self._parameters().get_capacity_limit(self, production=True)

    def _set_capex_specific_conversion(self) -> Attribute:
        """Return the normalized cost attribute."""
        return self._parameters().get_production_capex(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """Return the normalized cost attribute."""
        return self._parameters().get_production_fixed_opex(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """Return the normalized cost attribute."""
        return self._parameters().get_production_variable_opex(self)

    def _set_max_load(self) -> Attribute:
        """Allow for plant maintenance downtime."""
        return self.max_load.set_data(
            default_value=self.settings.liming_oae.production_max_load,
            source=AssumptionInformation(
                description=(
                    f"Assumed {self.settings.liming_oae.production_max_load:.0%} plant "
                    "availability; investment remains on nameplate"
                    " capacity."
                )
            ),
        )
