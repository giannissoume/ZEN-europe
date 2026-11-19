"""Combine production and marine-service inputs for liming OAE."""

from pathlib import Path
from typing import Any

import pandas as pd
from zen_creator import Attribute, DatasetCollection, SourceInformation
from zen_creator.utils.settings import Settings

from zen_europe.datasets.datasets.carrier.ipcc_emission_factors import (
    IPCCEmissionFactors,
)
from zen_europe.datasets.datasets.energy_system.marine_regions_eez import (
    MarineRegionsEez,
)
from zen_europe.datasets.datasets.financial.ECB import ECBDollar2Euro, ECBInflation
from zen_europe.datasets.datasets.technology.desnz_industry_opex import (
    DesnzIndustryOpex,
)
from zen_europe.datasets.datasets.technology.foteinis_hydration import FoteinisHydration
from zen_europe.datasets.datasets.technology.intermodal_charter import IntermodalCharter
from zen_europe.datasets.datasets.technology.jrc_lime_hydration import JrcLimeHydration
from zen_europe.datasets.datasets.technology.kowalczyk_ocean_liming import (
    KowalczykOceanLiming,
)
from zen_europe.datasets.datasets.technology.mitraki_lime_production import (
    MitrakiLimeProduction,
)
from zen_europe.datasets.datasets.technology.pacific_lime_hydrator import (
    PacificLimeHydrator,
)
from zen_europe.datasets.datasets.technology.strefler_marine_allowance import (
    StreflerMarineAllowance,
)
from zen_europe.utils.constants import Constants


