# Hide N Seek: UK Edition — Implementation Plan (Python CLI)

## 1. Project Overview

A single-player **text-based terminal game** where the human seeker tries to locate a computer hider who has hidden at a UK National Rail station. The seeker uses questions, hints, and guesses to narrow down the location. Time is the score — the faster you find the hider, the better.

Runs via `uv run game` using the entry point already defined in `pyproject.toml` (`game = "main:main"`).

### Game Data Summary (from `train_stations.csv`)
- **1,666 stations** across the UK
- **Columns**: `Station`, `Train Operating Companies / Lines`, `Postcode`, `Cardinal Direction`, `Region`, `Closest Major City`, `Landmark 1`, `Landmark 2`, `Landmark 3`
- **Regions (11)**: London, South East, South West, East of England, East Midlands, West Midlands, Yorkshire and the Humber, North East, North West, Wales, Scotland
- **Cardinal Directions**: North, South, East, West, Central
- **Closest Major Cities**: London, Manchester, Liverpool, Edinburgh, Glasgow, Cardiff, Swansea
- **Parsing detail**: The `Train Operating Companies / Lines` column is a comma-separated list inside a single quoted CSV field. Use Python's stdlib `csv` module — it handles this correctly out of the box.

---

## 2. Tech Stack

- **Language**: Python 3.11+ (project already set up)
- **Runtime entry**: `uv run game` → `main:main`
- **Stdlib only** for core logic: `csv`, `json`, `random`, `time`, `dataclasses`, `pathlib`, `re`, `difflib`
- **Optional dependency**: `rich` for coloured output, tables, and prompts. Recommended but not required — falls back to plain `print` / `input` gracefully.
- **Dev tools** (already in project): `pytest`, `ruff`
- **No external APIs, no network, no database.** All data ships as files in the repo.

---

## 3. Project Structure

```
jet-lag-the-game/
├── main.py                          # Thin entry: calls cli.run()
├── pyproject.toml                   # Already exists
├── README.md
├── data/
│   ├── countries.json               # Registry of available countries
│   └── uk/
│       ├── config.json              # UK game rules & penalties
│       ├── stations.json            # Normalised from train_stations.csv
│       ├── questions.json           # The 37 questions + metadata
│       └── regions.json             # Region adjacency map
├── scripts/
│   └── build_uk_data.py             # One-off: CSV → stations.json
├── src/
│   ├── __init__.py
│   ├── cli.py                       # Input/output loop (only I/O layer)
│   ├── models.py                    # @dataclass: Station, Question, Config
│   ├── data_loader.py               # Loads + validates JSON files
│   ├── game_state.py                # Pure state + transitions (no I/O)
│   ├── answer_engine.py             # Resolves questions from station data
│   ├── hint_engine.py               # Generates hints
│   ├── guess_engine.py              # Compares guesses (fuzzy match)
│   └── timer.py                     # Wall-clock + penalty tracking
└── tests/
    ├── __init__.py
    ├── test_data_loader.py
    ├── test_answer_engine.py
    ├── test_hint_engine.py
    ├── test_guess_engine.py
    ├── test_game_state.py
    └── test_timer.py
```

Key principle: **I/O lives only in `cli.py`**. Everything else is pure functions and data — which is why every other module is trivially testable with pytest.

---

## 4. Data Model

All runtime data is represented with `@dataclass` (frozen where possible) so the engine is type-friendly and test-friendly.

### 4.1 Station (`models.py`)
```python
@dataclass(frozen=True)
class Station:
    id: str                      # slug: "london-paddington"
    name: str                    # "London Paddington"
    operators: tuple[str, ...]   # ("Great Western Railway", "Elizabeth line", ...)
    postcode: str                # "W2 1HQ"
    postcode_area: str           # "W" — leading letters only
    cardinal_direction: str      # "North" | "South" | "East" | "West" | "Central"
    region: str                  # "London"
    closest_major_city: str      # "London"
    landmarks: tuple[str, ...]   # ("Paddington Bear Statue", ...) — "None" filtered
```

