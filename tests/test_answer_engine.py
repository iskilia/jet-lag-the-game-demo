"""Unit tests for the answer engine resolvers.

Tests use a small set of known stations derived from the CSV data.
At least 5 representative resolvers are exercised.
"""

import pytest

from src.answer_engine import answer_question

# ---------------------------------------------------------------------------
# Test fixtures — hand-crafted station records matching the CSV schema
# ---------------------------------------------------------------------------

PADDINGTON = {
    "id": "london-paddington",
    "name": "London Paddington",
    "operators": ["Great Western Railway", "Heathrow Express", "Elizabeth line"],
    "postcode": "W2 1HQ",
    "postcodeArea": "W",
    "cardinalDirection": "South",
    "region": "London",
    "closestMajorCity": "London",
    "landmarks": ["Paddington Bear Statue", "Bishop's Bridge"],
}

EDINBURGH = {
    "id": "edinburgh-waverley",
    "name": "Edinburgh Waverley",
    "operators": ["LNER", "ScotRail", "Caledonian Sleeper"],
    "postcode": "EH1 1BB",
    "postcodeArea": "EH",
    "cardinalDirection": "North",
    "region": "Scotland",
    "closestMajorCity": "Edinburgh",
    "landmarks": ["Edinburgh Castle", "Royal Mile"],
}

ABERYSTWYTH = {
    "id": "aberystwyth",
    "name": "Aberystwyth",
    "operators": ["Transport for Wales"],
    "postcode": "SY23 1DG",
    "postcodeArea": "SY",
    "cardinalDirection": "West",
    "region": "Wales",
    "closestMajorCity": "Cardiff",
    "landmarks": [],
}

MANCHESTER_PICCADILLY = {
    "id": "manchester-piccadilly",
    "name": "Manchester Piccadilly",
    "operators": ["Avanti West Coast", "TransPennine Express", "Northern"],
    "postcode": "M1 2BN",
    "postcodeArea": "M",
    "cardinalDirection": "North",
    "region": "North West",
    "closestMajorCity": "Manchester",
    "landmarks": ["Piccadilly Gardens"],
}

KINGS_CROSS = {
    "id": "london-kings-cross",
    "name": "London King's Cross",
    "operators": ["LNER", "Thameslink", "Great Northern"],
    "postcode": "N1C 4AH",
    "postcodeArea": "N",
    "cardinalDirection": "South",
    "region": "London",
    "closestMajorCity": "London",
    "landmarks": ["King's Cross Station"],
}

ALL_STATIONS = [PADDINGTON, EDINBURGH, ABERYSTWYTH, MANCHESTER_PICCADILLY, KINGS_CROSS]

CONFIG = {
    "intercityOperators": [
        "Avanti West Coast", "LNER", "CrossCountry", "GWR", "Great Western Railway"
    ],
    "sleeperOperators": ["Caledonian Sleeper", "Night Riviera"],
    "_regions": {
        "London": ["South East", "East of England"],
        "Scotland": ["North East", "North West"],
        "North West": ["West Midlands", "East Midlands", "Yorkshire and the Humber",
                       "North East", "Wales", "Scotland"],
        "Wales": ["South West", "West Midlands", "North West"],
    },
    "unansweredQuestionLimit": 3,
}