class LimingOaeParameters(DatasetCollection):
    """Normalize the integrated plant and chartered application service."""

    name = "liming_oae_parameters"
    HYDRATION_MASS_RATIO = 74.1 / 56.08

    def __init__(self, settings: Settings, source_path: Path | str):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _get_data(self) -> dict[str, Any]:
        return {
            "production": MitrakiLimeProduction(self.source_path),
            "gas_carbon": IPCCEmissionFactors(self.source_path),
            "hydration": FoteinisHydration(self.source_path),
            "water": JrcLimeHydration(self.source_path),
            "hydrator": PacificLimeHydrator(self.source_path),
            "fixed_opex": DesnzIndustryOpex(self.source_path),
            "marine": KowalczykOceanLiming(self.source_path),
            "charter": IntermodalCharter(self.source_path),
            "allowance": StreflerMarineAllowance(self.source_path),
            "areas": MarineRegionsEez(self.source_path),
            "exchange": ECBDollar2Euro(self.source_path),
            "inflation": ECBInflation(self.source_path),
        }

    def _value(self, dataset: str, parameter: str) -> float:
        return self.data[dataset].get_value(parameter)

    def _euro_factor(self, year: int) -> float:
        return self.data["inflation"].get_inflation_rate(
            year, self.settings.time.price_year
        )

    def _dollar_factor(self, year: int) -> float:
        return self.data["exchange"].get_dollar2euro(year) * self._euro_factor(year)

    def _attribute(
        self, element, name: str, value: Any, unit: str | None, description: str
    ) -> Attribute:
        return getattr(element, name).set_data(
            default_value=value,
            unit=unit,
            source=SourceInformation(description=description, metadata=self.metadata),
        )

    def get_production_coefficients(self) -> dict[str, float]:
        """Inputs and credited captured output per tonne dry hydrate."""
        r = self.HYDRATION_MASS_RATIO
        power = (
            sum(
                self._value("production", f"{c}_electricity_kwh_per_t_cao")
                for c in ("kiln", "cpu", "asu")
            )
            / r
        )
        process = self._value("production", "process_co2_t_per_t_cao") / r
        gas_mwh = self._value("production", "gas_gj_per_t_cao") / 3.6 / r
        gas_carbon = float(self.data["gas_carbon"].data.loc["natural_gas"])
        return {
            "limestone": self._value("production", "limestone_t_per_t_cao") / r,
            "natural_gas": gas_mwh / 1000,
            "electricity": (
                (power + self._value("hydration", "electricity_kwh_per_t_hydrate"))
                / 1e6
            ),
            "carbon": (
                (process + gas_mwh * gas_carbon)
                * self._value("production", "capture_fraction")
            ),
        }

    def get_water_m3_per_t(self) -> float:
        """Total hydration-water input, with density approximated as 1 t/m3."""
        return (
            self._value("water", "water_multiplier")
            * self._value("water", "stoichiometric_water_t_per_t_cao")
            / self.HYDRATION_MASS_RATIO
        )

    def get_capex_euro_per_tph(self) -> float:
        """Installed nameplate CAPEX, excluding model financing."""
        plant = 0.0
        for component in ("kiln", "cpu", "asu"):
            rate = self._value("production", f"{component}_interest")
            life = self._value("production", f"{component}_lifetime")
            crf = rate * (1 + rate) ** life / ((1 + rate) ** life - 1)
            plant += self._value("production", f"{component}_annual_charge") / crf
        plant *= (
            Constants.HOURS_PER_YEAR
            / self.HYDRATION_MASS_RATIO
            * self._euro_factor(2025)
        )
        hydrator = (
            self._value("hydrator", "package_usd")
            / self._value("hydrator", "capacity_t_per_h")
            * self._dollar_factor(2025)
        )
        return plant + hydrator

    def get_application_diesel_gwh_per_t(self) -> float:
        """Energy-equivalent diesel: discharge, access and slurry auxiliaries."""
        cfg = self.settings.liming_oae
        hourly = self._value("marine", "fuel_t_per_h") * self._value(
            "marine", "fuel_mwh_per_t"
        )
        discharge = hourly / self._value("marine", "discharge_t_per_h")
        access = hourly * 24 * cfg.access_days / cfg.cargo_t
        slurry = cfg.slurry_kwh_per_t / 1000 / cfg.generator_efficiency
        return (discharge + access + slurry) / 1000

    def get_application_euro_per_t(self) -> float:
        """Charter charge per tonne, excluding endogenous fuel cost."""
        cfg = self.settings.liming_oae
        daily = self._value("charter", "charter_usd_per_day")
        cost = daily / (24 * self._value("marine", "discharge_t_per_h"))
        cost += daily * (cfg.loading_days + cfg.access_days) / cfg.cargo_t
        return cost * self._dollar_factor(2023)

    def get_removal_tco2_per_t(self) -> float:
        """Gross ocean uptake; no extra downstream multiplier."""
        return self._value("marine", "uptake_mol_per_mol") * 44.01 / 74.1

    def get_production_conversion_factor(self, element) -> Attribute:
        coefficients = self.get_production_coefficients()
        units = {
            "limestone": "tproduct/tproduct",
            "natural_gas": "GWh/tproduct",
            "electricity": "GWh/tproduct",
            "carbon": "tCO2/tproduct",
        }
        return self._attribute(
            element,
            "conversion_factor",
            [
                {k: {"default_value": v, "unit": units[k]}}
                for k, v in coefficients.items()
            ],
            None,
            "Mitraki NGOxy-CC inputs are rebased from CaO to dry hydrate by 74.1/56.08;"
            " Foteinis hydration electricity is added. Capture is 90% of calcination"
            " plus fuel CO2, using the existing IPCC natural-gas factor as in baseline"
            " CCS. This inherits the baseline fuel-carbon approximation across gas"
            " supply routes. Captured CO2 enters the carbon network; only storage"
            " earns a permanent-storage credit.",
        )

    def get_production_carbon_intensity(self, element) -> Attribute:
        return self._attribute(
            element,
            "carbon_intensity_technology",
            self._value("production", "process_co2_t_per_t_cao")
            / self.HYDRATION_MASS_RATIO,
            "ton/tproduct",
            "Gross calcination emissions are charged once. Fuel emissions are accounted"
            " by the existing gas system; captured carbon is credited only at storage.",
        )

    def get_production_capex(self, element) -> Attribute:
        return self._attribute(
            element,
            "capex_specific_conversion",
            self.get_capex_euro_per_tph(),
            "Euro/(tproduct/h)",
            "Reverse Mitraki component annuities using their reported rates and"
            " lifetimes; multiply by 8760 and rebase to hydrate output. Add the Pacific"
            " Lime co-located hydration package, assuming 15 tph hydrate output."
            " Convert monetary years with ECB; do not add source annuities again.",
        )

    def get_production_fixed_opex(self, element) -> Attribute:
        return self._attribute(
            element,
            "opex_specific_fixed",
            self.get_capex_euro_per_tph()
            * self._value("fixed_opex", "fixed_opex_fraction"),
            "Euro/(tproduct/h)",
            "DESNZ 2.5% annual fixed-O&M proxy applied to the complete "
            "production CAPEX, including hydration.",
        )

    def get_production_variable_opex(self, element) -> Attribute:
        return self._attribute(
            element,
            "opex_specific_variable",
            self.get_water_m3_per_t()
            * self.settings.liming_oae.water_euro_per_m3
            * self._euro_factor(self.settings.liming_oae.utility_price_year),
            "Euro/tproduct",
            "JRC hydration water is about twice stoichiometric, priced at an assumed "
            f"{self.settings.liming_oae.water_euro_per_m3:g} "
            f"EUR{self.settings.liming_oae.utility_price_year}/m3 and adjusted to "
            "the model price year. No water network, separate ASU/CPU cooling "
            "charge or heat revenue.",
        )

    def get_limestone_price(self, element) -> Attribute:
        return self._attribute(
            element,
            "price_import",
            self.settings.liming_oae.limestone_euro_per_t
            * self._euro_factor(self.settings.liming_oae.utility_price_year),
            "Euro/tproduct",
            "Assumed kiln-ready limestone procurement at "
            f"{self.settings.liming_oae.limestone_euro_per_t:g} "
            f"EUR{self.settings.liming_oae.utility_price_year}/t, adjusted to the "
            "model price year and informed by"
            " Mitraki's 0.02 EUR/kg. Source price-year and delivery boundary are"
            " unclear; no separate quarry, preparation or quarry-to-plant freight"
            " inventory is added.",
        )

    def get_production_lifetime(self, element) -> Attribute:
        return self._attribute(
            element,
            "lifetime",
            self._value("production", "kiln_lifetime"),
            "1",
            "Use the kiln's 20 years for the combined plant; CPU and ASU source lives "
            "are longer. Aggregate replacement follows the existing model convention.",
        )

    def get_application_conversion_factor(self, element) -> Attribute:
        return self._attribute(
            element,
            "conversion_factor",
            [
                {
                    "truck_mileage": {
                        "default_value": self.settings.liming_oae.delivery_km,
                        "unit": "tkm/tproduct",
                    }
                },
                {
                    "diesel": {
                        "default_value": self.get_application_diesel_gwh_per_t(),
                        "unit": "GWh/tproduct",
                    }
                },
            ],
            None,
            f"Assume {self.settings.liming_oae.delivery_km:g} km road delivery. "
            "Marine fuel follows Kowalczyk's inventory with a "
            f"{self.settings.liming_oae.cargo_t:g}-t cargo, "
            f"{self._value('marine', 'discharge_t_per_h'):g} t/h discharge and "
            f"{self.settings.liming_oae.access_days:g} access/return days. Add "
            f"{self.settings.liming_oae.slurry_kwh_per_t:g} kWh/t slurry auxiliaries "
            f"at {self.settings.liming_oae.generator_efficiency:.0%} generator "
            "efficiency. Existing diesel is"
            " an energy-equivalent fuel proxy; road freight is charged separately.",
        )

    def get_application_opex(self, element) -> Attribute:
        return self._attribute(
            element,
            "opex_specific_variable",
            self.get_application_euro_per_t(),
            "Euro/tproduct",
            "Intermodal 2023 charter rate divided by daily discharge "
            f"(24 × {self._value('marine', 'discharge_t_per_h'):g} t/h), plus "
            f"{self.settings.liming_oae.loading_days:g} loading days and "
            f"{self.settings.liming_oae.access_days:g} access days per "
            f"{self.settings.liming_oae.cargo_t:g}-t cargo, converted with ECB. "
            "Fuel is charged through diesel. Dedicated slurry-equipment ownership, "
            "extra labour, port fees and variable waiting/weather costs are excluded.",
        )

    def get_application_carbon_intensity(self, element) -> Attribute:
        return self._attribute(
            element,
            "carbon_intensity_technology",
            -self.get_removal_tco2_per_t(),
            "ton/tproduct",
            "Gross uptake of 1.5 mol CO2/mol Ca(OH)2 is credited once "
            "at application. No uptake delay or extra 0.775 factor; operational "
            "emissions and production/storage accounting remain separate.",
        )

    def get_capacity_limit(self, element, *, production: bool = False) -> Attribute:
        nodes = list(element.model.config.system.set_nodes)
        areas = self.data["areas"].get_area_km2(nodes)
        if production:
            limit = pd.Series(float("inf"), index=areas.index).where(areas > 0, 0.0)
            description = (
                "Production is restricted to coastal model nodes; inland-to-coast lime"
                " trade is not represented."
            )
        else:
            rate = self._value("allowance", "concentration_g_per_m3") * self._value(
                "allowance", "receiving_layer_m"
            )
            limit = (
                areas
                * rate
                * self.settings.liming_oae.eligible_area_fraction
                / Constants.HOURS_PER_YEAR
            )
            description = (
                f"National main-territory marine area times {rate:g} t/km2/year "
                "and an eligible fraction of "
                f"{self.settings.liming_oae.eligible_area_fraction:g}, divided by "
                "8760. The concentration, receiving layer, annual reuse and "
                "eligibility are deployment proxies, not ecological capacity. No"
                " cumulative stock or Mediterranean-specific correction."
            )
        limit.name = "capacity_limit"
        return element.capacity_limit.set_data(
            df=limit,
            unit="tproduct/h",
            source=SourceInformation(description=description, metadata=self.metadata),
        )
