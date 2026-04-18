"""Hide N Seek: UK Edition — terminal game entry point.

Run with::

    uv run python main.py

The game is a single-player terminal experience where the human plays as the
seeker, trying to locate the computer hider's hidden UK rail station using
questions, hints, and guesses. Time is the score.
"""

import sys
import time

from src.answer_engine import answer_question
from src.data_loader import load_countries, load_country_data
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
    STATE_SETUP_STARTING_STATION,
    get_final_time,
    initial_state,
    reduce,
)
from src.guess_engine import check_guess
from src.hint_engine import generate_hint, remaining_hint_count

# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def _divider(char: str = "-", width: int = 60) -> None:
    """Print a horizontal divider line.

    Args:
        char: Character to repeat.
        width: Total width of the divider.
    """
    print(char * width)


def _header(title: str) -> None:
    """Print a section header.

    Args:
        title: Title text to display.
    """
    _divider("=")
    print(f"  {title}")
    _divider("=")


def _elapsed_str(start_time: float) -> str:
    """Format elapsed seconds since start_time as MM:SS.

    Args:
        start_time: Unix timestamp of game start.

    Returns:
        Formatted string like "04:12".
    """
    elapsed = int(time.time() - start_time)
    minutes = elapsed // 60
    seconds = elapsed % 60
    return f"{minutes:02d}:{seconds:02d}"


def _print_timer(state: dict) -> None:
    """Print the current elapsed time and penalty summary.

    Args:
        state: Current game state dict.
    """
    if state.get("gameStartTime"):
        elapsed = _elapsed_str(state["gameStartTime"])
        penalty = state.get("penaltyMinutes", 0)
        print(f"\n  Timer: {elapsed} elapsed  |  Penalty: +{penalty} min")
        print(f"  Seeker's station: {state['seekerStation']['name']}\n")


def _print_history(state: dict) -> None:
    """Print the history log of events.

    Args:
        state: Current game state dict.
    """
    history = state.get("history", [])
    if not history:
        print("  (no history yet)")
        return
    for entry in history:
        etype = entry.get("type")
        if etype == "question":
            result = entry["result"]
            answer = result.get("answer")
            if isinstance(answer, bool):
                answer_str = "Yes" if answer else "No"
            else:
                answer_str = str(answer)
            print(f"  [Q] {entry['questionText']}")
            print(f"      -> {answer_str}  (+{entry['penaltyAdded']} min)")
        elif etype == "question_repeat":
            result = entry["result"]
            answer = result.get("answer")
            if isinstance(answer, bool):
                answer_str = "Yes" if answer else "No"
            else:
                answer_str = str(answer)
            print(f"  [Q] {entry['questionText']} (asked before)")
            print(f"      -> {answer_str}  (no extra penalty)")
        elif etype == "question_unanswerable":
            print(f"  [Q] {entry['questionText']}")
            print(f"      -> UNANSWERABLE: {entry['result'].get('reason', '')}")
        elif etype == "hint":
            print(f"  [H] {entry['hintText']}")
        elif etype == "hint_exhausted":
            print("  [H] No more hints available.")
        elif etype == "guess_wrong":
            suggestion = entry.get("suggestion", "")
            sug_str = f"  Did you mean: {suggestion}?" if suggestion else ""
            print(f"  [X] Wrong guess: '{entry['input']}'{sug_str}  (+{entry['penaltyAdded']} min)")
        elif etype == "guess_correct":
            print(f"  [V] Correct! '{entry['input']}'")
        elif etype == "give_up":
            print("  [!] Player gave up.")


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------


def _prompt(message: str, default: str = "") -> str:
    """Prompt the user for input, stripping surrounding whitespace.

    Args:
        message: Prompt text to display.
        default: Value returned if the user presses Enter without typing.

    Returns:
        Stripped input string, or ``default`` if empty.
    """
    try:
        value = input(message).strip()
        return value if value else default
    except (EOFError, KeyboardInterrupt):
        print("\nExiting game.")
        sys.exit(0)