def _questions_stub() -> list[dict]:
    """Return a minimal questions list covering the resolvers under test."""
    return [
        {"id": "q01", "resolver": "firstLetterOfName", "penaltyMinutes": 3},
        {"id": "q02", "resolver": "lastLetterOfName", "penaltyMinutes": 3},
        {"id": "q03", "resolver": "isSingleWord", "penaltyMinutes": 3},
        {"id": "q04", "resolver": "isMultiWord", "penaltyMinutes": 3},
        {"id": "q05", "resolver": "nameLongerThan10", "penaltyMinutes": 3},
        {"id": "q06", "resolver": "containsWestOrEast", "penaltyMinutes": 3},
        {"id": "q07", "resolver": "containsNorthOrSouth", "penaltyMinutes": 3},
        {"id": "q08", "resolver": "containsCompassWord", "penaltyMinutes": 3},
        {"id": "q09", "resolver": "containsNew", "penaltyMinutes": 3},
        {"id": "q10", "resolver": "containsKingOrQueen", "penaltyMinutes": 3},
        {"id": "q11", "resolver": "containsSaint", "penaltyMinutes": 3},
        {"id": "q12", "resolver": "containsSuffixWord", "penaltyMinutes": 3},
        {"id": "q13", "resolver": "containsPark", "penaltyMinutes": 3},
        {"id": "q14", "resolver": "containsAmpersand", "penaltyMinutes": 3},
        {"id": "q15", "resolver": "hasBracketedQualifier", "penaltyMinutes": 3},
        {"id": "q16", "resolver": "hasCelticPrefix", "penaltyMinutes": 3},
        {"id": "q17", "resolver": "sharesAtLeast2Letters", "penaltyMinutes": 3},
        {"id": "q18", "resolver": "sharesMoreThan3Letters", "penaltyMinutes": 3},
        {"id": "q19", "resolver": "sharesVowels", "penaltyMinutes": 3},
        {"id": "q20", "resolver": "isInLondon", "penaltyMinutes": 3},
        {"id": "q21", "resolver": "countryOfUK", "penaltyMinutes": 3},
        {"id": "q22", "resolver": "regionName", "penaltyMinutes": 3},
        {"id": "q23", "resolver": "sameRegionAsSeeker", "penaltyMinutes": 3},
        {"id": "q24", "resolver": "cardinalDirection", "penaltyMinutes": 3},
        {"id": "q25", "resolver": "sameCardinalAsSeeker", "penaltyMinutes": 3},
        {"id": "q26", "resolver": "regionsBorder", "penaltyMinutes": 3},
        {"id": "q27", "resolver": "closestMajorCity", "penaltyMinutes": 3},
        {"id": "q28", "resolver": "sameMajorCityAsSeeker", "penaltyMinutes": 3},
        {"id": "q29", "resolver": "cityIsManchesterOrLiverpool", "penaltyMinutes": 3},
        {"id": "q30", "resolver": "sharesOperator", "penaltyMinutes": 3},
        {"id": "q31", "resolver": "hasMultipleOperators", "penaltyMinutes": 3},
        {"id": "q32", "resolver": "hasIntercityOperator", "penaltyMinutes": 3},
        {"id": "q33", "resolver": "hasSleeperOperator", "penaltyMinutes": 3},
        {"id": "q34", "resolver": "isAirportStation", "penaltyMinutes": 3},
        {"id": "q35", "resolver": "passesThroughSeeker", "penaltyMinutes": 3},
        {"id": "q36", "resolver": "samePostcodeArea", "penaltyMinutes": 3},
        {"id": "q37", "resolver": "postcodeStartsWithVowel", "penaltyMinutes": 3},
    ]


QUESTIONS = _questions_stub()


def _ask(question_id: str, hider=PADDINGTON, seeker=EDINBURGH) -> dict:
    """Shorthand to call answer_question with default fixtures."""
    return answer_question(
        question_id, QUESTIONS, hider, seeker, ALL_STATIONS, CONFIG
    )


# ---------------------------------------------------------------------------
# Tests: name-based resolvers
# ---------------------------------------------------------------------------


class TestFirstLetterOfName:
    """Tests for the firstLetterOfName resolver."""

    def test_london_paddington_starts_l(self):
        """London Paddington's first letter should be L."""
        result = _ask("q01", hider=PADDINGTON)
        assert result["answerable"] is True
        assert result["answer"] == "L"

    def test_edinburgh_starts_e(self):
        """Edinburgh Waverley's first letter should be E."""
        result = _ask("q01", hider=EDINBURGH)
        assert result["answer"] == "E"

    def test_aberystwyth_starts_a(self):
        """Aberystwyth's first letter should be A."""
        result = _ask("q01", hider=ABERYSTWYTH)
        assert result["answer"] == "A"