### 4.2 Question
```python
@dataclass(frozen=True)
class Question:
    id: str                      # "q_first_letter"
    text: str                    # "What is the first letter of your station name?"
    answer_type: str             # "yes_no" | "value" | "multi_choice"
    resolver: str                # Name of function in answer_engine
    answerable_always: bool      # False means hider may decline
    penalty_minutes: int         # Usually 3
```

### 4.3 Country config
```python
@dataclass(frozen=True)
class CountryConfig:
    country_id: str              # "UK"
    label: str                   # "United Kingdom"
    stations_file: str
    questions_file: str
    regions_file: str
    wrong_guess_penalty_min: int # 1
    question_penalty_min: int    # 3
    hint_penalty_min: int        # 0
    unanswered_limit: int        # 3
    intercity_operators: tuple[str, ...]
    sleeper_operators: tuple[str, ...]
```

### 4.4 Game state
```python
@dataclass
class GameState:
    phase: str                                 # "setup" | "playing" | "ended"
    country: CountryConfig
    all_stations: tuple[Station, ...]
    hider_station: Station
    seeker_station: Station
    start_time: float                          # time.monotonic()
    end_time: float | None
    end_reason: str | None                     # "found" | "gave_up" | "unanswered_limit"
    penalty_seconds: int
    history: list[HistoryEvent]
    asked_question_ids: set[str]
    revealed_hint_types: set[str]
    unanswered_count: int
```

---

## 5. Game Flow

```
START
  │
  ▼
[cli] pick country (only UK for now, but menu is data-driven)
  │
  ▼
[engine] pick random hider station
[engine] pick 3 random starting stations (excluding hider's)
  │
  ▼
[cli] seeker picks one of 3 → SETUP done
  │
  ▼
[engine] record start_time = time.monotonic()
  │
  ▼
┌─ PLAYING LOOP ─────────────────────────────────────────────┐
│  [cli] show menu:                                          │
│    1) Ask a question                                       │
│    2) Request a hint                                       │
│    3) Make a guess                                         │
│    4) Give up                                              │
│    5) Show history                                         │
│    6) Show current time + penalties                        │
│                                                            │
│  1 → pick question → engine answers → show answer          │
│      answerable: +3 min penalty                            │
│      unanswerable: no penalty, unanswered_count += 1       │
│      if unanswered_count ≥ limit → END (unanswered_limit)  │
│                                                            │
│  2 → engine picks unseen hint → show it → no penalty       │
│                                                            │
│  3 → seeker types guess →                                  │
│      match → END (found)                                   │
│      near-match → show suggestion, do NOT auto-accept      │
│      no match → +1 min penalty, continue                   │
│                                                            │
│  4 → confirm → END (gave_up)                               │
└────────────────────────────────────────────────────────────┘
  │
  ▼
[cli] show end screen: hider station + full details + final time + breakdown
  │
  ▼
[cli] play again? (y/n)
```

### Ambiguity flagged
Your original spec is truncated: *"If the hider is unable to answer 3 questions during the game,"* — the sentence ends there. **Default assumption**: game ends, hider station revealed, marked as `unanswered_limit`. Made configurable via `unanswered_limit` in config. Task 16 calls this out so you can confirm the intended behaviour.

---

## 6. Answer Engine

`answer_engine.py` exposes a single public function:

```python
def answer_question(
    question: Question,
    hider: Station,
    seeker: Station,
    all_stations: tuple[Station, ...],
    config: CountryConfig,
    regions_map: dict[str, tuple[str, ...]],
) -> AnswerResult: ...
```

Where `AnswerResult` is:
```python
@dataclass(frozen=True)
class AnswerResult:
    answerable: bool
    answer: str | None          # formatted for display, None if unanswerable
    reason: str | None          # only set if answerable is False
```

