"""Data loader — loads JSON data files for the game.

Provides functions to load station records, question records, region adjacency
maps, and country configs from the data/ directory.
"""

import json
import os
from typing import Optional

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _load_json(filename: str) -> object:
    """Load and parse a JSON file from the data directory.

    Args:
        filename: Filename (not path) within the data/ directory.

    Returns:
        Parsed JSON object (list or dict).

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    path = os.path.join(_DATA_DIR, filename)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_countries() -> list[dict]:
    """Load the list of supported countries.

    Returns:
        List of country dicts with id, label, and configFile keys.
    """
    return _load_json("countries.json")  # type: ignore[return-value]


def load_config(config_file: str) -> dict:
    """Load a country config file.

    Args:
        config_file: Filename of the config JSON (e.g. "config.uk.json").

    Returns:
        Config dict for the country.
    """
    return _load_json(config_file)  # type: ignore[return-value]


def load_stations(stations_file: str) -> list[dict]:
    """Load station records from a JSON file.

    Args:
        stations_file: Filename of the stations JSON (e.g. "stations.uk.json").

    Returns:
        List of station record dicts.
    """
    return _load_json(stations_file)  # type: ignore[return-value]


def load_questions(questions_file: str) -> list[dict]:
    """Load question records from a JSON file.

    Args:
        questions_file: Filename of the questions JSON (e.g. "questions.uk.json").

    Returns:
        List of question record dicts.
    """
    return _load_json(questions_file)  # type: ignore[return-value]


def load_regions(regions_file: str) -> dict:
    """Load the region adjacency map from a JSON file.

    Args:
        regions_file: Filename of the regions JSON (e.g. "regions.uk.json").

    Returns:
        Dict mapping region names to lists of bordering region names.
    """
    return _load_json(regions_file)  # type: ignore[return-value]


def load_country_data(country_id: str) -> Optional[tuple[dict, list[dict], list[dict], dict]]:
    """Load all data for a given country.

    Resolves the country's config file, then loads stations, questions, and
    regions. The region adjacency map is injected into the config under the
    ``_regions`` key for use by the answer engine.

    Args:
        country_id: The country identifier (e.g. "UK").

    Returns:
        A 4-tuple (config, stations, questions, regions) or None if the
        country_id is not found.
    """
    countries = load_countries()
    country = next((c for c in countries if c["id"] == country_id), None)
    if country is None:
        return None

    config = load_config(country["configFile"])
    stations = load_stations(config["stationsFile"])
    questions = load_questions(config["questionsFile"])
    regions = load_regions(config["regionsFile"])

    # Inject region adjacency into config for the answer engine
    config["_regions"] = regions

    return config, stations, questions, regions
