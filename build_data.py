"""Build all static JSON data files from train_stations.csv.

This script is run once to generate:
  - data/stations.uk.json
  - data/questions.uk.json
  - data/regions.uk.json
  - data/config.uk.json
  - data/countries.json
"""

import csv
import json
import os
import re

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CSV_PATH = os.path.join(os.path.dirname(__file__), "train_stations.csv")


def slugify(name: str) -> str:
    """Convert a station name to a URL-friendly slug id.

    Args:
        name: The station name to slugify.

    Returns:
        Lowercase string with spaces replaced by hyphens and
        non-alphanumeric/hyphen characters removed.
    """
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    return slug


def parse_postcode_area(postcode: str) -> str:
    """Extract the leading letters from a postcode.

    Args:
        postcode: A UK postcode string such as "W2 1HQ" or "EC2M 7PY".

    Returns:
        The leading letter(s), e.g. "W" or "EC".
    """
    match = re.match(r"^([A-Z]+)", postcode.strip().upper())
    return match.group(1) if match else ""


def build_stations() -> list[dict]:
    """Parse train_stations.csv and return normalised station records.

    Returns:
        A list of dicts matching the station record schema defined in
        implementation_plan.md §4.1.
    """
    stations = []
    with open(CSV_PATH, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            operators_raw = row.get("Train Operating Companies / Lines", "")
            operators = [op.strip() for op in operators_raw.split(",") if op.strip()]

            landmarks_raw = [
                row.get("Landmark 1", "").strip(),
                row.get("Landmark 2", "").strip(),
                row.get("Landmark 3", "").strip(),
            ]
            landmarks = [lm for lm in landmarks_raw if lm and lm.lower() != "none"]

            postcode = row.get("Postcode", "").strip()
            name = row.get("Station", "").strip()

            station = {
                "id": slugify(name),
                "name": name,
                "operators": operators,
                "postcode": postcode,
                "postcodeArea": parse_postcode_area(postcode),
                "cardinalDirection": row.get("Cardinal Direction", "").strip(),
                "region": row.get("Region", "").strip(),
                "closestMajorCity": row.get("Closest Major City", "").strip(),
                "landmarks": landmarks,
            }
            stations.append(station)
    return stations


def build_questions() -> list[dict]:
    """Build the 37 question records for the UK game.

    Returns:
        A list of question dicts matching the schema defined in
        implementation_plan.md §4.2, with resolver, answerType,
        answerableAlways, and penaltyMinutes populated.
    """
    questions = [
        {
            "id": "q01",
            "text": "What is the first letter of your station name?",
            "answerType": "value",
            "resolver": "firstLetterOfName",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q02",
            "text": "What is the last letter of your station name?",
            "answerType": "value",
            "resolver": "lastLetterOfName",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q03",
            "text": "Is your station name a single word?",
            "answerType": "yes_no",
            "resolver": "isSingleWord",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q04",
            "text": "Does your station name consist of two or more words?",
            "answerType": "yes_no",
            "resolver": "isMultiWord",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q05",
            "text": "Is your station name longer than 10 characters?",
            "answerType": "yes_no",
            "resolver": "nameLongerThan10",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q06",
            "text": 'Does your station name contain "West" or "East"?',
            "answerType": "yes_no",
            "resolver": "containsWestOrEast",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q07",
            "text": 'Does your station name contain "North" or "South"?',
            "answerType": "yes_no",
            "resolver": "containsNorthOrSouth",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q08",
            "text": "Does your station name contain a compass direction (North, South, East, West, Upper, Lower, Central)?",  # noqa: E501
            "answerType": "yes_no",
            "resolver": "containsCompassWord",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q09",
            "text": 'Does your station name contain the word "New"?',
            "answerType": "yes_no",
            "resolver": "containsNew",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q10",
            "text": 'Does your station name contain "King" or "Queen"?',
            "answerType": "yes_no",
            "resolver": "containsKingOrQueen",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q11",
            "text": 'Does your station name contain "St" (as in Saint)?',
            "answerType": "yes_no",
            "resolver": "containsSaint",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q12",
            "text": 'Does your station name contain the word "Street", "Road", "Junction", "Central", or "Parkway"?',  # noqa: E501
            "answerType": "yes_no",
            "resolver": "containsSuffixWord",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q13",
            "text": 'Does your station name contain the word "Park"?',
            "answerType": "yes_no",
            "resolver": "containsPark",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q14",
            "text": 'Does your station name contain an "&" symbol?',
            "answerType": "yes_no",
            "resolver": "containsAmpersand",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q15",
            "text": 'Does your station name contain a bracketed qualifier, e.g. "(Kent)" or "(Lancashire)"?',  # noqa: E501
            "answerType": "yes_no",
            "resolver": "hasBracketedQualifier",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q16",
            "text": 'Does your station name start with a place name from Wales or Scotland (e.g. "Llan-", "Aber-", "Inver-", "Glen-")?',  # noqa: E501
            "answerType": "yes_no",
            "resolver": "hasCelticPrefix",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q17",
            "text": "Does your station share at least 2 letters with my station name?",
            "answerType": "yes_no",
            "resolver": "sharesAtLeast2Letters",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q18",
            "text": "Does your station share more than 3 letters in common with my station name?",
            "answerType": "yes_no",
            "resolver": "sharesMoreThan3Letters",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q19",
            "text": "Does your station share any vowels with my station name?",
            "answerType": "yes_no",
            "resolver": "sharesVowels",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q20",
            "text": "Is your station in London?",
            "answerType": "yes_no",
            "resolver": "isInLondon",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q21",
            "text": "Is your station in Scotland, Wales, or England?",
            "answerType": "value",
            "resolver": "countryOfUK",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q22",
            "text": "What region of the United Kingdom is your station in?",
            "answerType": "value",
            "resolver": "regionName",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q23",
            "text": "Is your station in the same region as my station?",
            "answerType": "yes_no",
            "resolver": "sameRegionAsSeeker",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q24",
            "text": "What is the cardinal direction of your station within the UK — North, South, East, West, or Central?",  # noqa: E501
            "answerType": "value",
            "resolver": "cardinalDirection",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q25",
            "text": "Is your station in the same cardinal direction as my station?",
            "answerType": "yes_no",
            "resolver": "sameCardinalAsSeeker",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q26",
            "text": "Does my station's region border your station's region?",
            "answerType": "yes_no",
            "resolver": "regionsBorder",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q27",
            "text": "What is the closest major city to your station?",
            "answerType": "value",
            "resolver": "closestMajorCity",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q28",
            "text": "Does your station share the same closest major city as my station?",
            "answerType": "yes_no",
            "resolver": "sameMajorCityAsSeeker",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q29",
            "text": "Is your station's closest major city Manchester or Liverpool?",
            "answerType": "yes_no",
            "resolver": "cityIsManchesterOrLiverpool",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q30",
            "text": "Does your station share the same train operating company as my station?",
            "answerType": "yes_no",
            "resolver": "sharesOperator",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q31",
            "text": "Is your station served by more than one train operating company?",
            "answerType": "yes_no",
            "resolver": "hasMultipleOperators",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q32",
            "text": "Is your station served by a long-distance intercity operator (Avanti West Coast, LNER, CrossCountry, or GWR)?",  # noqa: E501
            "answerType": "yes_no",
            "resolver": "hasIntercityOperator",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q33",
            "text": "Is your station served by a sleeper train service?",
            "answerType": "yes_no",
            "resolver": "hasSleeperOperator",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q34",
            "text": "Is your station directly connected to an airport?",
            "answerType": "yes_no",
            "resolver": "isAirportStation",
            "answerableAlways": False,
            "penaltyMinutes": 3,
        },
        {
            "id": "q35",
            "text": "Would you pass through my station to reach yours on the most direct rail route?",  # noqa: E501
            "answerType": "yes_no",
            "resolver": "passesThroughSeeker",
            "answerableAlways": False,
            "penaltyMinutes": 3,
        },
        {
            "id": "q36",
            "text": "Does your postcode area start with the same letter(s) as my station's postcode area?",  # noqa: E501
            "answerType": "yes_no",
            "resolver": "samePostcodeArea",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
        {
            "id": "q37",
            "text": "Is the first letter of your postcode a vowel (A, E, I, O, U)?",
            "answerType": "yes_no",
            "resolver": "postcodeStartsWithVowel",
            "answerableAlways": True,
            "penaltyMinutes": 3,
        },
    ]
    return questions


def build_regions() -> dict:
    """Build the UK region adjacency map.

    Returns:
        A dict keyed by region name where each value is a list of
        bordering region names. The graph is symmetric.
    """
    adjacency = {
        "London": ["South East", "East of England"],
        "South East": ["London", "South West", "East of England", "West Midlands"],
        "South West": ["South East", "West Midlands", "Wales"],
        "East of England": ["London", "South East", "East Midlands"],
        "East Midlands": [
            "East of England",
            "West Midlands",
            "Yorkshire and the Humber",
            "North West",
        ],
        "West Midlands": [
            "South East",
            "South West",
            "East Midlands",
            "North West",
            "Wales",
        ],
        "Yorkshire and the Humber": [
            "East Midlands",
            "North West",
            "North East",
        ],
        "North West": [
            "West Midlands",
            "East Midlands",
            "Yorkshire and the Humber",
            "North East",
            "Wales",
            "Scotland",
        ],
        "North East": ["Yorkshire and the Humber", "North West", "Scotland"],
        "Wales": ["South West", "West Midlands", "North West"],
        "Scotland": ["North East", "North West"],
    }
    return adjacency


def build_config() -> dict:
    """Build the UK country config dict.

    Returns:
        A dict matching the config schema defined in
        implementation_plan.md §4.3.
    """
    return {
        "country": "UK",
        "label": "United Kingdom",
        "stationsFile": "stations.uk.json",
        "questionsFile": "questions.uk.json",
        "regionsFile": "regions.uk.json",
        "penalties": {
            "wrongGuess": 1,
            "question": 3,
            "hint": 0,
        },
        "unansweredQuestionLimit": 3,
        # NOTE: The spec says "If the hider is unable to answer 3 questions
        # during the game," but the sentence is incomplete. The default
        # behaviour here is to end the game when unansweredQuestionLimit is
        # reached and reveal the hider's station, marked as
        # "unanswered_limit". Confirm this with the user.
        "unansweredLimitBehaviour": "end_game",
        "intercityOperators": [
            "Avanti West Coast",
            "LNER",
            "CrossCountry",
            "GWR",
            "Great Western Railway",
        ],
        "sleeperOperators": [
            "Caledonian Sleeper",
            "Night Riviera",
        ],
    }


def build_countries() -> list[dict]:
    """Build the top-level countries list.

    Returns:
        A list with one entry per supported country, each referencing its
        config file.
    """
    return [
        {
            "id": "UK",
            "label": "United Kingdom",
            "configFile": "config.uk.json",
        }
    ]


def main() -> None:
    """Generate all JSON data files and write them to the data/ directory."""
    os.makedirs(DATA_DIR, exist_ok=True)

    # Task 1 — stations
    stations = build_stations()
    stations_path = os.path.join(DATA_DIR, "stations.uk.json")
    with open(stations_path, "w", encoding="utf-8") as fh:
        json.dump(stations, fh, ensure_ascii=False, indent=2)
    print(f"Written {len(stations)} stations → {stations_path}")

    # Task 2 — questions
    questions = build_questions()
    questions_path = os.path.join(DATA_DIR, "questions.uk.json")
    with open(questions_path, "w", encoding="utf-8") as fh:
        json.dump(questions, fh, ensure_ascii=False, indent=2)
    print(f"Written {len(questions)} questions → {questions_path}")

    # Task 3 — regions
    regions = build_regions()
    regions_path = os.path.join(DATA_DIR, "regions.uk.json")
    with open(regions_path, "w", encoding="utf-8") as fh:
        json.dump(regions, fh, ensure_ascii=False, indent=2)
    print(f"Written {len(regions)} regions → {regions_path}")

    # Verify symmetry
    for region, neighbours in regions.items():
        for neighbour in neighbours:
            assert region in regions[neighbour], (
                f"Asymmetry: {region} borders {neighbour} but not vice versa"
            )
    print("Region adjacency symmetry verified.")

    # Task 4 — config
    config = build_config()
    config_path = os.path.join(DATA_DIR, "config.uk.json")
    with open(config_path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, ensure_ascii=False, indent=2)
    print(f"Written config → {config_path}")

    countries = build_countries()
    countries_path = os.path.join(DATA_DIR, "countries.json")
    with open(countries_path, "w", encoding="utf-8") as fh:
        json.dump(countries, fh, ensure_ascii=False, indent=2)
    print(f"Written countries → {countries_path}")


if __name__ == "__main__":
    main()