def _choose_from_list(items: list[str], prompt: str = "Enter number: ") -> int:
    """Display a numbered list and prompt the user to choose an item.

    Keeps prompting until a valid integer in range is entered.

    Args:
        items: List of display strings.
        prompt: Input prompt text.

    Returns:
        Zero-based index of the chosen item.
    """
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item}")
    while True:
        choice = _prompt(prompt)
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return idx
        print(f"  Please enter a number between 1 and {len(items)}.")


# ---------------------------------------------------------------------------
# Screen: Country selection
# ---------------------------------------------------------------------------


def screen_select_country() -> tuple[str, dict, list, list]:
    """Display the country selection screen and return loaded game data.

    Returns:
        A 4-tuple: (country_id, config, stations, questions).
    """
    _header("HIDE N SEEK: UK RAIL EDITION")
    print("  Welcome! You are the seeker. Your goal is to find the hider's")
    print("  hidden UK rail station as quickly as possible.")
    print()

    countries = load_countries()
    labels = [c["label"] for c in countries]
    print("  Select a country:")
    idx = _choose_from_list(labels)
    country_id = countries[idx]["id"]

    result = load_country_data(country_id)
    if result is None:
        print(f"  Error: could not load data for {country_id}")
        sys.exit(1)

    config, stations, questions, _ = result
    return country_id, config, stations, questions


# ---------------------------------------------------------------------------
# Screen: Starting station selection
# ---------------------------------------------------------------------------


def screen_select_starting_station(state: dict) -> str:
    """Display the starting station picker and return the chosen station id.

    Args:
        state: Game state in SETUP_STARTING_STATION status.

    Returns:
        The chosen station's id string.
    """
    _header("CHOOSE YOUR STARTING STATION")
    print("  The hider has secretly chosen a station. Now choose your")
    print("  starting station — this is the station you are located at.")
    print()
    options = state["startingStationOptions"]
    labels = []
    for s in options:
        ops = ", ".join(s["operators"][:2])
        if len(s["operators"]) > 2:
            ops += f" (+{len(s['operators']) - 2} more)"
        labels.append(f"{s['name']}  [{s['region']}]  ({ops})")
    idx = _choose_from_list(labels, "Choose your starting station: ")
    return options[idx]["id"]


# ---------------------------------------------------------------------------
# Screen: Main game loop
# ---------------------------------------------------------------------------


def screen_game(state: dict) -> dict:
    """Run the main game loop, returning the final state when the game ends.

    Presents a menu of: Ask Question, Request Hint, Make Guess, Give Up,
    View History. Calls the engines and dispatches actions back to the reducer.

    Args:
        state: Game state in PLAYING status.

    Returns:
        Final game state dict (status == ENDED).
    """
    _header("GAME IN PROGRESS")
    print("  The hider is hiding somewhere on the UK rail network!")
    print("  Use questions, hints, and guesses to find them.")
    print()

    questions = state["questions"]
    all_stations = state["allStations"]
    config = state["config"]

    while state["status"] == STATE_PLAYING:
        _print_timer(state)
        _divider()
        print("  What would you like to do?")
        print("  1. Ask a question  (+3 min penalty)")
        print("  2. Request a hint  (no penalty)")
        print("  3. Make a guess    (+1 min if wrong)")
        print("  4. Give up")
        print("  5. View history")
        _divider()
        choice = _prompt("  Enter choice (1-5): ")

        if choice == "1":
            state = _action_ask_question(state, questions, all_stations, config)
        elif choice == "2":
            state = _action_request_hint(state)
        elif choice == "3":
            state = _action_make_guess(state, all_stations)
        elif choice == "4":
            state = _action_give_up(state)
        elif choice == "5":
            _header("HISTORY")
            _print_history(state)
        else:
            print("  Invalid choice. Please enter 1, 2, 3, 4, or 5.")

    return state


