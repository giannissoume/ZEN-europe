"""Ground basalt carrier produced by grinding."""

from __future__ import annotations

from typing import TYPE_CHECKING

from zen_creator import AssumptionInformation
from zen_creator.elements import Carrier
from zen_creator.utils.attribute import Attribute

if TYPE_CHECKING:
    from zen_creator.model import Model


class GroundBasalt(Carrier):
    """Ground basalt produced endogenously for field application."""

    name: str = "ground_basalt"

    def __init__(self, model: Model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_availability_import(self) -> Attribute:
        """Do not allow independent ground-basalt imports."""
        attr = self.availability_import
        return attr.set_data(
            default_value=0,
            unit=self.power_unit,
            source=AssumptionInformation(
                description=(
                    "Ground basalt is produced endogenously by basalt "
                    "grinding. Independent imports are not available."
                ),
            ),
        )

    def _set_price_import(self) -> Attribute:
        """Set the unused import price to zero."""
        attr = self.price_import
        return attr.set_data(
            default_value=0,
            unit="Euro/tproduct",
            source=AssumptionInformation(
                description=(
                    "The ground-basalt import price is zero because "
                    "independent imports are not available."
                ),
            ),
        )

    def _set_carbon_intensity_carrier_import(self) -> Attribute:
        """Set the unused import carbon intensity to zero."""
        attr = self.carbon_intensity_carrier_import
        return attr.set_data(
            default_value=0,
            unit="ton/tproduct",
            source=AssumptionInformation(
                description=(
                    "The ground-basalt import carbon intensity is zero "
                    "because independent imports are not available. The unit "
                    "ton/tproduct matches cement and zen-garden's "
                    "emissions-[mass] convention."
                ),
            ),
        )
