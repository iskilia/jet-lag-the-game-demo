"""Game state machine — pure reducer for the Hide N Seek game.

The state machine manages the full game lifecycle via a ``reduce`` function.
All state transitions are pure: no I/O, no randomness beyond what is injected
via ``random_fn``.

States::

    IDLE
    SETUP_COUNTRY
    SETUP_STARTING_STATION
    PLAYING
    ENDED

Actions::

    SELECT_COUNTRY           payload: {"country_id": str}
    START_SETUP              payload: {"random_fn": callable}  (optional override)
    SELECT_STARTING_STATION  payload: {"station_id": str}
    ASK_QUESTION             payload: {"question_id": str, "result": dict}
    REQUEST_HINT             payload: {"hint": dict | None}
    MAKE_GUESS               payload: {"input": str, "result": dict}
    GIVE_UP                  payload: {}
    RESET                    payload: {}
"""

import copy
import time
from typing import Any, Callable, Optional

# ---------------------------------------------------------------------------
# State constants
# ---------------------------------------------------------------------------

STATE_IDLE = "IDLE"
STATE_SETUP_COUNTRY = "SETUP_COUNTRY"
STATE_SETUP_STARTING_STATION = "SETUP_STARTING_STATION"
STATE_PLAYING = "PLAYING"
STATE_ENDED = "ENDED"

# ---------------------------------------------------------------------------
# Action type constants
# ---------------------------------------------------------------------------

ACTION_SELECT_COUNTRY = "SELECT_COUNTRY"
ACTION_START_SETUP = "START_SETUP"
ACTION_SELECT_STARTING_STATION = "SELECT_STARTING_STATION"
ACTION_ASK_QUESTION = "ASK_QUESTION"
ACTION_REQUEST_HINT = "REQUEST_HINT"
ACTION_MAKE_GUESS = "MAKE_GUESS"
ACTION_GIVE_UP = "GIVE_UP"
ACTION_RESET = "RESET"


# ---------------------------------------------------------------------------
# Initial state factory
# ---------------------------------------------------------------------------


def initial_state() -> dict:
    """Return the initial game state dict.

    Returns:
        A dict representing the IDLE game state with all counters zeroed.
    """
    return {
        "status": STATE_IDLE,
        "countryId": None,
        "config": None,
        "allStations": [],
        "questions": [],
        "hiderStation": None,
        "seekerStation": None,
        "startingStationOptions": [],
        "history": [],                   # list of event dicts
        "penaltyMinutes": 0,             # accumulated penalty
        "unansweredCount": 0,            # count of unanswerable questions
        "wrongGuessCount": 0,
        "askedQuestionIds": [],          # q-ids already asked
        "revealedHintTypes": [],         # hint type keys already revealed
        "gameStartTime": None,           # float (Unix timestamp)
        "gameEndTime": None,             # float (Unix timestamp)
        "endReason": None,               # "found" | "gave_up" | "unanswered_limit"
    }


# ---------------------------------------------------------------------------
# Reducer helpers
# ---------------------------------------------------------------------------


def _pick_hider_station(stations: list[dict], random_fn: Callable) -> dict:
    """Pick a random hider station from the full list.

    Args:
        stations: List of all station records.
        random_fn: A callable equivalent to ``random.choice`` for injection.

    Returns:
        A single station record chosen at random.
    """
    return random_fn(stations)


def _pick_starting_options(
    stations: list[dict],
    hider_station: dict,
    random_fn: Callable,
    count: int = 3,
) -> list[dict]:
    """Pick starting-station options for the seeker, excluding the hider's station.

    Re-rolls until all options are distinct from the hider's station. In the
    1/1666 chance that a candidate equals the hider, it is excluded.

    Args:
        stations: Full list of station records.
        hider_station: The hider's already-chosen station (must be excluded).
        random_fn: Callable matching ``random.choice`` signature.
        count: Number of options to generate.

    Returns:
        A list of ``count`` distinct station records, none of which is the
        hider's station.
    """
    pool = [s for s in stations if s["id"] != hider_station["id"]]
    # Cap count at pool size to avoid an infinite loop with small datasets
    actual_count = min(count, len(pool))
    chosen: list[dict] = []
    used_ids: set[str] = set()
    while len(chosen) < actual_count:
        candidate = random_fn(pool)
        if candidate["id"] not in used_ids:
            chosen.append(candidate)
            used_ids.add(candidate["id"])
    return chosen


