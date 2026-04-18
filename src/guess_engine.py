"""Guess engine — checks seeker guesses against the hider's station.

Normalises both the input and station names before comparing. If no exact
match is found, computes Levenshtein distance to the hider's station and
returns a suggestion if the distance is <= 2.

Usage::

    from src.guess_engine import check_guess

    result = check_guess("london paddington", hider_station, all_stations)
    # {"correct": True}
    # or {"correct": False}
    # or {"correct": False, "suggestion": "London Paddington"}
"""

import re

# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------


def normalise(text: str) -> str:
    """Normalise a station name or guess for comparison.

    Steps:
      1. Strip leading/trailing whitespace.
      2. Lowercase.
      3. Collapse internal whitespace to a single space.
      4. Strip punctuation (keep alphanumeric and spaces).

    Args:
        text: Raw input string.

    Returns:
        Normalised string.
    """
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return text


# ---------------------------------------------------------------------------
# Levenshtein distance
# ---------------------------------------------------------------------------


def levenshtein(a: str, b: str) -> int:
    """Compute the Levenshtein edit distance between two strings.

    Uses dynamic programming with O(min(|a|, |b|)) space.

    Args:
        a: First string.
        b: Second string.

    Returns:
        Integer edit distance.
    """
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    # a is now the longer string
    prev_row = list(range(len(b) + 1))
    for i, char_a in enumerate(a):
        curr_row = [i + 1]
        for j, char_b in enumerate(b):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (char_a != char_b)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_guess(
    input_text: str,
    hider_station: dict,
    all_stations: list[dict],
) -> dict:
    """Check whether the seeker's guess matches the hider's station.

    Normalises both sides before comparison. If the normalised guess exactly
    matches the hider's normalised name, returns ``{"correct": True}``.

    Otherwise computes Levenshtein distance between the normalised guess and
    the normalised hider name. If the distance is <= 2, returns
    ``{"correct": False, "suggestion": "<original name>"}`` so the UI can
    offer a "Did you mean?" prompt. The seeker must confirm — the suggestion
    is not auto-accepted.

    Args:
        input_text: The raw text typed by the seeker.
        hider_station: The hider's station record.
        all_stations: Full list of station records (unused but kept for API
            symmetry with other engines).

    Returns:
        A dict with ``"correct": bool`` and an optional ``"suggestion": str``.
    """
    normalised_input = normalise(input_text)
    normalised_hider = normalise(hider_station["name"])

    if normalised_input == normalised_hider:
        return {"correct": True}

    distance = levenshtein(normalised_input, normalised_hider)
    if distance <= 2:
        return {"correct": False, "suggestion": hider_station["name"]}

    return {"correct": False}