def _action_ask_question(
    state: dict,
    questions: list[dict],
    all_stations: list[dict],
    config: dict,
) -> dict:
    """Handle the Ask Question flow.

    Displays the full list of 37 questions, lets the user pick one, resolves
    the answer, and dispatches ASK_QUESTION to the reducer.

    Re-asking a previously asked question shows the cached answer without a
    new penalty.

    Args:
        state: Current game state.
        questions: Full list of question records.
        all_stations: All station records.
        config: Country config dict.

    Returns:
        Updated game state.
    """
    _header("ASK A QUESTION")
    asked_ids = state.get("askedQuestionIds", [])
    labels = []
    for q in questions:
        marker = " (asked)" if q["id"] in asked_ids else ""
        labels.append(f"[{q['id']}]{marker} {q['text']}")

    print("  Each question adds 3 min to your total time.\n")
    idx = _choose_from_list(labels, "  Choose question: ")
    chosen_q = questions[idx]

    result = answer_question(
        chosen_q["id"],
        questions,
        state["hiderStation"],
        state["seekerStation"],
        all_stations,
        config,
    )

    # Display answer immediately
    if result.get("answerable", True):
        answer = result["answer"]
        if isinstance(answer, bool):
            answer_str = "Yes" if answer else "No"
        else:
            answer_str = str(answer)
        print(f"\n  Answer: {answer_str}")
    else:
        print(f"\n  Unanswerable: {result.get('reason', 'No data available')}")

    return reduce(
        state,
        {
            "type": ACTION_ASK_QUESTION,
            "payload": {
                "question_id": chosen_q["id"],
                "question_text": chosen_q["text"],
                "result": result,
                "penalty_minutes": chosen_q["penaltyMinutes"],
                "timestamp": time.time(),
            },
        },
    )


def _action_request_hint(state: dict) -> dict:
    """Handle the Request Hint flow.

    Generates a hint via the hint engine and dispatches REQUEST_HINT.

    Args:
        state: Current game state.

    Returns:
        Updated game state.
    """
    _header("REQUEST A HINT")
    remaining = remaining_hint_count(
        state["hiderStation"], state["revealedHintTypes"]
    )
    print(f"  Hints remaining: {remaining}")
    print()

    hint = generate_hint(state["hiderStation"], state["revealedHintTypes"])
    if hint:
        print(f"  Hint: {hint['text']}")
    else:
        print("  No more hints available.")

    return reduce(
        state,
        {
            "type": ACTION_REQUEST_HINT,
            "payload": {"hint": hint, "timestamp": time.time()},
        },
    )


def _action_make_guess(state: dict, all_stations: list[dict]) -> dict:
    """Handle the Make Guess flow.

    Normalises the guess, checks it against the hider's station, and
    dispatches MAKE_GUESS. If a suggestion is offered, prompts the user to
    confirm before accepting it.

    Args:
        state: Current game state.
        all_stations: Full list of station records.

    Returns:
        Updated game state.
    """
    _header("MAKE A GUESS")

    # Offer autocomplete hint
    guess_input = _prompt("  Enter station name: ")
    if not guess_input:
        print("  No input provided.")
        return state

    result = check_guess(guess_input, state["hiderStation"], all_stations)

    if result.get("correct"):
        print(f"\n  CORRECT! The hider was at {state['hiderStation']['name']}!")
    elif "suggestion" in result:
        suggestion = result["suggestion"]
        print(f"\n  No exact match. Did you mean: {suggestion}?")
        confirm = _prompt("  Confirm? (y/n): ").lower()
        if confirm == "y":
            # Re-run check_guess with the suggested name
            result = check_guess(suggestion, state["hiderStation"], all_stations)
            if result.get("correct"):
                print(f"\n  CORRECT! The hider was at {state['hiderStation']['name']}!")
            else:
                print("\n  Wrong guess. +1 min penalty.")
        else:
            print("  Guess cancelled, no penalty applied.")
            return state
    else:
        print("\n  Wrong guess. +1 min penalty.")

    return reduce(
        state,
        {
            "type": ACTION_MAKE_GUESS,
            "payload": {
                "input": guess_input,
                "result": result,
                "timestamp": time.time(),
            },
        },
    )


