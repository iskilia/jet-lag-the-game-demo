## Task Status Summary

| Task | Status | Notes |
|---|---|---|
| 1 — Parse and normalise station CSV | COMPLETE | `data/stations.uk.json`, 1,666 records |
| 2 — Build UK questions JSON | COMPLETE | `data/questions.uk.json`, 37 questions |
| 3 — Build region adjacency map | COMPLETE | `data/regions.uk.json` |
| 4 — Build country config | COMPLETE | `data/config.uk.json`, `data/countries.json` |
| 5 — Implement answer engine | COMPLETE | `src/answer_engine.py`, all 37 resolvers, tests pass |
| 6 — Implement hint engine | COMPLETE | `src/hint_engine.py` |
| 7 — Implement guess engine | COMPLETE | `src/guess_engine.py`, Levenshtein fuzzy match |
| 8 — Implement game state machine | COMPLETE | `src/game_state.py`, pure reducer, tests pass |
| 9 — Build UI components | COMPLETE | Adapted to terminal UI in `main.py` (not React — project is Python/terminal) |
| 10 — Handle edge cases and polish | COMPLETE | All 6 edge cases addressed |
| 11 — Document extensibility | COMPLETE | `README.md` updated with full developer guide |
| 12 — Confirm ambiguous spec rule | COMPLETE | Surfaced as `unansweredLimitBehaviour` in config; flagged in `main.py` |

---

## 12. Structured Tasks for Execution Agents

Each task below is self-contained and ready to hand to an execution agent. Dependencies are listed.

---

### TASK 1 — Parse and normalise the station CSV
**Depends on**: none
**Inputs**: `/mnt/user-data/uploads/train_stations.csv`
**Deliverable**: `stations.uk.json`
**Steps**:
1. Use a proper CSV parser (Python `csv` module, PapaParse, etc.) — the file has quoted fields containing commas.
2. For each row, produce the normalised record shape in §4.1.
3. Split `Train Operating Companies / Lines` on comma → trimmed array.
4. Derive `postcodeArea` = leading letters of the postcode (regex `^[A-Z]+`).
5. Filter `"None"` out of landmarks; keep array of real ones.
6. Generate a slug `id` from the name (lowercase, spaces → hyphens).
**Acceptance**: JSON file with exactly 1,666 records, all fields present, operators are arrays, landmarks arrays contain no `"None"`.

---

### TASK 2 — Build the UK questions JSON
**Depends on**: none (can run in parallel with Task 1)
**Deliverable**: `questions.uk.json`
**Steps**:
1. For each of the 37 questions in `seeker_questions.md`, create one record matching §4.2 schema.
2. Set `resolver` per the mapping table in §6.
3. Set `answerableAlways: false` for Q34 and Q35; `true` for the rest.
4. All questions get `penaltyMinutes: 3`.
**Acceptance**: Valid JSON array of 37 objects, each with `id`, `text`, `answerType`, `resolver`, `answerableAlways`, `penaltyMinutes`.

---

### TASK 3 — Build the region adjacency map
**Depends on**: none
**Deliverable**: `regions.uk.json`
**Steps**:
1. Create an object keyed by region name, value = array of bordering region names.
2. Use these adjacencies (geographic truth, symmetric):
   - London ↔ South East, East of England
   - South East ↔ London, South West, East of England, West Midlands
   - South West ↔ South East, West Midlands, Wales
   - East of England ↔ London, South East, East Midlands
   - East Midlands ↔ East of England, West Midlands, Yorkshire and the Humber, North West
   - West Midlands ↔ South East, South West, East Midlands, North West, Wales
   - Yorkshire and the Humber ↔ East Midlands, North West, North East
   - North West ↔ West Midlands, East Midlands, Yorkshire and the Humber, North East, Wales, Scotland
   - North East ↔ Yorkshire and the Humber, North West, Scotland
   - Wales ↔ South West, West Midlands, North West
   - Scotland ↔ North East, North West
**Acceptance**: Symmetric — if A borders B, B borders A. Valid JSON.

---