Dispatch is done via a dict `RESOLVERS: dict[str, Callable]` keyed by `question.resolver`. Adding a new resolver = add one function and one dict entry.

### Full mapping of all 37 questions

| # | Question | `resolver` | Answerable? |
|---|---|---|---|
| 1 | First letter of name | `first_letter_of_name` | always |
| 2 | Last letter of name | `last_letter_of_name` | always |
| 3 | Single word name? | `is_single_word` | always |
| 4 | Two or more words? | `is_multi_word` | always |
| 5 | Longer than 10 chars? | `name_longer_than_10` | always |
| 6 | Contains West/East? | `contains_west_or_east` | always |
| 7 | Contains North/South? | `contains_north_or_south` | always |
| 8 | Contains compass word? | `contains_compass_word` | always |
| 9 | Contains "New"? | `contains_new` | always |
| 10 | Contains King/Queen? | `contains_king_or_queen` | always |
| 11 | Contains "St"? | `contains_saint` | always |
| 12 | Contains Street/Road/Junction/Central/Parkway? | `contains_suffix_word` | always |
| 13 | Contains "Park"? | `contains_park` | always |
| 14 | Contains "&"? | `contains_ampersand` | always |
| 15 | Has bracketed qualifier? | `has_bracketed_qualifier` | always |
| 16 | Welsh/Scottish prefix? | `has_celtic_prefix` | always |
| 17 | Shares ≥2 letters with seeker's? | `shares_n_letters_2` | always |
| 18 | Shares >3 letters with seeker's? | `shares_more_than_3_letters` | always |
| 19 | Shares any vowels with seeker's? | `shares_vowels` | always |
| 20 | In London? | `is_in_london` | always |
| 21 | In Scotland/Wales/England? | `country_of_uk` | always |
| 22 | What region? | `region_name` | always (reveals value) |
| 23 | Same region as seeker? | `same_region_as_seeker` | always |
| 24 | Cardinal direction? | `cardinal_direction` | always (reveals value) |
| 25 | Same cardinal as seeker? | `same_cardinal_as_seeker` | always |
| 26 | Regions border each other? | `regions_border` | always (uses `regions.json`) |
| 27 | Closest major city? | `closest_major_city` | always (reveals value) |
| 28 | Same major city as seeker? | `same_major_city_as_seeker` | always |
| 29 | Closest city Manchester/Liverpool? | `city_is_manchester_or_liverpool` | always |
| 30 | Same TOC as seeker? | `shares_operator` | always |
| 31 | Served by >1 TOC? | `has_multiple_operators` | always |
| 32 | Served by intercity operator? | `has_intercity_operator` | always (list from config) |
| 33 | Served by sleeper? | `has_sleeper_operator` | always (list from config) |
| 34 | Connected to airport? | `is_airport_station` | **unanswerable** (data not in CSV) |
| 35 | Would seeker pass through? | `passes_through_seeker` | **unanswerable** (no route data) |
| 36 | Same postcode area letters? | `same_postcode_area` | always |
| 37 | Postcode starts with vowel? | `postcode_starts_with_vowel` | always |

### Country mapping (for Q21)
London, South East, South West, East of England, East Midlands, West Midlands, Yorkshire and the Humber, North East, North West → **England**.
Wales → **Wales**. Scotland → **Scotland**.

### Unanswerable behaviour
Q34 and Q35 return `AnswerResult(answerable=False, answer=None, reason="Route/airport data not available in this dataset")`. The game state bumps `unanswered_count` but does **not** apply the 3-minute penalty.

---

## 7. Hint Engine

`hint_engine.py`:

```python
def generate_hint(station: Station, revealed_types: set[str], rng: random.Random | None = None) -> Hint | None: ...
```