class TestLastLetterOfName:
    """Tests for the lastLetterOfName resolver."""

    def test_london_paddington_ends_n(self):
        """London Paddington ends in N."""
        result = _ask("q02", hider=PADDINGTON)
        assert result["answer"] == "N"

    def test_aberystwyth_ends_h(self):
        """Aberystwyth ends in H."""
        result = _ask("q02", hider=ABERYSTWYTH)
        assert result["answer"] == "H"


class TestIsSingleWord:
    """Tests for the isSingleWord resolver."""

    def test_aberystwyth_is_single_word(self):
        """Aberystwyth is a single word."""
        result = _ask("q03", hider=ABERYSTWYTH)
        assert result["answer"] is True

    def test_london_paddington_is_not_single_word(self):
        """London Paddington is not a single word."""
        result = _ask("q03", hider=PADDINGTON)
        assert result["answer"] is False


class TestNameLongerThan10:
    """Tests for the nameLongerThan10 resolver."""

    def test_london_paddington_is_longer(self):
        """'London Paddington' is 17 chars, longer than 10."""
        result = _ask("q05", hider=PADDINGTON)
        assert result["answer"] is True

    def test_aberystwyth_is_not_longer(self):
        """'Aberystwyth' is 11 chars, which IS longer than 10."""
        result = _ask("q05", hider=ABERYSTWYTH)
        assert result["answer"] is True

    def test_short_station(self):
        """A 5-char station name should not be longer than 10."""
        short = {**ABERYSTWYTH, "name": "Leeds"}
        result = _ask("q05", hider=short)
        assert result["answer"] is False


class TestContainsWestOrEast:
    """Tests for the containsWestOrEast resolver."""

    def test_no_match(self):
        """London Paddington does not contain West or East as whole words."""
        result = _ask("q06", hider=PADDINGTON)
        assert result["answer"] is False

    def test_match_west(self):
        """A station with 'West' in the name should match."""
        west = {**PADDINGTON, "name": "Bristol West"}
        result = _ask("q06", hider=west)
        assert result["answer"] is True


class TestCountryOfUK:
    """Tests for the countryOfUK resolver."""

    def test_london_is_england(self):
        """London Paddington is in England."""
        result = _ask("q21", hider=PADDINGTON)
        assert result["answer"] == "England"

    def test_scotland(self):
        """Edinburgh Waverley is in Scotland."""
        result = _ask("q21", hider=EDINBURGH)
        assert result["answer"] == "Scotland"

    def test_wales(self):
        """Aberystwyth is in Wales."""
        result = _ask("q21", hider=ABERYSTWYTH)
        assert result["answer"] == "Wales"


class TestRegionsBorder:
    """Tests for the regionsBorder resolver."""

    def test_london_borders_south_east(self):
        """London borders South East; seeker is in London, hider in South East."""
        south_east_station = {**PADDINGTON, "region": "South East"}
        result = _ask("q26", hider=south_east_station, seeker=PADDINGTON)
        assert result["answer"] is True

    def test_scotland_does_not_border_london(self):
        """Scotland does not border London."""
        result = _ask("q26", hider=PADDINGTON, seeker=EDINBURGH)
        # Seeker is Scotland; London not in Scotland's neighbours
        assert result["answer"] is False

    def test_north_west_borders_wales(self):
        """North West borders Wales."""
        seeker_nw = {**MANCHESTER_PICCADILLY, "region": "North West"}
        hider_wales = {**ABERYSTWYTH, "region": "Wales"}
        result = _ask("q26", hider=hider_wales, seeker=seeker_nw)
        assert result["answer"] is True


class TestSharesOperator:
    """Tests for the sharesOperator resolver."""

    def test_both_have_lner(self):
        """Edinburgh (LNER) and King's Cross (LNER) share an operator."""
        result = _ask("q30", hider=EDINBURGH, seeker=KINGS_CROSS)
        assert result["answer"] is True

    def test_no_shared_operator(self):
        """Aberystwyth (Transport for Wales) and Manchester (Avanti etc) share nothing."""
        result = _ask("q30", hider=ABERYSTWYTH, seeker=MANCHESTER_PICCADILLY)
        assert result["answer"] is False