### TASK 4 — Build the country config
**Depends on**: none
**Deliverable**: `config.uk.json` (and a top-level `countries.json` listing all supported countries)
**Steps**:
1. Create the config per §4.3.
2. Create `countries.json` with an array `[{ "id": "UK", "label": "United Kingdom", "configFile": "config.uk.json" }]`.
3. Penalties: `wrongGuess: 1`, `question: 3`, `hint: 0`.
4. `unansweredQuestionLimit: 3`.
5. Include `intercityOperators` and `sleeperOperators` lists as described in §6.
**Acceptance**: Both JSON files valid; config references files produced by tasks 1–3.

---

### TASK 5 — Implement the answer engine
**Depends on**: Tasks 1, 2, 3
**Deliverable**: `answerEngine.js` with dispatch function `answerQuestion(questionId, hiderStation, seekerStation, allStations, config) → { answerable, answer }`
**Steps**:
1. Implement every resolver function in the table in §6.
2. Build a dispatch map: `{ firstLetterOfName: fn, lastLetterOfName: fn, ... }`.
3. For "shares N letters" — compare sets of unique letters (case-insensitive, ignore spaces) — count of intersection.
4. For "shares vowels" — intersect vowel sets `{a,e,i,o,u}`.
5. For `countryOfUK` — map region → country (London, South East, South West, East of England, East Midlands, West Midlands, Yorkshire and the Humber, North East, North West → England; Wales → Wales; Scotland → Scotland).
6. For `passesThroughSeeker` and `isAirportStation` — return `{ answerable: false, reason: "route/airport data not available" }`.
7. Write unit tests for at least 5 representative resolvers using a few known stations from the CSV (London Paddington, Edinburgh Waverley, Aberystwyth, etc.).
**Acceptance**: All 37 question IDs dispatch without error; tests pass.

---

### TASK 6 — Implement the hint engine
**Depends on**: Task 1
**Deliverable**: `hintEngine.js` exporting `generateHint(station, revealedHintTypes) → { type, text } | null`
**Steps**:
1. Implement each hint source from §7.
2. Randomly pick an un-revealed source, generate hint text.
3. Return `null` when exhausted.
**Acceptance**: Calling repeatedly for the same station returns distinct hints until exhausted, then `null`.

---

### TASK 7 — Implement the guess engine
**Depends on**: Task 1
**Deliverable**: `guessEngine.js` exporting `checkGuess(input, hiderStation, allStations) → { correct, suggestion? }`
**Steps**:
1. Normalise input and names (lowercase, trim, collapse whitespace, strip punctuation).
2. Exact match after normalisation → `{ correct: true }`.
3. Else compute Levenshtein distance to the hider's station name; if ≤ 2 return a `suggestion`.
4. Else `{ correct: false }`.
**Acceptance**: "london paddington", "London Paddington", and "london  paddington" all match "London Paddington".

---

### TASK 8 — Implement the game state machine / reducer
**Depends on**: Tasks 4, 5, 6, 7
**Deliverable**: `gameState.js` — a pure reducer `(state, action) → newState`
**Steps**:
1. States: `IDLE`, `SETUP_COUNTRY`, `SETUP_STARTING_STATION`, `PLAYING`, `ENDED`.
2. Actions: `SELECT_COUNTRY`, `START_SETUP`, `SELECT_STARTING_STATION`, `ASK_QUESTION`, `REQUEST_HINT`, `MAKE_GUESS`, `GIVE_UP`, `RESET`.
3. On `START_SETUP`: pick random hider station from the country's stations; pick 3 random starting stations (not including hider's); record `gameStartTime`.
4. On `ASK_QUESTION`: call answer engine; if answerable → add `penaltyMinutes` to penalty accumulator and log; if not → increment `unansweredCount`; if `unansweredCount >= unansweredQuestionLimit` → transition to `ENDED` with reason `"unanswered_limit"`.
5. On `MAKE_GUESS`: if correct → `ENDED` with reason `"found"`; if wrong → +1 min penalty.
6. On `GIVE_UP`: `ENDED` with reason `"gave_up"`.
7. Expose `getFinalTime(state) → { elapsedMs, penaltyMs, totalMs, breakdown }`.
**Acceptance**: Reducer is pure (no side effects). Unit-tested transitions for each action.

---