Hint sources (each is a function `(Station) -> str | None`; skipped if `type` already in `revealed_types`):
- `region` → "This station is in the *South East* region."
- `cardinal` → "This station is in the *South* of the UK."
- `major_city` → "The closest major city is *Manchester*."
- `landmark` → "A nearby landmark is *the Gherkin*." (random from list)
- `postcode_area` → "The postcode starts with *EC*."
- `operator` → "This station is served by *Greater Anglia*." (random from list)
- `name_length` → "The station name has 14 characters."
- `first_letter` → "The first letter of the name is *L*."
- `last_letter` → "The last letter of the name is *n*."

Returns `None` when all sources are exhausted.

---

## 8. Guess Engine

`guess_engine.py`:

```python
def check_guess(raw_input: str, hider: Station, all_stations: tuple[Station, ...]) -> GuessResult: ...
```

Where:
```python
@dataclass(frozen=True)
class GuessResult:
    correct: bool
    suggestion: str | None       # closest match if wrong but close
```

Logic:
1. Normalise both sides: `lower().strip()`, collapse whitespace, strip punctuation (`re.sub(r"[^\w\s]", "", s)`).
2. Exact match after normalisation → `correct=True`.
3. Otherwise, use `difflib.get_close_matches(raw, [s.name for s in all_stations], n=1, cutoff=0.85)` (stdlib — no extra dep); if a match comes back → `suggestion` set.
4. Seeker must re-type the suggested name to accept — no auto-correction.

---

## 9. Timer

`timer.py`:

```python
def now() -> float: ...                               # time.monotonic() wrapper
def elapsed_seconds(start: float, end: float | None) -> int: ...
def format_duration(seconds: int) -> str: ...         # "12:34"
def final_breakdown(state: GameState) -> TimerBreakdown: ...
```

`TimerBreakdown` contains elapsed, penalty minutes from questions, penalty minutes from wrong guesses, total — displayed at end of game.

---

## 10. CLI Layer (`cli.py`)

This is the **only** module with `input()` and `print()` calls. Everything else is pure.

```python
def run() -> int: ...   # returns exit code
```

Responsibilities:
- Main menu loop (country picker, new game, quit).
- Rendering each phase of the game (setup, playing, end).
- Building menus of questions with numbers for selection.
- Accepting a free-text guess; if engine returns a suggestion, prompt "Did you mean X? (y/n)" — on y, re-submit that exact string as a new guess.
- Formatting answers nicely: boolean → "Yes" / "No", values displayed plainly.
- Handling `Ctrl+C` → graceful quit with station reveal.

### Optional: `rich`
If `rich` is available (detected via `try: import rich`), use its `Console`, `Panel`, `Prompt.ask()`, and `Table` for a nicer UX. Otherwise fall back to plain `print` / `input`. This keeps stdlib-only runs viable.

### `main.py`
Three lines:
```python
from src.cli import run

def main() -> int:
    return run()
```

This matches `[project.scripts] game = "main:main"` in `pyproject.toml`.

---

## 11. Extensibility (explicit)

### Add a new question
1. Open `data/uk/questions.json`.
2. Append a new object with `id`, `text`, `resolver`, `answer_type`, `answerable_always`, `penalty_minutes`.
3. If the `resolver` name already exists → **zero code change**.
4. If it needs new logic → add one function to `answer_engine.py` and add one line to the `RESOLVERS` dict.

### Add a new country
1. Extract the CSV with the same column schema.
2. Create `data/xx/stations.json`, `data/xx/questions.json`, `data/xx/regions.json`, `data/xx/config.json`.
3. Append an entry to `data/countries.json`.
4. The country picker in `cli.py` reads `countries.json` — it'll appear automatically.

### Add a new hint type
1. Add a function to `hint_engine.py` returning `(type_name, text)`.
2. Register it in the `HINT_SOURCES` list.

### Change penalties or limits
Edit `data/uk/config.json`. No code changes.

---

## 12. Structured Tasks for Execution Agents

