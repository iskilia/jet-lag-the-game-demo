"""Unit tests for the guess engine (Task 7 acceptance criteria)."""

from src.guess_engine import check_guess, levenshtein, normalise

HIDER = {
    "id": "london-paddington",
    "name": "London Paddington",
}

ALL_STATIONS = [HIDER]


class TestNormalise:
    """Tests for the normalise helper."""

    def test_lowercase(self):
        """Input is lowercased."""
        assert normalise("LONDON") == "london"

    def test_strip_whitespace(self):
        """Leading/trailing whitespace is stripped."""
        assert normalise("  london  ") == "london"

    def test_collapse_internal_spaces(self):
        """Multiple internal spaces are collapsed to one."""
        assert normalise("london  paddington") == "london paddington"

    def test_strip_punctuation(self):
        """Punctuation is removed."""
        assert normalise("london's") == "londons"


class TestLevenshtein:
    """Tests for the Levenshtein distance function."""

    def test_identical(self):
        """Distance between identical strings is 0."""
        assert levenshtein("abc", "abc") == 0

    def test_single_insert(self):
        """One insertion is distance 1."""
        assert levenshtein("abc", "abcd") == 1

    def test_single_delete(self):
        """One deletion is distance 1."""
        assert levenshtein("abcd", "abc") == 1

    def test_single_substitute(self):
        """One substitution is distance 1."""
        assert levenshtein("abc", "aXc") == 1


class TestCheckGuess:
    """Tests for check_guess acceptance criteria."""

    def test_exact_lowercase_match(self):
        """'london paddington' (lowercase) matches correctly."""
        result = check_guess("london paddington", HIDER, ALL_STATIONS)
        assert result["correct"] is True

    def test_exact_mixed_case_match(self):
        """'London Paddington' (original case) matches correctly."""
        result = check_guess("London Paddington", HIDER, ALL_STATIONS)
        assert result["correct"] is True

    def test_double_space_match(self):
        """'london  paddington' (double space) matches correctly."""
        result = check_guess("london  paddington", HIDER, ALL_STATIONS)
        assert result["correct"] is True

    def test_trailing_space_match(self):
        """Trailing whitespace is stripped before comparison."""
        result = check_guess("London Paddington   ", HIDER, ALL_STATIONS)
        assert result["correct"] is True

    def test_near_miss_suggestion(self):
        """A typo within edit distance 2 returns a suggestion."""
        result = check_guess("London Padinton", HIDER, ALL_STATIONS)
        assert result["correct"] is False
        assert result.get("suggestion") == "London Paddington"

    def test_completely_wrong_no_suggestion(self):
        """A completely different name returns no suggestion."""
        result = check_guess("Edinburgh Waverley", HIDER, ALL_STATIONS)
        assert result["correct"] is False
        assert "suggestion" not in result