def _action_give_up(state: dict) -> dict:
    """Handle the Give Up flow, with a confirmation prompt.

    Args:
        state: Current game state.

    Returns:
        Updated game state (transitioned to ENDED if confirmed).
    """
    confirm = _prompt("  Are you sure you want to give up? (y/n): ").lower()
    if confirm == "y":
        return reduce(
            state,
            {
                "type": ACTION_GIVE_UP,
                "payload": {"timestamp": time.time()},
            },
        )
    print("  Continuing game.")
    return state


# ---------------------------------------------------------------------------
# Screen: End screen
# ---------------------------------------------------------------------------


def screen_end(state: dict) -> None:
    """Display the end screen with the result and final time breakdown.

    Args:
        state: Final game state dict (status == ENDED).
    """
    _header("GAME OVER")
    reason = state.get("endReason")

    if reason == "found":
        print("  FOUND IT! Well done, seeker!")
    elif reason == "gave_up":
        print("  You gave up. Better luck next time.")
    elif reason == "unanswered_limit":
        print("  Too many unanswerable questions. Game over.")
        # NOTE: This behaviour (end game on unanswered limit) is the default.
        # The user should confirm whether this is the intended rule.
        # See config.unansweredLimitBehaviour and config.unansweredQuestionLimit.
    else:
        print("  Game ended.")

    hider = state.get("hiderStation", {})
    print()
    print(f"  The hider was hiding at: {hider.get('name', 'Unknown')}")
    print(f"  Region:                  {hider.get('region', '')}")
    print(f"  Cardinal direction:      {hider.get('cardinalDirection', '')}")
    print(f"  Closest major city:      {hider.get('closestMajorCity', '')}")
    if hider.get("landmarks"):
        print(f"  Nearby landmarks:        {', '.join(hider['landmarks'])}")
    print(f"  Operators:               {', '.join(hider.get('operators', []))}")
    print(f"  Postcode:                {hider.get('postcode', '')}")
    print()

    timing = get_final_time(state)
    print("  Final time breakdown:")
    for line in timing["breakdown"]:
        print(f"    {line}")
    print()

    _header("HISTORY")
    _print_history(state)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the Hide N Seek game from start to finish."""
    play_again = True
    while play_again:
        state = initial_state()

        # Country selection
        country_id, config, stations, questions = screen_select_country()
        state = reduce(
            state,
            {
                "type": ACTION_SELECT_COUNTRY,
                "payload": {
                    "country_id": country_id,
                    "config": config,
                    "all_stations": stations,
                    "questions": questions,
                },
            },
        )

        # Setup: pick hider and starting stations
        state = reduce(state, {"type": ACTION_START_SETUP, "payload": {}})

        if state["status"] != STATE_SETUP_STARTING_STATION:
            print("  Error during setup.")
            sys.exit(1)

        # Starting station selection
        chosen_id = screen_select_starting_station(state)
        state = reduce(
            state,
            {
                "type": ACTION_SELECT_STARTING_STATION,
                "payload": {
                    "station_id": chosen_id,
                    "timestamp": time.time(),
                },
            },
        )

        if state["status"] != STATE_PLAYING:
            print("  Error starting game.")
            sys.exit(1)

        # Main game loop
        state = screen_game(state)

        # End screen
        if state["status"] == STATE_ENDED:
            screen_end(state)

        again = _prompt("\n  Play again? (y/n): ").lower()
        play_again = again == "y"

        if play_again:
            state = reduce(state, {"type": ACTION_RESET, "payload": {}})

    print("\n  Thanks for playing! Goodbye.")


if __name__ == "__main__":
    main()