Each task is self-contained, has clear inputs and acceptance criteria, and lists its dependencies. Tests should be written alongside implementation (pytest is already a dev dependency).

---

### TASK 1 — Build data directory layout and country registry
**Depends on**: none
**Deliverables**: `data/countries.json`, empty `data/uk/` directory
**Steps**:
1. Create `data/countries.json`: `[{"id": "UK", "label": "United Kingdom", "config_path": "data/uk/config.json"}]`.
2. Create the `data/uk/` directory (later tasks populate it).
**Acceptance**: `data/countries.json` parses as valid JSON, lists exactly one country.

---

### TASK 2 — Write CSV-to-JSON converter script
**Depends on**: Task 1
**Deliverable**: `scripts/build_uk_data.py`
**Inputs**: `train_stations.csv`
**Output**: `data/uk/stations.json`
**Steps**:
1. Use Python's stdlib `csv.DictReader` — it handles the quoted multi-value column correctly.
2. For each row, produce a dict matching `Station` in §4.1.
3. Split `Train Operating Companies / Lines` on `,`, strip each element.
4. Derive `postcode_area` via `re.match(r"^[A-Z]+", postcode).group()`.
5. Build `landmarks` array from Landmark 1/2/3, dropping any equal to `"None"` or empty string.
6. Slug the `id`: lowercase, strip punctuation, spaces → hyphens.
7. Write `data/uk/stations.json` as a JSON array with `indent=2`.
8. Script should be runnable standalone: `python scripts/build_uk_data.py`.
**Acceptance**: Output file has exactly 1,666 records; every record has all fields; operators is an array; landmarks arrays never contain `"None"`; `id` values are unique.

---

