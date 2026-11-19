"""Selected European national marine areas from Marine Regions."""

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from zen_creator import Dataset, MetaData

from zen_europe.settings.cache import get_active_cache_settings


class MarineRegionsEez(Dataset[pd.Series]):
    """Cached country marine areas, excluding separately listed remote territories."""

    name = "marine_regions_eez"
    CACHE_FILE = "eez-attributes.json"
    URL = "https://geo.vliz.be/geoserver/MarineRegions/ows"
    REQUEST_PARAMS = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": "MarineRegions:eez",
        "outputFormat": "application/json",
        "propertyName": (
            "mrgid,geoname,pol_type,territory1,territory2,territory3,"
            "iso_ter1,iso_ter2,iso_ter3,iso_sov1,iso_sov2,iso_sov3,area_km2"
        ),
        "count": 2000,
    }
    TIMEOUT = 60
    COUNTRIES = dict(
        zip(
            "BE BG DE DK EE EL ES FI FR HR IE IT LT LV NL NO PL PT RO SE SI UK".split(),
            "BEL BGR DEU DNK EST GRC ESP FIN FRA HRV IRL ITA LTU LVA NLD NOR POL PRT"
            " ROU SWE SVN GBR".split(),
            strict=True,
        )
    )
    LANDLOCKED = {"AT", "CH", "CZ", "HU", "LU", "SK"}

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Maritime Boundaries and Exclusive Economic Zones (200NM)",
            author=["Flanders Marine Institute"],
            publication="Marine Regions",
            publication_year=2023,
            doi="10.14284/632",
            url="https://www.marineregions.org/sources.php",
            note=(
                "Cached WFS attributes, linked to the provider's version-12 citation;"
                " the live layer is not version-pinned. Main-territory 200NM features"
                " only; separate remote territories, joint regimes and claim features"
                " excluded. Provider geodetic areas include internal/archipelagic"
                " waters. Area is a deployment proxy, not an ecological suitability"
                " map. The cache is downloaded if missing; explicit refresh uses"
                " overwrite_marine_regions_eez."
            ),
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path is required for the EEZ cache.")
        path = Path(self.source_path) / "01-energy_system/marine_regions"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _set_data(self) -> pd.Series:
        cache_path = self.path / self.CACHE_FILE
        overwrite = get_active_cache_settings().overwrite_marine_regions_eez
        if cache_path.exists() and not overwrite:
            raw = cache_path.read_bytes()
            payload = json.loads(raw)
            areas = self._parse_areas(payload)
        else:
            response = requests.get(
                self.URL, params=self.REQUEST_PARAMS, timeout=self.TIMEOUT
            )
            response.raise_for_status()
            payload = response.json()
            # Validate before replacing any existing good cache.
            areas = self._parse_areas(payload)
            payload["zen_europe_source"] = {
                "url": self.URL,
                "params": self.REQUEST_PARAMS,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }
            raw = (json.dumps(payload, allow_nan=False) + "\n").encode()
            self._write_cache(cache_path, raw)
        provenance = payload.get("zen_europe_source", {})
        timestamp = provenance.get(
            "retrieved_at", payload.get("timeStamp", "unrecorded")
        )
        self.metadata.note += (
            f" Snapshot timestamp: {timestamp}; "
            f"SHA256: {hashlib.sha256(raw).hexdigest()}."
        )
        return areas

    @staticmethod
    def _write_cache(path: Path, raw: bytes) -> None:
        """Replace the whole cache atomically, including retrieval provenance."""
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(raw)
            os.replace(temporary, path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    @classmethod
    def _parse_areas(cls, payload: dict[str, Any]) -> pd.Series:
        """Validate a complete source response and select the national areas."""
        if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
            raise ValueError(
                "Marine Regions did not return a GeoJSON FeatureCollection."
            )
        features = payload.get("features")
        if not isinstance(features, list) or not features:
            raise ValueError("Marine Regions returned no feature records.")
        try:
            matched = int(payload["numberMatched"])
            returned = int(payload["numberReturned"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "Marine Regions response has invalid feature counts."
            ) from exc
        if matched != len(features) or returned != len(features):
            raise ValueError(
                "Marine Regions response is incomplete; no cache was replaced."
            )
        properties = [f.get("properties", {}) for f in features]
        areas = {code: 0.0 for code in cls.LANDLOCKED}
        for code, iso in cls.COUNTRIES.items():
            selected = [
                p
                for p in properties
                if p.get("iso_ter1") == iso and p.get("pol_type") == "200NM"
            ]
            if len(selected) != 1:
                raise ValueError(f"Missing or ambiguous main-territory EEZ: {code}")
            try:
                area = float(selected[0]["area_km2"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Invalid marine area: {code}") from exc
            if not isfinite(area) or area <= 0:
                raise ValueError(f"Invalid marine area: {code}")
            areas[code] = area
        return pd.Series(areas, name="area_km2").rename_axis("node")

    def get_area_km2(self, nodes: list[str]) -> pd.Series:
        """Return selected model-node areas, failing on unsupported countries."""
        missing = set(nodes) - set(self.data.index)
        if missing:
            raise ValueError(f"Unsupported marine-area countries: {sorted(missing)}")
        return self.data.loc[nodes].copy()