# ---------------------------------------------------------------------------
# Reducer
# ---------------------------------------------------------------------------


def reduce(state: dict, action: dict) -> dict:
    """Pure reducer: (state, action) -> new_state.

    Never mutates the input state. All changes are applied to a deep copy.

    Args:
        state: Current game state dict.
        action: Action dict with ``"type"`` key and optional ``"payload"``.

    Returns:
        New game state dict.
    """
    action_type = action.get("type")
    payload: dict = action.get("payload", {})
    new_state = copy.deepcopy(state)

    if action_type == ACTION_RESET:
        return initial_state()

    if action_type == ACTION_SELECT_COUNTRY:
        new_state["status"] = STATE_SETUP_COUNTRY
        new_state["countryId"] = payload.get("country_id")
        new_state["config"] = payload.get("config")
        new_state["allStations"] = payload.get("all_stations", [])
        new_state["questions"] = payload.get("questions", [])
        return new_state

    if action_type == ACTION_START_SETUP:
        random_fn: Callable = payload.get("random_fn", _default_random_choice)
        stations = new_state["allStations"]
        hider = _pick_hider_station(stations, random_fn)
        options = _pick_starting_options(stations, hider, random_fn)
        new_state["status"] = STATE_SETUP_STARTING_STATION
        new_state["hiderStation"] = hider
        new_state["startingStationOptions"] = options
        return new_state

    if action_type == ACTION_SELECT_STARTING_STATION:
        station_id = payload.get("station_id")
        station = next(
            (s for s in new_state["allStations"] if s["id"] == station_id), None
        )
        if station is None:
            return new_state  # no-op for unknown id
        new_state["status"] = STATE_PLAYING
        new_state["seekerStation"] = station
        new_state["gameStartTime"] = payload.get("timestamp", time.time())
        return new_state

    if action_type == ACTION_ASK_QUESTION:
        return _handle_ask_question(new_state, payload)

    if action_type == ACTION_REQUEST_HINT:
        return _handle_request_hint(new_state, payload)

    if action_type == ACTION_MAKE_GUESS:
        return _handle_make_guess(new_state, payload)

    if action_type == ACTION_GIVE_UP:
        new_state["status"] = STATE_ENDED
        new_state["endReason"] = "gave_up"
        new_state["gameEndTime"] = payload.get("timestamp", time.time())
        new_state["history"].append(
            {"type": "give_up", "timestamp": new_state["gameEndTime"]}
        )
        return new_state

    # Unknown action — return state unchanged
    return new_state


def _handle_ask_question(state: dict, payload: dict) -> dict:
    """Handle the ASK_QUESTION action.

    Logs the question and answer, applies penalties, and checks whether the
    unanswered limit has been reached.

    Args:
        state: Deep-copied current state.
        payload: Action payload with question_id and result dict.

    Returns:
        Updated state dict.
    """
    question_id: str = payload["question_id"]
    result: dict = payload["result"]        # from answer_engine.answer_question
    question_text: str = payload.get("question_text", "")
    timestamp: float = payload.get("timestamp", time.time())

    # Prevent double-penalty: if already asked, return cached answer, no penalty
    if question_id in state["askedQuestionIds"]:
        # Find the original history entry and return it without new penalty
        original = next(
            (e for e in state["history"] if e.get("questionId") == question_id),
            None,
        )
        state["history"].append(
            {
                "type": "question_repeat",
                "questionId": question_id,
                "questionText": question_text,
                "result": original["result"] if original else result,
                "timestamp": timestamp,
                "penaltyAdded": 0,
            }
        )
        return state

    state["askedQuestionIds"].append(question_id)

    if result.get("answerable", True):
        penalty = payload.get("penalty_minutes", 3)
        state["penaltyMinutes"] += penalty
        state["history"].append(
            {
                "type": "question",
                "questionId": question_id,
                "questionText": question_text,
                "result": result,
                "timestamp": timestamp,
                "penaltyAdded": penalty,
            }
        )
    else:
        # Unanswerable: increment counter, no time penalty
        state["unansweredCount"] += 1
        state["history"].append(
            {
                "type": "question_unanswerable",
                "questionId": question_id,
                "questionText": question_text,
                "result": result,
                "timestamp": timestamp,
                "penaltyAdded": 0,
            }
        )
        limit = state.get("config", {}).get("unansweredQuestionLimit", 3)
        if state["unansweredCount"] >= limit:
            state["status"] = STATE_ENDED
            state["endReason"] = "unanswered_limit"
            state["gameEndTime"] = timestamp

    return state


