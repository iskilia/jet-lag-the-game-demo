"""Unit tests for the game state machine (Task 8 acceptance criteria).

Tests verify that the reducer is pure (does not mutate input) and that each
action produces the correct state transition.
"""

import copy
import random

from src.game_state import (
    ACTION_ASK_QUESTION,
    ACTION_GIVE_UP,
    ACTION_MAKE_GUESS,
    ACTION_REQUEST_HINT,
    ACTION_RESET,
    ACTION_SELECT_COUNTRY,
    ACTION_SELECT_STARTING_STATION,
    ACTION_START_SETUP,
    STATE_ENDED,
    STATE_PLAYING,
    STATE_SETUP_COUNTRY,
    STATE_SETUP_STARTING_STATION,
    get_final_time,
    initial_state,
    reduce,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

STATION_A = {
    "id": "london-paddington",
    "name": "London Paddington",
    "operators": ["GWR"],
    "postcode": "W2 1HQ",
    "postcodeArea": "W",
    "cardinalDirection": "South",
    "region": "London",
    "closestMajorCity": "London",
    "landmarks": [],
}

STATION_B = {
    "id": "edinburgh-waverley",
    "name": "Edinburgh Waverley",
    "operators": ["LNER"],
    "postcode": "EH1 1BB",
    "postcodeArea": "EH",
    "cardinalDirection": "North",
    "region": "Scotland",
    "closestMajorCity": "Edinburgh",
    "landmarks": [],
}

STATION_C = {
    "id": "aberystwyth",
    "name": "Aberystwyth",
    "operators": ["TFW"],
    "postcode": "SY23 1DG",
    "postcodeArea": "SY",
    "cardinalDirection": "West",
    "region": "Wales",
    "closestMajorCity": "Cardiff",
    "landmarks": [],
}

STATION_D = {
    "id": "manchester-piccadilly",
    "name": "Manchester Piccadilly",
    "operators": ["Avanti West Coast"],
    "postcode": "M1 2BN",
    "postcodeArea": "M",
    "cardinalDirection": "North",
    "region": "North West",
    "closestMajorCity": "Manchester",
    "landmarks": [],
}

ALL_STATIONS = [STATION_A, STATION_B, STATION_C, STATION_D]

CONFIG = {
    "penalties": {"wrongGuess": 1, "question": 3, "hint": 0},
    "unansweredQuestionLimit": 3,
    "intercityOperators": [],
    "sleeperOperators": [],
}

QUESTIONS = [
    {"id": "q01", "text": "First letter?", "resolver": "firstLetterOfName", "penaltyMinutes": 3},
]


def _base_playing_state() -> dict:
    """Return a state wired to PLAYING with known stations."""
    state = initial_state()
    state = reduce(state, {
        "type": ACTION_SELECT_COUNTRY,
        "payload": {
            "country_id": "UK",
            "config": CONFIG,
            "all_stations": ALL_STATIONS,
            "questions": QUESTIONS,
        },
    })

    # Deterministic setup: inject stations directly
    state = reduce(state, {
        "type": ACTION_START_SETUP,
        "payload": {
            "random_fn": lambda seq: random.sample(seq, 1)[0],
        },
    })

    # Select seeker station (station_b)
    state = reduce(state, {
        "type": ACTION_SELECT_STARTING_STATION,
        "payload": {
            "station_id": STATION_B["id"],
            "timestamp": 1000.0,
        },
    })
    return state


# ---------------------------------------------------------------------------
# Tests: reducer purity
# ---------------------------------------------------------------------------


class TestReducerPurity:
    """Verify the reducer never mutates the input state."""

    def test_does_not_mutate_initial_state(self):
        """RESET action must not mutate the provided state."""
        state = initial_state()
        original = copy.deepcopy(state)
        reduce(state, {"type": ACTION_RESET})
        assert state == original

    def test_does_not_mutate_playing_state(self):
        """ASK_QUESTION must not mutate the input state."""
        state = _base_playing_state()
        original = copy.deepcopy(state)
        reduce(state, {
            "type": ACTION_ASK_QUESTION,
            "payload": {
                "question_id": "q01",
                "question_text": "First letter?",
                "result": {"answerable": True, "answer": "L"},
                "penalty_minutes": 3,
                "timestamp": 1100.0,
            },
        })
        assert state == original


# ---------------------------------------------------------------------------
# Tests: state transitions
# ---------------------------------------------------------------------------


class TestSelectCountry:
    """Tests for the SELECT_COUNTRY action."""

    def test_transitions_to_setup_country(self):
        """SELECT_COUNTRY transitions from IDLE to SETUP_COUNTRY."""
        state = initial_state()
        new_state = reduce(state, {
            "type": ACTION_SELECT_COUNTRY,
            "payload": {
                "country_id": "UK",
                "config": CONFIG,
                "all_stations": ALL_STATIONS,
                "questions": QUESTIONS,
            },
        })
        assert new_state["status"] == STATE_SETUP_COUNTRY
        assert new_state["countryId"] == "UK"
        assert len(new_state["allStations"]) == 4


class TestStartSetup:
    """Tests for the START_SETUP action."""

    def test_picks_hider_and_options(self):
        """START_SETUP picks a hider station and 3 starting options."""
        state = initial_state()
        state = reduce(state, {
            "type": ACTION_SELECT_COUNTRY,
            "payload": {
                "country_id": "UK",
                "config": CONFIG,
                "all_stations": ALL_STATIONS,
                "questions": QUESTIONS,
            },
        })
        new_state = reduce(state, {"type": ACTION_START_SETUP, "payload": {}})
        assert new_state["status"] == STATE_SETUP_STARTING_STATION
        assert new_state["hiderStation"] is not None

    def test_hider_not_in_starting_options(self):
        """The hider's station must not appear in the starting options."""
        state = initial_state()
        state = reduce(state, {
            "type": ACTION_SELECT_COUNTRY,
            "payload": {
                "country_id": "UK",
                "config": CONFIG,
                "all_stations": ALL_STATIONS,
                "questions": QUESTIONS,
            },
        })
        new_state = reduce(state, {"type": ACTION_START_SETUP, "payload": {}})
        hider_id = new_state["hiderStation"]["id"]
        option_ids = [s["id"] for s in new_state["startingStationOptions"]]
        assert hider_id not in option_ids


class TestSelectStartingStation:
    """Tests for the SELECT_STARTING_STATION action."""

    def test_transitions_to_playing(self):
        """SELECT_STARTING_STATION transitions to PLAYING."""
        state = _base_playing_state()
        assert state["status"] == STATE_PLAYING
        assert state["seekerStation"]["id"] == STATION_B["id"]
        assert state["gameStartTime"] == 1000.0


class TestAskQuestion:
    """Tests for the ASK_QUESTION action."""

    def test_answerable_question_adds_penalty(self):
        """Answerable question adds penalty minutes."""
        state = _base_playing_state()
        initial_penalty = state["penaltyMinutes"]
        new_state = reduce(state, {
            "type": ACTION_ASK_QUESTION,
            "payload": {
                "question_id": "q01",
                "question_text": "First letter?",
                "result": {"answerable": True, "answer": "L"},
                "penalty_minutes": 3,
                "timestamp": 1100.0,
            },
        })
        assert new_state["penaltyMinutes"] == initial_penalty + 3
        assert "q01" in new_state["askedQuestionIds"]

    def test_repeat_question_no_extra_penalty(self):
        """Re-asking the same question does not add another penalty."""
        state = _base_playing_state()
        state = reduce(state, {
            "type": ACTION_ASK_QUESTION,
            "payload": {
                "question_id": "q01",
                "question_text": "First letter?",
                "result": {"answerable": True, "answer": "L"},
                "penalty_minutes": 3,
                "timestamp": 1100.0,
            },
        })
        penalty_after_first = state["penaltyMinutes"]
        new_state = reduce(state, {
            "type": ACTION_ASK_QUESTION,
            "payload": {
                "question_id": "q01",
                "question_text": "First letter?",
                "result": {"answerable": True, "answer": "L"},
                "penalty_minutes": 3,
                "timestamp": 1200.0,
            },
        })
        assert new_state["penaltyMinutes"] == penalty_after_first

    def test_unanswerable_question_increments_count(self):
        """Unanswerable question increments unansweredCount without penalty."""
        state = _base_playing_state()
        new_state = reduce(state, {
            "type": ACTION_ASK_QUESTION,
            "payload": {
                "question_id": "q01",
                "question_text": "Airport?",
                "result": {"answerable": False, "reason": "No data"},
                "penalty_minutes": 3,
                "timestamp": 1100.0,
            },
        })
        assert new_state["unansweredCount"] == 1
        assert new_state["penaltyMinutes"] == 0

    def test_unanswered_limit_ends_game(self):
        """Reaching unansweredQuestionLimit transitions to ENDED."""
        state = _base_playing_state()
        unanswerable_result = {"answerable": False, "reason": "No data"}
        for i in range(3):
            state = reduce(state, {
                "type": ACTION_ASK_QUESTION,
                "payload": {
                    "question_id": f"q0{i + 1}",
                    "question_text": "?",
                    "result": unanswerable_result,
                    "penalty_minutes": 3,
                    "timestamp": 1100.0 + i,
                },
            })
        assert state["status"] == STATE_ENDED
        assert state["endReason"] == "unanswered_limit"


class TestRequestHint:
    """Tests for the REQUEST_HINT action."""

    def test_hint_added_to_history(self):
        """A revealed hint is added to the history log."""
        state = _base_playing_state()
        hint = {"type": "region", "text": "The station is in London."}
        new_state = reduce(state, {
            "type": ACTION_REQUEST_HINT,
            "payload": {"hint": hint, "timestamp": 1100.0},
        })
        assert "region" in new_state["revealedHintTypes"]
        history_types = [e["type"] for e in new_state["history"]]
        assert "hint" in history_types


class TestMakeGuess:
    """Tests for the MAKE_GUESS action."""

    def test_correct_guess_ends_game(self):
        """A correct guess transitions to ENDED with reason 'found'."""
        state = _base_playing_state()
        new_state = reduce(state, {
            "type": ACTION_MAKE_GUESS,
            "payload": {
                "input": "London Paddington",
                "result": {"correct": True},
                "timestamp": 1500.0,
            },
        })
        assert new_state["status"] == STATE_ENDED
        assert new_state["endReason"] == "found"

    def test_wrong_guess_adds_penalty(self):
        """A wrong guess adds 1 min penalty."""
        state = _base_playing_state()
        new_state = reduce(state, {
            "type": ACTION_MAKE_GUESS,
            "payload": {
                "input": "Wrong Station",
                "result": {"correct": False},
                "timestamp": 1500.0,
            },
        })
        assert new_state["penaltyMinutes"] == 1
        assert new_state["wrongGuessCount"] == 1
        assert new_state["status"] == STATE_PLAYING


class TestGiveUp:
    """Tests for the GIVE_UP action."""

    def test_give_up_ends_game(self):
        """GIVE_UP transitions to ENDED with reason 'gave_up'."""
        state = _base_playing_state()
        new_state = reduce(state, {
            "type": ACTION_GIVE_UP,
            "payload": {"timestamp": 2000.0},
        })
        assert new_state["status"] == STATE_ENDED
        assert new_state["endReason"] == "gave_up"


class TestReset:
    """Tests for the RESET action."""

    def test_reset_returns_idle(self):
        """RESET returns an IDLE state regardless of current state."""
        state = _base_playing_state()
        new_state = reduce(state, {"type": ACTION_RESET})
        assert new_state == initial_state()


class TestGetFinalTime:
    """Tests for the get_final_time scoring function."""

    def test_final_time_includes_penalty(self):
        """Final time equals elapsed + penalty minutes converted to ms."""
        state = _base_playing_state()
        state["gameEndTime"] = state["gameStartTime"] + 120  # 2 minutes elapsed
        state["penaltyMinutes"] = 5

        result = get_final_time(state)
        assert result["elapsed_ms"] == 120_000
        assert result["penalty_ms"] == 5 * 60 * 1000
        assert result["total_ms"] == 120_000 + 300_000
