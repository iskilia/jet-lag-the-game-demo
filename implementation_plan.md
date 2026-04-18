# Hide N Seek: UK Edition — Implementation Plan

## 1. Project Overview

A single-player web-based guessing game where the **human seeker** tries to locate a **computer hider** who has hidden at a UK National Rail station. The seeker uses questions, hints, and guesses to narrow down the location. Time is the score — the faster you find the hider, the better.

### Game Data Summary (from `train_stations.csv`)
- **1,666 stations** across the UK
- **Columns**: `Station`, `Train Operating Companies / Lines`, `Postcode`, `Cardinal Direction`, `Region`, `Closest Major City`, `Landmark 1`, `Landmark 2`, `Landmark 3`
- **Regions (11)**: London, South East, South West, East of England, East Midlands, West Midlands, Yorkshire and the Humber, North East, North West, Wales, Scotland
- **Cardinal Directions**: North, South, East, West, Central
- **Closest Major Cities**: London, Manchester, Liverpool, Edinburgh, Glasgow, Cardiff, Swansea
- **Notable parsing detail**: The `Train Operating Companies / Lines` column is a comma-separated list inside a single quoted CSV field (e.g. `"Great Western Railway,Heathrow Express,Elizabeth line"`). Must use a proper CSV parser.

---

## 2. Recommended Tech Stack

A single-file React artifact (`.jsx`) is the right choice: it renders in the Claude chat, has no backend, and supports the stateful UI this game needs. Alternative: HTML + vanilla JS for simpler deployment.

- **UI**: React with hooks (`useState`, `useEffect`, `useRef` for the timer)
- **Styling**: Tailwind utility classes
- **Data loading**: Ship the CSV parsed into JSON at build time, OR load and parse the CSV with PapaParse at runtime
- **No browser storage** — all game state lives in React state

---

## 3. Architecture & File Structure

Keep it modular so adding questions/countries later is trivial.

```
/src
  /data
    stations.uk.json          # Parsed from train_stations.csv
    questions.uk.json         # The 37 seeker questions + metadata
    regions.uk.json           # Region adjacency map for Q26
    config.uk.json            # Country-level config (penalties, labels)
  /engine
    gameState.js              # Pure state reducer
    answerEngine.js           # Answers questions from station data
    hintEngine.js             # Generates hints from CSV fields
    guessEngine.js            # Compares guesses (fuzzy match)
    timer.js                  # Timer logic + penalty tracking
  /components
    App.jsx                   # Root, country selector
    SetupScreen.jsx           # Starting station picker (3 random)
    GameScreen.jsx            # Main play UI
    QuestionPanel.jsx         # Question picker
    HintPanel.jsx             # Hint request
    GuessInput.jsx            # Autocomplete guess input
    HistoryLog.jsx            # Q&A / hint / guess history
    TimerDisplay.jsx          # Live timer + penalties
    EndScreen.jsx             # Reveal + final time
```

For an artifact, all of this collapses into one `.jsx` file, but the **logical separation above must be preserved as internal modules/functions** so extending is easy.

---

## 4. Data Model

### 4.1 Station record (normalised from CSV)
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
Notes:
- `postcodeArea` = leading letters of postcode (e.g. `W2 1HQ` → `W`, `EC2M 7PY` → `EC`).
- Filter out `"None"` values in landmarks.
- Pre-compute this once — don't parse the CSV on every game.

### 4.2 Question record
Each question is **self-describing** so the engine can answer it without hard-coded logic per question.
```json
{
  "id": "q_first_letter",
  "text": "What is the first letter of your station name?",
  "answerType": "value",                // "yes_no" | "value" | "multi_choice"
  "resolver": "firstLetterOfName",      // name of a function in answerEngine
  "answerableAlways": true,             // false means hider may decline
  "penaltyMinutes": 3
}
```

### 4.3 Country config
```json
{
  "country": "UK",
  "label": "United Kingdom",
  "stationsFile": "stations.uk.json",
  "questionsFile": "questions.uk.json",
  "regionsFile": "regions.uk.json",
  "penalties": { "wrongGuess": 1, "question": 3, "hint": 0 },
  "unansweredQuestionLimit": 3
}
```
Adding a new country = drop 3 JSON files + 1 config entry. No code changes.