def _handle_request_hint(state: dict, payload: dict) -> dict:
    """Handle the REQUEST_HINT action.

    Logs the hint, records the revealed hint type, and applies the hint
    penalty from config.

    Args:
        state: Deep-copied current state.
        payload: Action payload with the hint dict (or None if exhausted).

    Returns:
        Updated state dict.
    """
    hint: Optional[dict] = payload.get("hint")
    timestamp: float = payload.get("timestamp", time.time())
    penalty: int = state.get("config", {}).get("penalties", {}).get("hint", 0)

    if hint is not None:
        state["revealedHintTypes"].append(hint["type"])
        state["penaltyMinutes"] += penalty
        state["history"].append(
            {
                "type": "hint",
                "hintType": hint["type"],
                "hintText": hint["text"],
                "timestamp": timestamp,
                "penaltyAdded": penalty,
            }
        )
    else:
        state["history"].append(
            {
                "type": "hint_exhausted",
                "timestamp": timestamp,
                "penaltyAdded": 0,
            }
        )
    return state


def _handle_make_guess(state: dict, payload: dict) -> dict:
    """Handle the MAKE_GUESS action.

    If correct → transition to ENDED(found). If wrong → add 1 min penalty.

    Args:
        state: Deep-copied current state.
        payload: Action payload with input text and result from guess_engine.

    Returns:
        Updated state dict.
    """
    guess_input: str = payload.get("input", "")
    result: dict = payload["result"]        # from guess_engine.check_guess
    timestamp: float = payload.get("timestamp", time.time())
    config = state.get("config") or {}
    wrong_penalty: int = config.get("penalties", {}).get("wrongGuess", 1)

    if result.get("correct"):
        state["status"] = STATE_ENDED
        state["endReason"] = "found"
        state["gameEndTime"] = timestamp
        state["history"].append(
            {
                "type": "guess_correct",
                "input": guess_input,
                "timestamp": timestamp,
                "penaltyAdded": 0,
            }
        )
    else:
        state["wrongGuessCount"] += 1
        state["penaltyMinutes"] += wrong_penalty
        entry: dict[str, Any] = {
            "type": "guess_wrong",
            "input": guess_input,
            "timestamp": timestamp,
            "penaltyAdded": wrong_penalty,
        }
        if "suggestion" in result:
            entry["suggestion"] = result["suggestion"]
        state["history"].append(entry)

    return state


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def get_final_time(state: dict) -> dict:
    """Compute the final time breakdown for a completed game.

    Args:
        state: The game state (should be in ENDED status for meaningful output).

    Returns:
        A dict with keys:
          - ``elapsed_ms``: wall-clock time in milliseconds.
          - ``penalty_ms``: total penalty in milliseconds.
          - ``total_ms``: elapsed_ms + penalty_ms.
          - ``breakdown``: human-readable summary strings.
    """
    start = state.get("gameStartTime") or 0.0
    end = state.get("gameEndTime") or time.time()
    elapsed_ms = int((end - start) * 1000)
    penalty_ms = state.get("penaltyMinutes", 0) * 60 * 1000
    total_ms = elapsed_ms + penalty_ms

    # Build breakdown lines
    history = state.get("history", [])
    question_count = sum(1 for e in history if e.get("type") == "question")
    wrong_guesses = state.get("wrongGuessCount", 0)
    breakdown = [
        f"Elapsed time:   {_ms_to_mmss(elapsed_ms)}",
        f"Questions asked: {question_count} x 3 min = {question_count * 3} min penalty",
        f"Wrong guesses:   {wrong_guesses} x 1 min = {wrong_guesses} min penalty",
        f"Total penalty:   {state.get('penaltyMinutes', 0)} min",
        f"Total time:     {_ms_to_mmss(total_ms)}",
    ]
    return {
        "elapsed_ms": elapsed_ms,
        "penalty_ms": penalty_ms,
        "total_ms": total_ms,
        "breakdown": breakdown,
    }


def _ms_to_mmss(ms: int) -> str:
    """Convert milliseconds to a MM:SS string.

    Args:
        ms: Duration in milliseconds.

    Returns:
        Formatted string like "03:45".
    """
    total_seconds = ms // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def _default_random_choice(seq: list) -> Any:
    """Default random choice implementation using the standard library.

    Args:
        seq: A non-empty sequence.

    Returns:
        A randomly chosen element.
    """
    import random
    return random.choice(seq)
