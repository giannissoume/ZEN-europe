"""Purchased basalt carrier."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from zen_creator import AssumptionInformation
from zen_creator.elements import Carrier
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.basalt_erw_parameters import (
    BasaltErwParameters,
)

if TYPE_CHECKING:
    from zen_creator.model import Model


class Basalt(Carrier):
    """Purchased basalt rock before grinding."""

    name: str = "basalt"

    def __init__(self, model: Model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    def _parameters(self) -> BasaltErwParameters:
        return BasaltErwParameters(settings=self.settings, source_path=self.source_path)

    def _set_availability_import(self) -> Attribute:
        """Allow unlimited basalt purchases."""
        attr = self.availability_import
        return attr.set_data(
            default_value=np.inf,
            unit=self.power_unit,
            source=AssumptionInformation(
                description=(
                    "Basalt is purchased from outside the model. Import "
                    "availability is unlimited."
                ),
            ),
        )

    def _set_price_import(self) -> Attribute:
        """Return the NETL purchase price in model euros."""
        return self._parameters().get_basalt_price_import(self)

    def _set_carbon_intensity_carrier_import(self) -> Attribute:
        """Exclude upstream quarry emissions by the model boundary."""
        attr = self.carbon_intensity_carrier_import
        return attr.set_data(
            default_value=0,
            unit="ton/tproduct",
            source=AssumptionInformation(
                description=(
                    "Upstream quarry emissions are excluded by the agreed "
                    "model boundary. The import carbon intensity of basalt "
                    "is therefore zero. The purchase price is still included. "
                    "The unit ton/tproduct matches cement and zen-garden's "
                    "emissions-[mass] convention."
                ),
            ),
        )
