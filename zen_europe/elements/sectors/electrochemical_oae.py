"""Optional electrochemical ocean alkalinity enhancement sector."""

from zen_creator import Sector

from zen_europe.elements.carriers.olivine import Olivine
from zen_europe.elements.conversion_technologies.seawater_mineralization import (
    SeawaterMineralization,
)


class ElectrochemicalOaeSector(Sector):
    """Purchased olivine and coastal in-plant seawater mineralization."""

    name = "electrochemical_oae"
    required_sectors = ["electricity", "truck_transport", "hydrogen"]

    def __init__(self) -> None:
        super().__init__()
        self.elements = [Olivine, SeawaterMineralization]
