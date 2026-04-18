"""Hint engine — generates progressive hints about the hider's station.

Each hint source is a small function that returns a human-readable string or
None if that source is exhausted or unavailable. Hint sources are sampled
randomly from whichever sources have not yet been revealed.

Usage::

    from src.hint_engine import generate_hint

    revealed: list[str] = []
    hint = generate_hint(station, revealed)
    if hint:
        revealed.append(hint["type"])
        print(hint["text"])
"""

import random
from typing import Optional

# ---------------------------------------------------------------------------
# Hint source functions
# ---------------------------------------------------------------------------


def _hint_region(station: dict) -> Optional[str]:
    """Return a region hint for the station.

    Args:
        station: Station record dict.

    Returns:
        A hint string, or None if region is unavailable.
    """
    region = station.get("region", "")
    if not region:
        return None
    return f"The station is in the {region} region."


def _hint_cardinal(station: dict) -> Optional[str]:
    """Return a cardinal direction hint for the station.

    Args:
        station: Station record dict.

    Returns:
        A hint string, or None if cardinal direction is unavailable.
    """
    direction = station.get("cardinalDirection", "")
    if not direction:
        return None
    return f"The station is in the {direction} part of the UK."


def _hint_city(station: dict) -> Optional[str]:
    """Return a closest major city hint for the station.

    Args:
        station: Station record dict.

    Returns:
        A hint string, or None if closest major city is unavailable.
    """
    city = station.get("closestMajorCity", "")
    if not city:
        return None
    return f"The closest major city to the station is {city}."


def _hint_landmark(station: dict) -> Optional[str]:
    """Return a random landmark hint for the station.

    Args:
        station: Station record dict.

    Returns:
        A hint string referencing a nearby landmark, or None if no landmarks
        are available.
    """
    landmarks = station.get("landmarks", [])
    if not landmarks:
        return None
    landmark = random.choice(landmarks)
    return f"A nearby landmark is: {landmark}."


def _hint_postcode_area(station: dict) -> Optional[str]:
    """Return a postcode area hint for the station.

    Args:
        station: Station record dict.

    Returns:
        A hint string with the postcode area letters, or None if unavailable.
    """
    area = station.get("postcodeArea", "")
    if not area:
        return None
    return f"The postcode area starts with: {area}."


def _hint_operator(station: dict) -> Optional[str]:
    """Return a random train operator hint for the station.

    Args:
        station: Station record dict.

    Returns:
        A hint string naming one operator, or None if no operators are listed.
    """
    operators = station.get("operators", [])
    if not operators:
        return None
    op = random.choice(operators)
    return f"The station is served by {op}."


def _hint_name_length(station: dict) -> Optional[str]:
    """Return the station name length as a hint.

    Args:
        station: Station record dict.

    Returns:
        A hint string with the character count.
    """
    name = station.get("name", "")
    if not name:
        return None
    return f"The station name is {len(name)} characters long (including spaces)."


def _hint_first_letter(station: dict) -> Optional[str]:
    """Return the first letter of the station name as a hint.

    Args:
        station: Station record dict.

    Returns:
        A hint string with the first letter.
    """
    name = station.get("name", "")
    if not name:
        return None
    return f"The station name starts with the letter '{name[0].upper()}'."


def _hint_last_letter(station: dict) -> Optional[str]:
    """Return the last letter of the station name as a hint.

    Args:
        station: Station record dict.

    Returns:
        A hint string with the last letter.
    """
    name = station.get("name", "")
    if not name:
        return None
    return f"The station name ends with the letter '{name[-1].upper()}'."


# ---------------------------------------------------------------------------
# Hint source registry
# ---------------------------------------------------------------------------

# Each entry is (type_key, generator_function).
# The type_key is used to track which hints have already been revealed.
_HINT_SOURCES: list[tuple[str, object]] = [
    ("region", _hint_region),
    ("cardinal", _hint_cardinal),
    ("city", _hint_city),
    ("landmark", _hint_landmark),
    ("postcodeArea", _hint_postcode_area),
    ("operator", _hint_operator),
    ("nameLength", _hint_name_length),
    ("firstLetter", _hint_first_letter),
    ("lastLetter", _hint_last_letter),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_hint(
    station: dict,
    revealed_hint_types: list[str],
) -> Optional[dict]:
    """Generate the next hint for a station, avoiding already-revealed types.

    Randomly selects from unrevealed hint sources and returns the first one
    that produces a non-None result. Returns None when all sources are
    exhausted.

    Args:
        station: The hider's station record.
        revealed_hint_types: List of type keys already shown to the seeker.

    Returns:
        A dict ``{"type": str, "text": str}`` or None if exhausted.
    """
    available = [
        (key, fn)
        for key, fn in _HINT_SOURCES
        if key not in revealed_hint_types
    ]
    random.shuffle(available)

    for key, fn in available:
        text = fn(station)  # type: ignore[operator]
        if text is not None:
            return {"type": key, "text": text}

    return None


def remaining_hint_count(station: dict, revealed_hint_types: list[str]) -> int:
    """Return how many hints are still available for a station.

    Args:
        station: The hider's station record.
        revealed_hint_types: List of type keys already shown to the seeker.

    Returns:
        Integer count of hints that can still be revealed.
    """
    available = [
        key for key, fn in _HINT_SOURCES if key not in revealed_hint_types
    ]
    count = 0
    for key in available:
        fn = dict(_HINT_SOURCES)[key]
        if fn(station) is not None:  # type: ignore[operator]
            count += 1
    return count
