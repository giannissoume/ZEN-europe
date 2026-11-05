from __future__ import annotations

from typing import TYPE_CHECKING

from zen_creator import AssumptionInformation
from zen_creator.elements import Carrier
from zen_creator.utils.attribute import Attribute

if TYPE_CHECKING:
    from zen_creator.model import Model


class Biochar(Carrier):
    """Biochar carrier class."""

    name: str = "biochar"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_availability_import(self) -> Attribute:
        """Do not allow external biochar imports."""
        attr = self.availability_import
        return attr.set_data(
            default_value=0,
            unit=self.power_unit,
            source=AssumptionInformation(
                description=(
                    "Biochar is produced endogenously by pyrolysis; external "
                    "biochar imports are not considered."
                ),
            ),
        )

    def _set_price_import(self) -> Attribute:
        """Set the unused import price to zero."""
        attr = self.price_import
        return attr.set_data(
            default_value=0,
            unit="Euro/MWh",
            source=AssumptionInformation(
                description=(
                    "The biochar import price is set to zero because external "
                    "biochar imports are not available."
                ),
            ),
        )

    def _set_carbon_intensity_carrier_import(self) -> Attribute:
        """Set the unused import carbon intensity to zero."""
        attr = self.carbon_intensity_carrier_import
        return attr.set_data(
            default_value=0,
            unit="ton/MWh",
            source=AssumptionInformation(
                description=(
                    "The biochar import carbon intensity is set to zero because "
                    "external biochar imports are not available."
                ),
            ),
        )