### TASK 3 — Build the UK questions JSON
**Depends on**: Task 1
**Deliverable**: `data/uk/questions.json`
**Steps**:
1. For each of the 37 questions in `seeker_questions.md`, create one object matching the schema in §4.2.
2. Use the resolver names from the table in §6.
3. `answerable_always: false` for Q34 and Q35; `true` for all others.
4. `penalty_minutes: 3` for every question.
5. `id`s should be stable and descriptive (e.g. `q_first_letter`, `q_contains_new`, `q_same_region`).
**Acceptance**: 37 objects in valid JSON. Schema check passes (see Task 7's validation).

---

### TASK 4 — Build the region adjacency map
**Depends on**: Task 1
**Deliverable**: `data/uk/regions.json`
**Steps**:
1. Object keyed by region name, value = array of bordering region names.
2. Use these adjacencies (symmetric — if A borders B, ensure B also borders A):
   - **London** ↔ South East, East of England
   - **South East** ↔ London, South West, East of England, West Midlands
   - **South West** ↔ South East, West Midlands, Wales
   - **East of England** ↔ London, South East, East Midlands
   - **East Midlands** ↔ East of England, West Midlands, Yorkshire and the Humber, North West
   - **West Midlands** ↔ South East, South West, East Midlands, North West, Wales
   - **Yorkshire and the Humber** ↔ East Midlands, North West, North East
   - **North West** ↔ West Midlands, East Midlands, Yorkshire and the Humber, North East, Wales, Scotland
   - **North East** ↔ Yorkshire and the Humber, North West, Scotland
   - **Wales** ↔ South West, West Midlands, North West
   - **Scotland** ↔ North East, North West
**Acceptance**: Valid JSON. Symmetry test passes (every listed adjacency is reciprocated).

---

### TASK 5 — Build the UK config JSON
**Depends on**: Tasks 2, 3, 4
**Deliverable**: `data/uk/config.json`
**Steps**:
1. Create config per §4.3:
   - `country_id`: "UK"
   - `label`: "United Kingdom"
   - `stations_file`: "data/uk/stations.json" (relative to project root)
   - `questions_file`: "data/uk/questions.json"
   - `regions_file`: "data/uk/regions.json"
   - `wrong_guess_penalty_min`: 1
   - `question_penalty_min`: 3
   - `hint_penalty_min`: 0
   - `unanswered_limit`: 3
   - `intercity_operators`: `["Avanti West Coast", "LNER", "CrossCountry", "Great Western Railway", "GWR"]`
   - `sleeper_operators`: `["Caledonian Sleeper", "Night Riviera"]`
**Acceptance**: Valid JSON. All referenced files exist.

---

### TASK 6 — Implement `models.py`
**Depends on**: none
**Deliverable**: `src/models.py`
**Steps**:
1. Define `Station`, `Question`, `CountryConfig`, `AnswerResult`, `GuessResult`, `Hint`, `HistoryEvent`, `GameState`, `TimerBreakdown` as `@dataclass`.
2. Use `frozen=True` where appropriate (Station, Question, CountryConfig, AnswerResult, GuessResult, Hint).
3. Use `tuple[...]` (not `list[...]`) for fields on frozen dataclasses.
4. Add a `from_dict` classmethod to `Station`, `Question`, `CountryConfig` for loading from JSON.
**Acceptance**: `python -c "from src.models import Station; print(Station)"` runs. Dataclasses instantiable from JSON dicts.

---

### TASK 7 — Implement `data_loader.py`
**Depends on**: Tasks 1–6
**Deliverable**: `src/data_loader.py`
**Steps**:
1. `load_countries() -> list[dict]` → reads `data/countries.json`.
2. `load_config(path: str) -> CountryConfig` → loads and validates a config JSON.
3. `load_stations(config: CountryConfig) -> tuple[Station, ...]` → reads stations file, builds Station objects.
4. `load_questions(config: CountryConfig) -> tuple[Question, ...]` → reads questions file.
5. `load_regions(config: CountryConfig) -> dict[str, tuple[str, ...]]` → reads region adjacency.
6. Validation: raise `ValueError` with a clear message if any file is malformed or missing required fields.
7. All paths resolved relative to project root (use `pathlib.Path(__file__).parent.parent`).
**Acceptance**: `test_data_loader.py` passes — loads UK data fully and asserts 1,666 stations, 37 questions, 11 regions.

---

### TASK 8 — Implement `answer_engine.py`
**Depends on**: Tasks 6, 7
**Deliverable**: `src/answer_engine.py`
**Steps**:
1. Implement every resolver function from the §6 table. Each takes `(hider: Station, seeker: Station, all_stations, config, regions_map)` and returns `AnswerResult`.
2. Build the `RESOLVERS: dict[str, Callable]` dispatch table.
3. Expose public `answer_question(question, hider, seeker, all_stations, config, regions_map) -> AnswerResult`.
4. For the "shares N letters" resolvers — compare sets of unique letters (case-insensitive, excluding spaces), count intersection size.
5. For "shares vowels" — intersect vowel sets `{a, e, i, o, u}` (case-insensitive).
6. For `country_of_uk` — return "England", "Scotland", or "Wales" based on the region mapping in §6.
7. For `regions_border` — look up `regions_map[seeker.region]` and check if `hider.region` is in it.
8. `is_airport_station` and `passes_through_seeker` return `AnswerResult(answerable=False, answer=None, reason="...")`.
9. Format answers for display: `"Yes"` / `"No"` for yes-no; the raw value for `value` types.
**Tests** (`test_answer_engine.py`): At minimum cover first_letter, single_word, is_in_london, shares_vowels, regions_border, has_intercity_operator, unanswerable cases. Use 3–5 real stations from the CSV.
**Acceptance**: Every question ID in `questions.json` resolves without raising. Tests pass.

---

### TASK 9 — Implement `hint_engine.py`
**Depends on**: Task 6
**Deliverable**: `src/hint_engine.py`
**Steps**:
1. Define `HINT_SOURCES: list[tuple[str, Callable[[Station], str | None]]]` with the 9 sources from §7.
2. `generate_hint(station, revealed_types, rng=None)` picks a random unseen source, calls it, returns `Hint(type=..., text=...)` or `None` if exhausted.
3. Sources that could return empty (e.g. no landmarks) should return `None` and be skipped.
4. Accept optional `random.Random` param for deterministic testing.
**Tests**: Request hints repeatedly for one station with a seeded RNG; assert each hint type is unique; assert `None` returned after all exhausted.
**Acceptance**: Deterministic with seeded RNG.

---

### TASK 10 — Implement `guess_engine.py`
**Depends on**: Task 6
**Deliverable**: `src/guess_engine.py`
**Steps**:
1. `_normalise(s: str) -> str` — lowercase, strip, collapse whitespace, remove punctuation.
2. `check_guess(raw, hider, all_stations) -> GuessResult`:
   - If `_normalise(raw) == _normalise(hider.name)` → `GuessResult(correct=True, suggestion=None)`.
   - Else use `difflib.get_close_matches(raw, [s.name for s in all_stations], n=1, cutoff=0.85)` for a suggestion.
   - Return `GuessResult(correct=False, suggestion=...)`.
**Tests**: Exact match, case-insensitive match, extra-whitespace match, near-match suggestion, no-match case.
**Acceptance**: `"london paddington"`, `"London Paddington"`, `"  LONDON  PADDINGTON  "` all match. `"londn paddington"` returns a suggestion.

---

### TASK 11 — Implement `timer.py`
**Depends on**: Task 6
**Deliverable**: `src/timer.py`
**Steps**:
1. `now() -> float` — wraps `time.monotonic()` (so tests can monkeypatch).
2. `elapsed_seconds(start, end) -> int` — `end or now()` minus start, integer.
3. `format_duration(seconds) -> str` — `"MM:SS"` format.
4. `final_breakdown(state) -> TimerBreakdown` — compute elapsed + penalty breakdown, return dataclass.
**Tests**: Format edge cases (0s, 59s, 3600s). Breakdown sums correctly.
**Acceptance**: Tests pass.

---

### TASK 12 — Implement `game_state.py`
**Depends on**: Tasks 6–11
**Deliverable**: `src/game_state.py` — pure state transitions, no I/O
**Steps**:
1. `start_game(config, stations, rng) -> GameState` — picks hider, picks 3 starting options, returns state in "setup" phase with the 3 options stored.
2. `select_starting_station(state, chosen_id) -> GameState` — transitions to "playing", records `start_time`.
3. `ask_question(state, question, regions_map) -> tuple[GameState, AnswerResult]` — calls answer engine; updates penalties, `asked_question_ids`, `unanswered_count`; auto-ends if unanswered limit hit.
4. `request_hint(state, rng) -> tuple[GameState, Hint | None]` — calls hint engine; updates `revealed_hint_types`.
5. `make_guess(state, raw_input) -> tuple[GameState, GuessResult]` — wrong → +1 min penalty; correct → ends with reason "found".
6. `give_up(state) -> GameState` — ends with reason "gave_up".
7. Every transition appends a `HistoryEvent` to `state.history`.
8. All functions are pure: same inputs → same outputs (given the same RNG). No `print` / `input`.
**Tests** (`test_game_state.py`): Full happy-path game (start → ask → hint → wrong guess → correct guess → ended). Unanswered-limit end. Give-up end. Penalty accumulation.
**Acceptance**: No I/O calls anywhere in this module. Tests pass.

---

### TASK 13 — Implement `cli.py`
**Depends on**: all above
**Deliverable**: `src/cli.py`
**Steps**:
1. `run() -> int` main entry.
2. Menu loop: "New game" / "Quit".
3. Country picker (reads `countries.json`).
4. During setup: present 3 starting station options as a numbered menu.
5. Playing loop: numbered menu with 6 options (§5), read input, dispatch to state functions, render result.
6. For "Ask a question": paginate the 37 questions (e.g. 10 per page), let user pick by number. Hide or grey out already-asked. Show penalty next to each.
7. For "Make a guess": free-text input. After submission, if `suggestion` returned, ask "Did you mean X? (y/n)" — on y, treat as a fresh guess of that string.
8. End screen: show hider station name + region + closest city + all landmarks + postcode, plus formatted timer breakdown.
9. Graceful `KeyboardInterrupt` handling → "Exiting. The hider was at X." confirmation.
10. Optionally detect and use `rich` if installed.
**Acceptance**: `uv run game` launches the game end-to-end. Every menu option reachable. No crashes on common inputs.

---

### TASK 14 — Wire up `main.py`
**Depends on**: Task 13
**Deliverable**: `main.py`
**Steps**:
```python
from src.cli import run

def main() -> int:
    return run()

if __name__ == "__main__":
    raise SystemExit(main())
```
**Acceptance**: `uv run game` works. Running `python main.py` also works.

---

### TASK 15 — Write README
**Depends on**: all above
**Deliverable**: `README.md`
**Content**:
- Quick start: `uv sync`, `uv run game`.
- How to play (menu explanation, penalty structure).
- Data regeneration: `python scripts/build_uk_data.py`.
- **How to add a new question** (see §11).
- **How to add a new country** (see §11).
- **How to add a new hint type** (see §11).
- Data schema reference for stations / questions / regions / config.
- Running tests: `uv run pytest`.
**Acceptance**: A fresh developer can add a demo question by reading only the README.

---

### TASK 16 — Confirm ambiguous spec rule
**Depends on**: none (flag early, before Task 12)
**Action**: Your original spec ends mid-sentence: *"If the hider is unable to answer 3 questions during the game,"* — intent unclear. Default implementation: game ends, reveal station, mark as `unanswered_limit`. Configured via `unanswered_limit` in `config.json`. Surface a `# TODO(user): confirm intended behaviour` comment at the relevant spot in `game_state.py`.

---

## 13. Suggested Additional Questions (for later)

These extend the bank and all map to data already in the CSV — most need only trivial resolver additions:

1. **Is the closest major city to your station London?** (narrows the big London cluster)
2. **Is your station in England?** (boolean version of Q21)
3. **Is your station's cardinal direction "Central"?**
4. **Does your station's name contain a digit?**
5. **Is any of your landmarks a bridge / cathedral / palace / museum?** (keyword probe over landmarks)
6. **Is your station served by the Elizabeth line?** (specific-operator probe)
7. **Does your postcode start with a digit after the letters?**
8. **Does your station have more than one landmark listed?** (proxy for "popular station")
9. **Is your station in one of the Home Counties?** (South East + East of England)
10. **Does your station name start with the same letter as the seeker's?** (letter-overlap probe)

The README (Task 15) explains how to add these by editing `questions.json` alone.

---

## 14. Out of Scope

- Real route / pathfinding for Q35 ("would you pass through my station") — no rail graph data.
- Airport connection data for Q34 — not in the CSV. Could be added as an extra column later.
- Multiplayer / AI-seeker mode — not requested.
- Persistent high scores / leaderboards — not requested (trivial to add by writing to a JSON file in the home directory, but deferred).
- Difficulty levels (restricted question bank, fewer hints) — easy to add after core is done.
- GUI / web version — this plan is CLI-only.

---

## 15. Test Coverage Expectations

At minimum these should be green before handing off:
- `test_data_loader.py`: UK data loads; correct counts; malformed JSON raises.
- `test_answer_engine.py`: 8–10 resolvers across the different answer types; unanswerable cases.
- `test_hint_engine.py`: Exhaustion behaviour; no repeats.
- `test_guess_engine.py`: Exact, normalised, and near-match paths.
- `test_timer.py`: Format edge cases; breakdown sums.
- `test_game_state.py`: Full happy path; unanswered-limit path; give-up path; penalty accumulation.

Run via `uv run pytest`.
