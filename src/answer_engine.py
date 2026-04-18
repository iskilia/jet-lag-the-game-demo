"""Answer engine — resolves questions about the hider's station.

Each public resolver receives a hider station dict, a seeker station dict,
the full stations list, and the country config. It returns a dict:

    { "answerable": True, "answer": <value> }
or
    { "answerable": False, "reason": <str> }

The dispatch function ``answer_question`` maps question resolver names to
the correct function.
"""

import re
from typing import Any

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _letter_set(name: str) -> set[str]:
    """Return the set of unique lower-case letters in a station name.

    Args:
        name: Station name string.

    Returns:
        A set of unique lower-case letters (spaces and punctuation excluded).
    """
    return {ch for ch in name.lower() if ch.isalpha()}


def _vowel_set(name: str) -> set[str]:
    """Return the set of vowels present in a station name.

    Args:
        name: Station name string.

    Returns:
        A set containing only the vowels found in the name (lower-case).
    """
    return _letter_set(name) & {"a", "e", "i", "o", "u"}


def _word_in_name(name: str, word: str) -> bool:
    """Test whether a whole word (case-insensitive) appears in a name.

    Args:
        name: Station name string.
        word: The word to search for.

    Returns:
        True if the word appears as a whole word in the name.
    """
    return bool(re.search(rf"\b{re.escape(word)}\b", name, re.IGNORECASE))


def _ok(answer: Any) -> dict:
    """Wrap a successful answer.

    Args:
        answer: The resolved answer value.

    Returns:
        Dict with answerable=True and the answer.
    """
    return {"answerable": True, "answer": answer}


def _unanswerable(reason: str) -> dict:
    """Return an unanswerable result with an explanation.

    Args:
        reason: Human-readable reason the question cannot be answered.

    Returns:
        Dict with answerable=False and the reason.
    """
    return {"answerable": False, "reason": reason}


# ---------------------------------------------------------------------------
# Name-based resolvers (no seeker context needed)
# ---------------------------------------------------------------------------