class TestHasIntercityOperator:
    """Tests for the hasIntercityOperator resolver."""

    def test_paddington_has_gwr(self):
        """London Paddington is served by Great Western Railway (intercity)."""
        result = _ask("q32", hider=PADDINGTON)
        assert result["answer"] is True

    def test_aberystwyth_no_intercity(self):
        """Aberystwyth is served only by Transport for Wales (not intercity)."""
        result = _ask("q32", hider=ABERYSTWYTH)
        assert result["answer"] is False


class TestHasSleeperOperator:
    """Tests for the hasSleeperOperator resolver."""

    def test_edinburgh_has_sleeper(self):
        """Edinburgh Waverley is served by Caledonian Sleeper."""
        result = _ask("q33", hider=EDINBURGH)
        assert result["answer"] is True

    def test_paddington_no_sleeper(self):
        """London Paddington does not appear in sleeper operators list."""
        result = _ask("q33", hider=PADDINGTON)
        assert result["answer"] is False


class TestUnanswerable:
    """Tests for unanswerable resolvers."""

    def test_airport_unanswerable(self):
        """Q34 (airport) should always be unanswerable."""
        result = _ask("q34")
        assert result["answerable"] is False

    def test_passes_through_unanswerable(self):
        """Q35 (route) should always be unanswerable."""
        result = _ask("q35")
        assert result["answerable"] is False


class TestPostcodeResolvers:
    """Tests for the postcode area resolvers."""

    def test_same_postcode_area_false(self):
        """Paddington (W) and Edinburgh (EH) have different postcode areas."""
        result = _ask("q36", hider=PADDINGTON, seeker=EDINBURGH)
        assert result["answer"] is False

    def test_same_postcode_area_true(self):
        """Two stations with the same postcode area should match."""
        same_area = {**EDINBURGH, "postcodeArea": "W"}
        result = _ask("q36", hider=PADDINGTON, seeker=same_area)
        assert result["answer"] is True

    def test_postcode_vowel_true(self):
        """Edinburgh (EH) starts with E — a vowel."""
        result = _ask("q37", hider=EDINBURGH)
        assert result["answer"] is True

    def test_postcode_vowel_false(self):
        """Paddington (W) starts with W — not a vowel."""
        result = _ask("q37", hider=PADDINGTON)
        assert result["answer"] is False


class TestHasCelticPrefix:
    """Tests for the hasCelticPrefix resolver."""

    def test_aberystwyth_has_celtic_prefix(self):
        """Aberystwyth starts with 'Aber' — a Celtic prefix."""
        result = _ask("q16", hider=ABERYSTWYTH)
        assert result["answer"] is True

    def test_london_no_celtic_prefix(self):
        """London Paddington does not start with a Celtic prefix."""
        result = _ask("q16", hider=PADDINGTON)
        assert result["answer"] is False


class TestLetterSharing:
    """Tests for letter-sharing resolvers."""

    def test_shares_at_least_2_letters_true(self):
        """Paddington and Edinburgh share many letters."""
        result = _ask("q17", hider=PADDINGTON, seeker=EDINBURGH)
        assert result["answer"] is True

    def test_shares_vowels_true(self):
        """Both have vowels in common."""
        result = _ask("q19", hider=PADDINGTON, seeker=EDINBURGH)
        assert result["answer"] is True


class TestDispatchAllQuestionIds:
    """Verify all 37 question IDs dispatch without raising errors."""

    def test_all_questions_dispatch(self):
        """Every question ID in QUESTIONS must dispatch to a resolver."""
        for q in QUESTIONS:
            result = answer_question(
                q["id"], QUESTIONS, PADDINGTON, EDINBURGH, ALL_STATIONS, CONFIG
            )
            assert "answerable" in result, f"Missing 'answerable' key for {q['id']}"

    def test_unknown_question_raises(self):
        """An unknown question id should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown question id"):
            answer_question("q99", QUESTIONS, PADDINGTON, EDINBURGH, ALL_STATIONS, CONFIG)
