This is a project where I am working to make hide and seek a video game that is loosely based on the associated following youtube series:
1. "Jet Lag: The Game" by Sam Denby and his friends. (https://www.youtube.com/@JetLagTheGame)
2. "The Hide and Seek World Championship" by Tom Scott.

This project is intended for educational purposes only, and is not intended for commercial use.

Inspirations:
1. https://www.youtube.com/watch?v=Zftv6Kh2zi4&list=PLB7ZcpBcwdC5aiPqLOh4v2mGGxm2_gmu6
2. https://www.youtube.com/playlist?list=PLB7ZcpBcwdC5V7encRbWQdst2keI78jyL
3. https://www.youtube.com/playlist?list=PLB7ZcpBcwdC79KvPUh76PhFZ8x7q18hOW

The main game is a text-based terminal game. The human plays as the seeker and must locate the computer hider's hidden UK rail station using questions, hints, and guesses. Time is the score.

---

## Running the game

```
uv run python main.py
```

## Running tests

```
uv run pytest
```

## Linting

```
uv run ruff check
```

---

## Developer guide

### Adding a new question

1. Open `data/questions.uk.json`.
2. Append a new object following this schema:

```json
{
  "id": "q38",
  "text": "Is your station in England?",
  "answerType": "yes_no",
  "resolver": "countryOfUK",
  "answerableAlways": true,
  "penaltyMinutes": 3
}
```

Fields:

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique identifier. Use the next sequential `q##` number. |
| `text` | string | Question text shown to the seeker. |
| `answerType` | string | `"yes_no"`, `"value"`, or `"multi_choice"`. |
| `resolver` | string | Name of the resolver function in `src/answer_engine.py`. |
| `answerableAlways` | bool | `false` means the hider may decline (currently only Q34 and Q35). |
| `penaltyMinutes` | int | Minutes added to the seeker's time when the question is asked. |

If the new question maps to an existing resolver (see the resolver table below), no code changes are needed. The UI and engine will pick up the new question automatically.

If the question needs new logic, add one function to `src/answer_engine.py` and register it in the `RESOLVER_MAP` dict at the bottom of that file. The function signature is:

```python
def my_resolver(hider: dict, seeker: dict, all_stations: list, config: dict) -> dict:
    ...
    return {"answerable": True, "answer": <value>}
    # or
    return {"answerable": False, "reason": "explanation"}
```

### Adding a new country

Three JSON files and one config entry are required. No code changes.

1. Create `data/stations.xx.json` — a list of station records (see schema below).
2. Create `data/questions.xx.json` — a list of question records (can reuse the UK file).
3. Create `data/regions.xx.json` — a region adjacency map (see schema below).
4. Create `data/config.xx.json` — the country config (see schema below).
5. Open `data/countries.json` and add an entry:

```json
{ "id": "XX", "label": "Country Name", "configFile": "config.xx.json" }
```

The country dropdown in the game is data-driven from `countries.json` and will display the new country automatically.

### Adding a new hint type

1. Open `src/hint_engine.py`.
2. Add a new function following this pattern:

```python
def _hint_my_type(station: dict) -> Optional[str]:
    """Return a my-type hint for the station.

    Args:
        station: Station record dict.

    Returns:
        A hint string, or None if the data is unavailable.
    """
    value = station.get("myField", "")
    if not value:
        return None
    return f"The station's my-field is: {value}."
```

3. Register the function in the `_HINT_SOURCES` list:

```python
_HINT_SOURCES: list[tuple[str, object]] = [
    ...
    ("myType", _hint_my_type),
]
```

The `type` key (first element of the tuple) must be unique. It is used to track which hints have already been revealed to the seeker.

### Changing penalties and limits

All penalty values and game limits are stored in `data/config.uk.json` (or the equivalent file for another country). No code changes are needed.

```json
{
  "penalties": {
    "wrongGuess": 1,
    "question": 3,
    "hint": 0
  },
  "unansweredQuestionLimit": 3,
  "unansweredLimitBehaviour": "end_game"
}
```

| Key | Description |
|---|---|
| `penalties.wrongGuess` | Minutes added per wrong guess. |
| `penalties.question` | Minutes added per question asked (overridden per question by `penaltyMinutes`). |
| `penalties.hint` | Minutes added per hint (currently 0). |
| `unansweredQuestionLimit` | Number of unanswerable questions before the game ends. |
| `unansweredLimitBehaviour` | Behaviour when limit is reached. Currently only `"end_game"` is implemented. |

---

## Data schemas

### Station record (`stations.uk.json`)

```json
{
  "id": "london-paddington",
  "name": "London Paddington",
  "operators": ["Great Western Railway", "Heathrow Express", "Elizabeth line"],
  "postcode": "W2 1HQ",
  "postcodeArea": "W",
  "cardinalDirection": "South",
  "region": "London",
  "closestMajorCity": "London",
  "landmarks": ["Paddington Bear Statue", "Bishop's Bridge"]
}
```

| Field | Type | Description |
|---|---|---|
| `id` | string | Slug derived from name (lowercase, spaces to hyphens). |
| `name` | string | Full station name as it appears in the CSV. |
| `operators` | string[] | Train Operating Companies serving the station. |
| `postcode` | string | Full postcode. |
| `postcodeArea` | string | Leading letter(s) of the postcode (e.g. `W` or `EC`). |
| `cardinalDirection` | string | `North`, `South`, `East`, `West`, or `Central`. |
| `region` | string | One of the 11 UK regions listed below. |
| `closestMajorCity` | string | Nearest major city from the CSV data. |
| `landmarks` | string[] | Nearby landmarks. `"None"` values are filtered out. |

Valid regions: `London`, `South East`, `South West`, `East of England`, `East Midlands`, `West Midlands`, `Yorkshire and the Humber`, `North East`, `North West`, `Wales`, `Scotland`.

### Question record (`questions.uk.json`)

```json
{
  "id": "q01",
  "text": "What is the first letter of your station name?",
  "answerType": "value",
  "resolver": "firstLetterOfName",
  "answerableAlways": true,
  "penaltyMinutes": 3
}
```

### Region adjacency map (`regions.uk.json`)

```json
{
  "London": ["South East", "East of England"],
  "South East": ["London", "South West", "East of England", "West Midlands"],
  ...
}
```

The map is symmetric: if A borders B, then B must also list A. Used by the `regionsBorder` resolver (question Q26).

### Country config (`config.uk.json`)

```json
{
  "country": "UK",
  "label": "United Kingdom",
  "stationsFile": "stations.uk.json",
  "questionsFile": "questions.uk.json",
  "regionsFile": "regions.uk.json",
  "penalties": { "wrongGuess": 1, "question": 3, "hint": 0 },
  "unansweredQuestionLimit": 3,
  "unansweredLimitBehaviour": "end_game",
  "intercityOperators": ["Avanti West Coast", "LNER", "CrossCountry", "GWR", "Great Western Railway"],
  "sleeperOperators": ["Caledonian Sleeper", "Night Riviera"]
}
```

| Field | Description |
|---|---|
| `stationsFile` | Filename of the stations JSON inside `data/`. |
| `questionsFile` | Filename of the questions JSON inside `data/`. |
| `regionsFile` | Filename of the region adjacency JSON inside `data/`. |
| `intercityOperators` | List of operators considered intercity (used by Q32). |
| `sleeperOperators` | List of operators that run sleeper trains (used by Q33). |

---

## Resolver reference

All 37 resolvers and their question mappings:

| Question | Resolver key |
|---|---|
| First letter of name | `firstLetterOfName` |
| Last letter of name | `lastLetterOfName` |
| Single word name? | `isSingleWord` |
| Two or more words? | `isMultiWord` |
| Longer than 10 chars? | `nameLongerThan10` |
| Contains West/East? | `containsWestOrEast` |
| Contains North/South? | `containsNorthOrSouth` |
| Contains compass direction? | `containsCompassWord` |
| Contains "New"? | `containsNew` |
| Contains King/Queen? | `containsKingOrQueen` |
| Contains "St"? | `containsSaint` |
| Contains Street/Road/Junction/Central/Parkway? | `containsSuffixWord` |
| Contains "Park"? | `containsPark` |
| Contains "&"? | `containsAmpersand` |
| Has bracketed qualifier? | `hasBracketedQualifier` |
| Welsh/Scottish prefix? | `hasCelticPrefix` |
| Shares >= 2 letters with seeker's? | `sharesAtLeast2Letters` |
| Shares > 3 letters with seeker's? | `sharesMoreThan3Letters` |
| Shares any vowels with seeker's? | `sharesVowels` |
| In London? | `isInLondon` |
| In Scotland/Wales/England? | `countryOfUK` |
| What region? | `regionName` |
| Same region as seeker? | `sameRegionAsSeeker` |
| Cardinal direction? | `cardinalDirection` |
| Same cardinal as seeker? | `sameCardinalAsSeeker` |
| Regions border each other? | `regionsBorder` |
| Closest major city? | `closestMajorCity` |
| Same major city as seeker? | `sameMajorCityAsSeeker` |
| Closest city Manchester/Liverpool? | `cityIsManchesterOrLiverpool` |
| Same TOC as seeker? | `sharesOperator` |
| Served by > 1 TOC? | `hasMultipleOperators` |
| Served by intercity operator? | `hasIntercityOperator` |
| Served by sleeper? | `hasSleeperOperator` |
| Connected to airport? | `isAirportStation` (unanswerable — data not in CSV) |
| Would seeker pass through? | `passesThroughSeeker` (unanswerable — no route data) |
| Same postcode area letters? | `samePostcodeArea` |
| Postcode starts with vowel? | `postcodeStartsWithVowel` |

---

## Known limitations

- **Q34 (airport connection)** and **Q35 (route through seeker's station)** are marked unanswerable because the required data is not in the CSV. They count toward the `unansweredQuestionLimit`.
- The `unansweredQuestionLimit` behaviour (ending the game after 3 unanswerable questions) is a default assumption based on an incomplete spec sentence. This is surfaced as `config.unansweredLimitBehaviour` so it can be changed without code edits.
- No multiplayer, persistent leaderboards, or difficulty levels are implemented.
