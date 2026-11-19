from zen_creator import Sector

from zen_europe.elements.carriers.biochar import Biochar
from zen_europe.elements.carriers.biochar_for_application import BiocharForApplication
from zen_europe.elements.conversion_technologies.biochar_application import (
    BiocharApplication,
)
from zen_europe.elements.conversion_technologies.biochar_to_application import (
    BiocharToApplication,
)
from zen_europe.elements.conversion_technologies.biochar_to_hard_coal import (
    BiocharToHardCoal,
)
from zen_europe.elements.conversion_technologies.pyrolysis import Pyrolysis


class BiocharCDRSector(Sector):
    """Biochar carbon dioxide removal pathway."""

    name = "biochar_cdr"
    required_sectors = [
        "electricity",
        "district_heating",
        "refining",
        "truck_transport",
        "passenger_transport",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.elements = [
            Pyrolysis,
            BiocharToHardCoal,
            BiocharApplication,
            BiocharToApplication,
            BiocharForApplication,
            Biochar,
        ]