### 4.4 Region adjacency (for Q26 — "Does my station's region border your station's region?")
```json
{
  "London": ["South East", "East of England"],
  "South East": ["London", "South West", "East of England", "West Midlands"],
  "...": "..."
}
```
This is a manually curated adjacency graph. Keep it in its own JSON file so corrections are easy.

---

## 5. Game Flow (State Machine)

```
IDLE
  └─> user picks country → SETUP
SETUP
  ├─ hider secretly picks random station
  ├─ seeker shown 3 random starting stations, picks one
  └─ timer starts → PLAYING
PLAYING  (loop)
  ├─ Ask Question   → answer shown, +3 min (or 0 if unanswerable)
  ├─ Request Hint   → hint shown, no penalty
  ├─ Make Guess
  │    ├─ correct → ENDED (found)
  │    └─ wrong   → +1 min, stay in PLAYING
  └─ Give Up        → ENDED (gave up)
ENDED
  └─ show hider station + final time + stats → back to IDLE
```

### Ambiguity to confirm with the user
The spec cuts off: *"If the hider is unable to answer 3 questions during the game,"* — the sentence is incomplete. **Assumption to flag**: interpret this as "the game ends / the seeker loses if 3 questions go unanswered." Task 12 below asks the implementer to surface this as a configurable rule (`unansweredQuestionLimit`) with a sensible default behaviour (end game, reveal station) and a TODO for the user to confirm.

---

## 6. Answer Engine — how each question is resolved

The answer engine is a dispatch table keyed by `question.resolver`. Each resolver receives `(hiderStation, seekerStation, allStations)` and returns `{ answerable: true|false, answer: ... }`.

Mapping of all 37 questions to resolver functions:

| # | Question | Resolver | Answerable? |
|---|---|---|---|
| 1 | First letter of name | `firstLetterOfName` | always |
| 2 | Last letter of name | `lastLetterOfName` | always |
| 3 | Single word name? | `isSingleWord` | always |
| 4 | Two or more words? | `isMultiWord` | always |
| 5 | Longer than 10 chars? | `nameLongerThan10` | always |
| 6 | Contains West/East? | `containsWestOrEast` | always |
| 7 | Contains North/South? | `containsNorthOrSouth` | always |
| 8 | Contains compass direction? | `containsCompassWord` | always |
| 9 | Contains "New"? | `containsNew` | always |
| 10 | Contains King/Queen? | `containsKingOrQueen` | always |
| 11 | Contains "St"? | `containsSaint` | always |
| 12 | Contains Street/Road/Junction/Central/Parkway? | `containsSuffixWord` | always |
| 13 | Contains "Park"? | `containsPark` | always |
| 14 | Contains "&"? | `containsAmpersand` | always |
| 15 | Has bracketed qualifier? | `hasBracketedQualifier` | always |
| 16 | Welsh/Scottish prefix? | `hasCelticPrefix` | always |
| 17 | Shares ≥2 letters with seeker's? | `sharesNLetters(2)` | always |
| 18 | Shares >3 letters with seeker's? | `sharesNLetters(4)` | always |
| 19 | Shares any vowels with seeker's? | `sharesVowels` | always |
| 20 | In London? | `isInRegion("London")` | always |
| 21 | In Scotland/Wales/England? | `countryOfUK` | always |
| 22 | What region? | `regionName` (reveals value) | always |
| 23 | Same region as seeker? | `sameRegionAsSeeker` | always |
| 24 | Cardinal direction? | `cardinalDirection` (reveals value) | always |
| 25 | Same cardinal as seeker? | `sameCardinalAsSeeker` | always |
| 26 | Regions border each other? | `regionsBorder` | always (uses adjacency file) |
| 27 | Closest major city? | `closestMajorCity` (reveals value) | always |
| 28 | Same major city as seeker? | `sameMajorCityAsSeeker` | always |
| 29 | Closest city Manchester/Liverpool? | `cityIsManchesterOrLiverpool` | always |
| 30 | Same TOC as seeker? | `sharesOperator` | always |
| 31 | Served by >1 TOC? | `hasMultipleOperators` | always |
| 32 | Served by intercity operator? | `hasIntercityOperator` | always (intercity list configured) |
| 33 | Served by sleeper? | `hasSleeperOperator` | always |
| 34 | Connected to airport? | `isAirportStation` | **unanswerable** (data not in CSV — see §7) |
| 35 | Would seeker pass through? | `passesThroughSeeker` | **unanswerable** (no route data) |
| 36 | Same postcode area letters? | `samePostcodeArea` | always |
| 37 | Postcode starts with vowel? | `postcodeStartsWithVowel` | always |

