"""Chartered marine application of dry hydrated lime."""

from zen_creator import AssumptionInformation, Attribute, ConversionTechnology

from zen_europe.datasets.dataset_collections.liming_oae_parameters import (
    LimingOaeParameters,
)


class LimeOceanApplication(ConversionTechnology):
    """Mix and discharge hydrate with immediate gross uptake."""

    name = "lime_ocean_application"

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
            default_value=["hydrated_lime", "truck_mileage", "diesel"],
            element=self,
        )

    def _set_output_carrier(self) -> Attribute:
        """Set the output flows."""
        return Attribute(name="output_carrier", default_value=[], element=self)

    def _set_conversion_factor(self) -> Attribute:
        """Return the source-normalized flow coefficients."""
        return self._parameters().get_application_conversion_factor(self)

    def _set_carbon_intensity_technology(self) -> Attribute:
        """Credit gross ocean uptake once at application."""
        return self._parameters().get_application_carbon_intensity(self)

    def _set_lifetime(self) -> Attribute:
        """Maintain service availability across the horizon."""
        return self.lifetime.set_data(
            default_value=100,
            source=AssumptionInformation(
                description=(
                    "100-year service bookkeeping life; vessel ownership is charged"
                    " through charter, not investment."
                )
            ),
        )

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
        """Apply the national marine-area allowance."""
        return self._parameters().get_capacity_limit(self, production=False)

    def _set_capex_specific_conversion(self) -> Attribute:
        """Vessel ownership is charged through charter."""
        return self.capex_specific_conversion.set_data(
            default_value=0,
            unit="Euro/(tproduct/h)",
            source=AssumptionInformation(
                description=(
                    "Charter includes ordinary vessel ownership. Dedicated"
                    " slurry-equipment costs are excluded."
                )
            ),
        )

    def _set_opex_specific_fixed(self) -> Attribute:
        """Vessel ownership is charged through charter."""
        return self.opex_specific_fixed.set_data(
            default_value=0,
            unit="Euro/(tproduct/h)",
            source=AssumptionInformation(
                description=(
                    "Charter includes ordinary vessel ownership. Dedicated"
                    " slurry-equipment costs are excluded."
                )
            ),
        )

    def _set_opex_specific_variable(self) -> Attribute:
        """Return the normalized cost attribute."""
        return self._parameters().get_application_opex(self)

    def _set_max_load(self) -> Attribute:
        """Annual service allowance uses all 8760 hours."""
        return self.max_load.set_data(
            default_value=1,
            source=AssumptionInformation(
                description=(
                    "The service capacity is the annual allowance divided by 8760."
                )
            ),
        )