### TASK 9 — Build the UI components
**Depends on**: Task 8
**Deliverable**: React components per §3 file structure
**Steps**:
1. `App.jsx` — wires reducer, renders current screen based on state.
2. `SetupScreen.jsx` — country dropdown + start button, then 3 starting-station cards.
3. `GameScreen.jsx` — composes the four action panels + timer + history.
4. `QuestionPanel.jsx` — searchable dropdown of the 37 questions, disable questions already asked, show their previous answer inline if re-clicked. Include a "Suggest a new question" textarea (non-submitting, label it clearly as "feedback for future versions").
5. `HintPanel.jsx` — button to request hint, shows count remaining.
6. `GuessInput.jsx` — text input with autocomplete from `allStations.map(s => s.name)`. On submit, shows correct/wrong + suggestion.
7. `HistoryLog.jsx` — chronological list of events with icons (❓ question, 💡 hint, ❌ wrong guess, ✅ correct guess).
8. `TimerDisplay.jsx` — live `MM:SS` updating every second via `useEffect` interval; shows penalty breakdown.
9. `EndScreen.jsx` — reveal panel + "Play again".
**Acceptance**: Every state transition is reachable by clicking UI. All 37 questions appear in the dropdown. Timer increments live. History log captures everything.

---

### TASK 10 — Handle edge cases and polish
**Depends on**: Task 9
**Steps**:
1. Seeker's starting station happens to equal the hider's station (1 in ~1,600 chance at setup): re-roll so they're distinct.
2. Seeker guesses their own starting station → handle cleanly (either wrong or correct based on comparison, no crash).
3. Re-asking the same question: either disable the option, or serve the cached answer without another penalty. Pick one and document.
4. Guessing with trailing/leading whitespace or different capitalisation → normalise.
5. Very long station names: ensure UI doesn't overflow.
6. Ambiguous short guesses like "London" — no exact match, show suggestions.
**Acceptance**: Manual playtest runs end-to-end without errors.

---

### TASK 11 — Document extensibility
**Depends on**: all above
**Deliverable**: `README.md`
**Content**:
- How to add a new question (append to JSON, optionally add resolver).
- How to add a new country (3 JSON files + config entry).
- How to add a new hint type (add function to hint engine).
- Where penalties / limits are configured.
- Data schema reference for stations, questions, regions, config.
**Acceptance**: Following the README, a fresh developer can add a demo question without touching UI code.

---

### TASK 12 — Confirm ambiguous spec rule with the user
**Depends on**: none, but should surface before Task 8 is finalised
**Action**: The spec sentence *"If the hider is unable to answer 3 questions during the game,"* is truncated. Default implementation: end the game, reveal the station, mark result as "unanswered-question limit reached". Surface this as `config.unansweredQuestionLimit` and `config.unansweredLimitBehaviour` with a code comment flagging that the user should confirm the intended rule.

---

## 13. Suggested Additional Questions (from the brief's "more can be added later")

These extend the question bank and all map to data already in the CSV — no new resolvers needed beyond trivial extensions:

1. **Is the closest major city to your station London?** (discriminates the large London cluster)
2. **Is your station in England?** (Q21 is multi-value; this is the boolean version)
3. **Is your station's cardinal direction "Central"?**
4. **Does your station's name contain a number?** (e.g. none currently, but future-proof)
5. **Is any of your landmarks a bridge / cathedral / palace / museum?** (landmark keyword probing)
6. **Is your station served by the Elizabeth line?** (specific operator probe)
7. **Does your postcode start with a digit after the letters?** (trivial, but narrows)
8. **Is your station name a single syllable?** (hard to auto-resolve — would need a syllable lib; flag as future)
9. **Does your station share a closest major city with more than 50 other stations?** (frequency probe)
10. **Is your station in one of the "Home Counties"** (South East + East of England region probe)

Task 11's README should explain how the user adds these by editing `questions.uk.json` only.

---

## 14. Out of Scope (flag for user)

- Real route / pathfinding (Q35 "would you pass through my station") — requires a rail network graph we don't have.
- Airport connection data (Q34) — not in CSV. Could be added as a `hasAirport: bool` field in a future CSV extension.
- Multiplayer / computer-as-seeker mode — not requested.
- Persistent leaderboards — ruled out by artifact storage restrictions.
- Difficulty levels (e.g. restricting question bank) — easy add once core is done.