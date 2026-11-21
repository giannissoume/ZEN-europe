"""Purchased olivine for anolyte neutralization."""

from zen_creator import AssumptionInformation, Attribute, Carrier

from zen_europe.datasets.dataset_collections.electrochemical_oae_parameters import (
    ElectrochemicalOaeParameters,
)


class Olivine(Carrier):
    """Purchased alkaline rock, with freight charged at the plant."""

    name = "olivine"

    def __init__(self, model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_availability_import(self) -> Attribute:
        return self.availability_import.set_data(
            default_value=float("inf"),
            unit=self.power_unit,
            source=AssumptionInformation(description="Unlimited purchased olivine."),
        )

    def _set_price_import(self) -> Attribute:
        return ElectrochemicalOaeParameters(self.source_path).get_price_import(self)

    def _set_carbon_intensity_carrier_import(self) -> Attribute:
        return self.carbon_intensity_carrier_import.set_data(
            default_value=0,
            unit="ton/tproduct",
            source=AssumptionInformation(
                description=(
                    "Exclude upstream quarry and off-site preparation emissions from "
                    "the purchased-carrier inventory. Account for modelled plant "
                    "electricity and freight emissions separately through their inputs."
                )
            ),
        )