def first_letter_of_name(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return the first letter of the hider's station name.

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with the first letter as a string.
    """
    return _ok(hider["name"][0].upper())


def last_letter_of_name(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return the last letter of the hider's station name.

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with the last letter as a string.
    """
    return _ok(hider["name"][-1].upper())


def is_single_word(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return yes/no: is the hider's station name a single word?

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    return _ok(len(hider["name"].split()) == 1)


def is_multi_word(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return yes/no: does the hider's station name consist of two or more words?

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    return _ok(len(hider["name"].split()) >= 2)


def name_longer_than_10(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return yes/no: is the hider's station name longer than 10 characters?

    Spaces are included in the character count.

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    return _ok(len(hider["name"]) > 10)


def contains_west_or_east(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return yes/no: does the hider's station name contain "West" or "East"?

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    name = hider["name"]
    return _ok(_word_in_name(name, "West") or _word_in_name(name, "East"))


def contains_north_or_south(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return yes/no: does the hider's station name contain "North" or "South"?

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    name = hider["name"]
    return _ok(_word_in_name(name, "North") or _word_in_name(name, "South"))


def contains_compass_word(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return yes/no: does the hider's name contain a compass/directional word?

    Checks for: North, South, East, West, Upper, Lower, Central.

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    compass_words = ["North", "South", "East", "West", "Upper", "Lower", "Central"]
    name = hider["name"]
    return _ok(any(_word_in_name(name, w) for w in compass_words))


def contains_new(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return yes/no: does the hider's station name contain the word "New"?

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    return _ok(_word_in_name(hider["name"], "New"))


def contains_king_or_queen(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return yes/no: does the hider's station name contain "King" or "Queen"?

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    name = hider["name"]
    return _ok(_word_in_name(name, "King") or _word_in_name(name, "Queen"))


def contains_saint(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return yes/no: does the hider's station name contain "St" (as in Saint)?

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    return _ok(_word_in_name(hider["name"], "St"))


def contains_suffix_word(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return yes/no: does the hider's name contain Street/Road/Junction/Central/Parkway?

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    words = ["Street", "Road", "Junction", "Central", "Parkway"]
    name = hider["name"]
    return _ok(any(_word_in_name(name, w) for w in words))


def contains_park(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return yes/no: does the hider's station name contain the word "Park"?

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    return _ok(_word_in_name(hider["name"], "Park"))


def contains_ampersand(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return yes/no: does the hider's station name contain an "&" symbol?

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    return _ok("&" in hider["name"])


def has_bracketed_qualifier(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return yes/no: does the hider's station name contain a bracketed qualifier?

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    return _ok(bool(re.search(r"\(.*?\)", hider["name"])))


def has_celtic_prefix(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return yes/no: does the hider's name start with a Welsh or Scottish prefix?

    Checks for prefixes: Llan, Aber, Inver, Glen, Bal, Dum, Kil, Pen, Tre, Blaen.

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    prefixes = [
        "Llan", "Aber", "Inver", "Glen", "Bal", "Dum",
        "Kil", "Pen", "Tre", "Blaen",
    ]
    name = hider["name"]
    return _ok(any(name.lower().startswith(p.lower()) for p in prefixes))


# ---------------------------------------------------------------------------
# Letter-sharing resolvers (require seeker context)
# ---------------------------------------------------------------------------


def shares_at_least_2_letters(
    hider: dict, seeker: dict, all_stations: list, config: dict
) -> dict:
    """Return yes/no: does the hider's station share at least 2 letters with the seeker's?

    Compares unique letter sets (case-insensitive, alphabetic characters only).

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    shared = _letter_set(hider["name"]) & _letter_set(seeker["name"])
    return _ok(len(shared) >= 2)


def shares_more_than_3_letters(
    hider: dict, seeker: dict, all_stations: list, config: dict
) -> dict:
    """Return yes/no: does the hider's station share more than 3 letters with the seeker's?

    Compares unique letter sets (case-insensitive, alphabetic characters only).

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    shared = _letter_set(hider["name"]) & _letter_set(seeker["name"])
    return _ok(len(shared) > 3)


def shares_vowels(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return yes/no: does the hider's station share any vowels with the seeker's?

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    return _ok(bool(_vowel_set(hider["name"]) & _vowel_set(seeker["name"])))


# ---------------------------------------------------------------------------
# Geographic resolvers
# ---------------------------------------------------------------------------

_REGION_TO_COUNTRY = {
    "London": "England",
    "South East": "England",
    "South West": "England",
    "East of England": "England",
    "East Midlands": "England",
    "West Midlands": "England",
    "Yorkshire and the Humber": "England",
    "North East": "England",
    "North West": "England",
    "Wales": "Wales",
    "Scotland": "Scotland",
}


def is_in_london(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return yes/no: is the hider's station in London?

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    return _ok(hider["region"] == "London")


def country_of_uk(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return the UK country (England/Wales/Scotland) for the hider's station.

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with the country name string.
    """
    country = _REGION_TO_COUNTRY.get(hider["region"], "Unknown")
    return _ok(country)


def region_name(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return the region name of the hider's station.

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with the region name string.
    """
    return _ok(hider["region"])


def same_region_as_seeker(
    hider: dict, seeker: dict, all_stations: list, config: dict
) -> dict:
    """Return yes/no: is the hider's station in the same region as the seeker's?

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    return _ok(hider["region"] == seeker["region"])


def cardinal_direction(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return the cardinal direction of the hider's station.

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with the cardinal direction string.
    """
    return _ok(hider["cardinalDirection"])


def same_cardinal_as_seeker(
    hider: dict, seeker: dict, all_stations: list, config: dict
) -> dict:
    """Return yes/no: is the hider's cardinal direction the same as the seeker's?

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    return _ok(hider["cardinalDirection"] == seeker["cardinalDirection"])


def regions_border(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return yes/no: does the seeker's region border the hider's region?

    Uses the adjacency data stored in config["_regions"] if available,
    otherwise returns unanswerable.

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict with optional _regions adjacency map.

    Returns:
        Answer dict with True or False, or unanswerable if no region data.
    """
    adjacency = config.get("_regions", {})
    if not adjacency:
        return _unanswerable("Region adjacency data not loaded")
    seeker_neighbours = adjacency.get(seeker["region"], [])
    return _ok(hider["region"] in seeker_neighbours)


def closest_major_city(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return the closest major city to the hider's station.

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with the city name string.
    """
    return _ok(hider["closestMajorCity"])


def same_major_city_as_seeker(
    hider: dict, seeker: dict, all_stations: list, config: dict
) -> dict:
    """Return yes/no: does the hider share the same closest major city as the seeker?

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    return _ok(hider["closestMajorCity"] == seeker["closestMajorCity"])


def city_is_manchester_or_liverpool(
    hider: dict, seeker: dict, all_stations: list, config: dict
) -> dict:
    """Return yes/no: is the hider's closest major city Manchester or Liverpool?

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    return _ok(hider["closestMajorCity"] in {"Manchester", "Liverpool"})


# ---------------------------------------------------------------------------
# Operator resolvers
# ---------------------------------------------------------------------------


def shares_operator(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return yes/no: does the hider share at least one TOC with the seeker?

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    hider_ops = set(hider["operators"])
    seeker_ops = set(seeker["operators"])
    return _ok(bool(hider_ops & seeker_ops))


def has_multiple_operators(
    hider: dict, seeker: dict, all_stations: list, config: dict
) -> dict:
    """Return yes/no: is the hider's station served by more than one TOC?

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    return _ok(len(hider["operators"]) > 1)


def has_intercity_operator(
    hider: dict, seeker: dict, all_stations: list, config: dict
) -> dict:
    """Return yes/no: is the hider served by a long-distance intercity operator?

    The intercity operators list is read from config["intercityOperators"].

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    intercity = set(config.get("intercityOperators", []))
    return _ok(bool(set(hider["operators"]) & intercity))


def has_sleeper_operator(
    hider: dict, seeker: dict, all_stations: list, config: dict
) -> dict:
    """Return yes/no: is the hider's station served by a sleeper train service?

    The sleeper operators list is read from config["sleeperOperators"].

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    sleepers = set(config.get("sleeperOperators", []))
    return _ok(bool(set(hider["operators"]) & sleepers))


# ---------------------------------------------------------------------------
# Unanswerable resolvers
# ---------------------------------------------------------------------------


def is_airport_station(
    hider: dict, seeker: dict, all_stations: list, config: dict
) -> dict:
    """Unanswerable: airport connection data is not in the CSV.

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Unanswerable dict with reason.
    """
    return _unanswerable("Airport connection data not available in station data")


def passes_through_seeker(
    hider: dict, seeker: dict, all_stations: list, config: dict
) -> dict:
    """Unanswerable: route/pathfinding data is not available.

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Unanswerable dict with reason.
    """
    return _unanswerable("Route data not available — rail network graph required")


# ---------------------------------------------------------------------------
# Postcode resolvers
# ---------------------------------------------------------------------------


def same_postcode_area(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    """Return yes/no: do the hider's and seeker's postcode areas start with the same letters?

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    return _ok(hider["postcodeArea"] == seeker["postcodeArea"])


def postcode_starts_with_vowel(
    hider: dict, seeker: dict, all_stations: list, config: dict
) -> dict:
    """Return yes/no: does the first letter of the hider's postcode area start with a vowel?

    Args:
        hider: Hider's station record.
        seeker: Seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        Answer dict with True or False.
    """
    area = hider["postcodeArea"]
    return _ok(bool(area) and area[0].upper() in "AEIOU")


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

RESOLVER_MAP: dict[str, Any] = {
    "firstLetterOfName": first_letter_of_name,
    "lastLetterOfName": last_letter_of_name,
    "isSingleWord": is_single_word,
    "isMultiWord": is_multi_word,
    "nameLongerThan10": name_longer_than_10,
    "containsWestOrEast": contains_west_or_east,
    "containsNorthOrSouth": contains_north_or_south,
    "containsCompassWord": contains_compass_word,
    "containsNew": contains_new,
    "containsKingOrQueen": contains_king_or_queen,
    "containsSaint": contains_saint,
    "containsSuffixWord": contains_suffix_word,
    "containsPark": contains_park,
    "containsAmpersand": contains_ampersand,
    "hasBracketedQualifier": has_bracketed_qualifier,
    "hasCelticPrefix": has_celtic_prefix,
    "sharesAtLeast2Letters": shares_at_least_2_letters,
    "sharesMoreThan3Letters": shares_more_than_3_letters,
    "sharesVowels": shares_vowels,
    "isInLondon": is_in_london,
    "countryOfUK": country_of_uk,
    "regionName": region_name,
    "sameRegionAsSeeker": same_region_as_seeker,
    "cardinalDirection": cardinal_direction,
    "sameCardinalAsSeeker": same_cardinal_as_seeker,
    "regionsBorder": regions_border,
    "closestMajorCity": closest_major_city,
    "sameMajorCityAsSeeker": same_major_city_as_seeker,
    "cityIsManchesterOrLiverpool": city_is_manchester_or_liverpool,
    "sharesOperator": shares_operator,
    "hasMultipleOperators": has_multiple_operators,
    "hasIntercityOperator": has_intercity_operator,
    "hasSleeperOperator": has_sleeper_operator,
    "isAirportStation": is_airport_station,
    "passesThroughSeeker": passes_through_seeker,
    "samePostcodeArea": same_postcode_area,
    "postcodeStartsWithVowel": postcode_starts_with_vowel,
}


def answer_question(
    question_id: str,
    questions: list[dict],
    hider_station: dict,
    seeker_station: dict,
    all_stations: list[dict],
    config: dict,
) -> dict:
    """Dispatch a question to the appropriate resolver function.

    Args:
        question_id: The question's id string (e.g. "q01").
        questions: The full list of question records.
        hider_station: The hider's station record.
        seeker_station: The seeker's station record.
        all_stations: Full list of station records.
        config: Country config dict.

    Returns:
        A dict with 'answerable' (bool) and either 'answer' or 'reason'.

    Raises:
        ValueError: If the question_id is not found or the resolver is unknown.
    """
    question = next((q for q in questions if q["id"] == question_id), None)
    if question is None:
        raise ValueError(f"Unknown question id: {question_id!r}")

    resolver_name = question["resolver"]
    resolver_fn = RESOLVER_MAP.get(resolver_name)
    if resolver_fn is None:
        raise ValueError(f"Unknown resolver: {resolver_name!r}")

    return resolver_fn(hider_station, seeker_station, all_stations, config)
