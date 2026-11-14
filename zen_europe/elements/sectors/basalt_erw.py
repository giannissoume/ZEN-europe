"""Basalt enhanced-rock-weathering sector."""

from zen_creator import Sector

from zen_europe.elements.carriers.basalt import Basalt
from zen_europe.elements.carriers.ground_basalt import GroundBasalt
from zen_europe.elements.conversion_technologies.basalt_application import (
    BasaltApplication,
)
from zen_europe.elements.conversion_technologies.basalt_grinding import BasaltGrinding


class BasaltErwSector(Sector):
    """Simplified basalt enhanced-rock-weathering pathway."""

    name = "basalt_erw"
    required_sectors = ["electricity", "truck_transport", "passenger_transport"]

    def __init__(self) -> None:
        super().__init__()
        self.elements = [
            BasaltGrinding,
            BasaltApplication,
            Basalt,
            GroundBasalt,
        ]