**Intercity operators list** (for Q32): `["Avanti West Coast", "LNER", "CrossCountry", "GWR", "Great Western Railway"]` — configurable.

**Sleeper operators list** (for Q33): `["Caledonian Sleeper", "Night Riviera"]` — configurable.

### Handling unanswerable questions
The hider returns `{ answerable: false }` when:
- Data isn't in the CSV (Q34 airport, Q35 route).
- Question references seeker context that isn't available.

When `answerable = false`: no time penalty, no increment of question count against the seeker, but **increment the `unansweredCount`**. When it hits `unansweredQuestionLimit`, trigger end-game (per §5 assumption).

---

## 7. Hint Engine

A hint randomly picks a CSV field the seeker hasn't seen yet and reveals it. Hint sources in priority-random order:
- Region
- Cardinal direction
- Closest major city
- A random landmark near the station
- Postcode area (first letters only, not full postcode)
- A single operator serving the station
- Name length in characters
- First or last letter of the name

Track which hints have been revealed so repeats don't happen. When exhausted, return "No more hints available."

---

## 8. Guess Engine

- **Input**: free-text typed by seeker, with autocomplete from the stations list.
- **Match rule**: normalise both sides (lowercase, trim, collapse whitespace, strip punctuation). Exact match after normalisation = correct.
- **Fuzzy suggestion**: if no exact match, show "Did you mean: *London Paddington*?" using Levenshtein distance ≤ 2 — but do **not** auto-accept. The seeker must confirm.
- Wrong guess → +1 min, logged in history.

---

## 9. Timer & Scoring

- Real elapsed time (wall clock) from game start to end.
- Penalties added on top: `final = elapsed + (questions × 3min) + (wrongGuesses × 1min)`.
- Display live: `MM:SS` elapsed, plus a breakdown of penalty minutes accrued.
- Freeze timer on game end.

---

## 10. UI Requirements

### Setup screen
- Country dropdown (only "United Kingdom" for now, but the dropdown must be data-driven from the country config list).
- "Start game" button → hider picks station, then shows 3 random starting stations as selectable cards.

### Main game screen (three panels side-by-side on desktop, stacked on mobile)
1. **Ask a Question** — dropdown or searchable list of all 37 questions. Shows penalty "+3 min" next to each. Disabled once asked (or allow re-ask with the original answer shown from history). Include a "Suggest a new question" free-text field that posts to a local list (non-functional placeholder, clearly marked as feedback only).
2. **Request a Hint** — button that reveals one unseen fact. Shows count remaining.
3. **Make a Guess** — autocomplete input + Submit button. "+1 min if wrong" shown.
4. **Give Up** — secondary-style button with confirmation modal.

### Persistent elements
- Timer (top, large).
- Seeker's starting station (always visible for reference).
- History log (chronological list of every question asked + answer, hint revealed, guess made + result).

### End screen
- "Found!" or "Gave up" banner.
- Reveal hider's station with all CSV details.
- Final time with breakdown.
- "Play again" button.

---

## 11. Extensibility Design (explicit)

The spec calls this out — here's how each piece is designed to extend:

**Adding a new question**: append one object to `questions.uk.json`. If it maps to an existing resolver, zero code change. If it needs new logic, add one function to `answerEngine.js` and reference it by name. **No changes to UI, engine dispatch, or penalty logic.**

**Adding a new country**: drop three JSON files (`stations.xx.json`, `questions.xx.json`, `regions.xx.json`) and one config entry. The country dropdown picks it up automatically. Questions can be country-specific (e.g. US stations would have different operators and regions).

**Adding a new hint type**: append to the hint source list in `hintEngine.js`. Each hint source is a small function `(station) => string | null`.

**Changing penalties**: edit `config.uk.json` — no code touched.