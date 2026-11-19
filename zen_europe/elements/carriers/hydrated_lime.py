"""Dry hydrated lime produced within the model."""

from zen_creator import AssumptionInformation, Attribute, Carrier


class HydratedLime(Carrier):
    """Dry hydrated lime produced within the model."""

    name = "hydrated_lime"

    def __init__(self, model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_availability_import(self) -> Attribute:
        """Set the purchased-supply boundary."""
        return self.availability_import.set_data(
            default_value=0,
            unit=self.power_unit,
            source=AssumptionInformation(
                description=(
                    "Hydrated lime is produced endogenously; independent imports are"
                    " unavailable."
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
                    "Independent hydrate imports are unavailable; removal is credited"
                    " only at marine application."
                )
            ),
        )

    def _set_price_import(self) -> Attribute:
        """No price is needed for unavailable independent imports."""
        return self.price_import.set_data(
            default_value=0,
            unit="Euro/tproduct",
            source=AssumptionInformation(
                description="Hydrated-lime imports are unavailable."
            ),
        )
