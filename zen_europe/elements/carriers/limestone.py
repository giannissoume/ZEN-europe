"""Purchased kiln-ready limestone."""

from zen_creator import AssumptionInformation, Attribute, Carrier

from zen_europe.datasets.dataset_collections.liming_oae_parameters import (
    LimingOaeParameters,
)


class Limestone(Carrier):
    """Purchased kiln-ready limestone."""

    name = "limestone"

    def __init__(self, model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_availability_import(self) -> Attribute:
        """Set the purchased-supply boundary."""
        return self.availability_import.set_data(
            default_value=float("inf"),
            unit=self.power_unit,
            source=AssumptionInformation(
                description=(
                    "Unlimited kiln-ready purchased limestone; no quarry resource"
                    " constraint."
                )
            ),
        )

    def _set_carbon_intensity_carrier_import(self) -> Attribute:
        """No upstream inventory is charged on this carrier."""
        return self.carbon_intensity_carrier_import.set_data(
            default_value=0,
            unit="ton/tproduct",
            source=AssumptionInformation(
                description=(
                    "Upstream quarry/preparation emissions are outside the limestone"
                    " procurement boundary."
                )
            ),
        )

    def _set_price_import(self) -> Attribute:
        """Return the kiln-ready procurement proxy."""
        return LimingOaeParameters(self.settings, self.source_path).get_limestone_price(
            self
        )
