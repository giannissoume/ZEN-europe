"""Marine Regions cache reuse, explicit refresh and source validation."""

import hashlib
import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest
import requests
from zen_creator import Dataset
from zen_creator.utils.settings import ModelSet, Settings

import zen_europe.datasets.datasets.energy_system.marine_regions_eez as module
from zen_europe.datasets.datasets.energy_system.marine_regions_eez import (
    MarineRegionsEez,
)
from zen_europe.model_creator import DATA_PATH
from zen_europe.settings.cache import clear_caches


@pytest.fixture
def source(monkeypatch):
    path = (
        DATA_PATH
        / "raw_data/01-energy_system/marine_regions"
        / MarineRegionsEez.CACHE_FILE
    )
    raw = path.read_bytes()
    flags = SimpleNamespace(overwrite_marine_regions_eez=False)
    monkeypatch.setattr(module, "get_active_cache_settings", lambda: flags)
    get = Mock(side_effect=AssertionError("Unexpected live network request"))
    monkeypatch.setattr(module.requests, "get", get)
    return SimpleNamespace(raw=raw, payload=json.loads(raw), flags=flags, get=get)


def cache_path(root):
    path = root / "01-energy_system/marine_regions" / MarineRegionsEez.CACHE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def download_response(source, payload):
    response = Mock()
    response.json.return_value = deepcopy(payload)
    source.get.side_effect = None
    source.get.return_value = response
    return response


def test_existing_cache_is_used_without_network_or_changes(tmp_path, source):
    path = cache_path(tmp_path)
    path.write_bytes(source.raw)
    dataset = MarineRegionsEez(tmp_path)
    source.get.assert_not_called()
    assert path.read_bytes() == source.raw
    assert len(dataset.data) == 28
    assert (dataset.data > 0).sum() == 22
    assert dataset.data.sum() == 5019521
    assert hashlib.sha256(source.raw).hexdigest() in dataset.metadata.note


def test_missing_cache_downloads_and_then_reuses_validated_data(tmp_path, source):
    download_response(source, source.payload)
    dataset = MarineRegionsEez(tmp_path)
    source.get.assert_called_once_with(
        MarineRegionsEez.URL,
        params=MarineRegionsEez.REQUEST_PARAMS,
        timeout=MarineRegionsEez.TIMEOUT,
    )
    path = cache_path(tmp_path)
    saved = json.loads(path.read_text())
    assert saved["features"] == source.payload["features"]
    info = saved["zen_europe_source"]
    assert info["url"] == MarineRegionsEez.URL
    assert info["params"] == MarineRegionsEez.REQUEST_PARAMS
    assert info["retrieved_at"] in dataset.metadata.note
    assert hashlib.sha256(path.read_bytes()).hexdigest() in dataset.metadata.note
    Dataset._registries.clear()
    again = MarineRegionsEez(tmp_path)
    assert source.get.call_count == 1
    pd.testing.assert_series_equal(again.data, dataset.data)


def test_explicit_refresh_replaces_cache_with_valid_data(tmp_path, source):
    path = cache_path(tmp_path)
    path.write_bytes(source.raw)
    source.flags.overwrite_marine_regions_eez = True
    changed = deepcopy(source.payload)
    row = next(
        f["properties"]
        for f in changed["features"]
        if f["properties"]["iso_ter1"] == "DEU"
        and f["properties"]["pol_type"] == "200NM"
    )
    row["area_km2"] += 1
    download_response(source, changed)
    dataset = MarineRegionsEez(tmp_path)
    assert dataset.data.loc["DE"] == 56832
    assert dataset.data.loc["CH"] == 0
    assert path.read_bytes() != source.raw
    assert source.get.call_count == 1


@pytest.mark.parametrize("failure", ["timeout", "http", "json"])
def test_failed_refresh_keeps_the_previous_cache(tmp_path, source, failure):
    path = cache_path(tmp_path)
    path.write_bytes(source.raw)
    source.flags.overwrite_marine_regions_eez = True
    response = download_response(source, source.payload)
    if failure == "timeout":
        source.get.side_effect = requests.Timeout("Test timeout")
        error = requests.Timeout
    elif failure == "http":
        response.raise_for_status.side_effect = requests.HTTPError("Test HTTP error")
        error = requests.HTTPError
    else:
        response.json.side_effect = ValueError("Test invalid JSON")
        error = ValueError
    with pytest.raises(error):
        MarineRegionsEez(tmp_path)
    assert path.read_bytes() == source.raw


@pytest.mark.parametrize(
    "invalid",
    ["truncated", "missing", "duplicate", "negative", "infinite", "nan", "wrong_type"],
)
def test_invalid_source_cannot_replace_good_cache(tmp_path, source, invalid):
    path = cache_path(tmp_path)
    path.write_bytes(source.raw)
    source.flags.overwrite_marine_regions_eez = True
    payload = deepcopy(source.payload)
    index = next(
        i
        for i, f in enumerate(payload["features"])
        if f["properties"]["iso_ter1"] == "DEU"
        and f["properties"]["pol_type"] == "200NM"
    )
    if invalid == "truncated":
        payload["numberMatched"] += 1
    elif invalid == "missing":
        payload["features"].pop(index)
        payload["numberMatched"] -= 1
        payload["numberReturned"] -= 1
    elif invalid == "duplicate":
        payload["features"].append(deepcopy(payload["features"][index]))
        payload["numberMatched"] += 1
        payload["numberReturned"] += 1
    elif invalid == "wrong_type":
        payload["type"] = "ExceptionReport"
    else:
        value = {"negative": -1, "infinite": float("inf"), "nan": float("nan")}[invalid]
        payload["features"][index]["properties"]["area_km2"] = value
    download_response(source, payload)
    with pytest.raises(ValueError):
        MarineRegionsEez(tmp_path)
    assert path.read_bytes() == source.raw


@pytest.mark.parametrize("location", ["config", "models"])
def test_refresh_flag_loads_through_normal_configuration(tmp_path, location):
    config = tmp_path / "config.yaml"
    config.write_text(
        "settings:\n  cache:\n    overwrite_marine_regions_eez: "
        + ("true\n" if location == "config" else "false\n")
    )
    patch = None
    if location == "models":
        models = tmp_path / "models.yaml"
        models.write_text(
            "models:\n  refresh:\n    settings:\n      cache:\n       "
            " overwrite_marine_regions_eez: true\n"
        )
        patch = ModelSet.load_from_yaml(models).settings_patch("refresh")
    assert Settings.load_from_yaml(
        config, patch=patch
    ).cache.overwrite_marine_regions_eez


def test_cache_clear_removes_only_downloaded_artifact(tmp_path):
    path = cache_path(tmp_path)
    path.write_text("test")
    note = path.parent / "README.md"
    note.write_text("keep")
    assert path in clear_caches(tmp_path)
    assert not path.exists()
    assert note.read_text() == "keep"
