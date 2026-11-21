"""Electrolytic seawater mineralization with atmospheric uptake inside the plant."""

from zen_creator import AssumptionInformation, Attribute, ConversionTechnology

from zen_europe.datasets.dataset_collections.electrochemical_oae_parameters import (
    ElectrochemicalOaeParameters,
)


class SeawaterMineralization(ConversionTechnology):
    """Bundled electrolysis, carbonation, acid/effluent treatment and H₂ recovery."""

    name = "seawater_mineralization"

    def __init__(self, model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    def _parameters(self) -> ElectrochemicalOaeParameters:
        return ElectrochemicalOaeParameters(self.source_path)

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["olivine"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute(
            "input_carrier",
            default_value=["olivine", "electricity", "truck_mileage"],
            element=self,
        )

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["hydrogen"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return self._parameters().get_conversion_factor(self)

    def _set_carbon_intensity_technology(self) -> Attribute:
        return self._parameters().get_carbon_intensity(self)

    def _set_capacity_limit(self) -> Attribute:
        return self._parameters().get_capacity_limit(self)

    def _set_lifetime(self) -> Attribute:
        return self.lifetime.set_data(
            default_value=self.settings.electrochemical_oae.plant_lifetime_years,
            source=AssumptionInformation(description="Assumed aggregate plant life."),
        )

    def _set_capex_specific_conversion(self) -> Attribute:
        return self._parameters().get_capex(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        return self._parameters().get_fixed_opex(self)

    def _set_opex_specific_variable(self) -> Attribute:
        return self.opex_specific_variable.set_data(
            default_value=0,
            unit="Euro/tproduct",
            source=AssumptionInformation(
                description="Use aggregate fixed O&M and explicit input purchases."
            ),
        )

    def _set_max_load(self) -> Attribute:
        return self._parameters().get_max_load(self)
