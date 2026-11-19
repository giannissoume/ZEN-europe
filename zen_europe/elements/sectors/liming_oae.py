"""Liming ocean alkalinity enhancement sector."""

from zen_creator import Sector

from zen_europe.elements.carriers.hydrated_lime import HydratedLime
from zen_europe.elements.carriers.limestone import Limestone
from zen_europe.elements.conversion_technologies.lime_ocean_application import (
    LimeOceanApplication,
)
from zen_europe.elements.conversion_technologies.lime_production_ccs import (
    LimeProductionCCS,
)


class LimingOaeSector(Sector):
    """Limestone procurement, production with capture, and marine application."""

    name = "liming_oae"
    required_sectors = [
        "electricity",
        "gas",
        "carbon",
        "truck_transport",
        "passenger_transport",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.elements = [
            Limestone,
            HydratedLime,
            LimeProductionCCS,
            LimeOceanApplication,
        ]
