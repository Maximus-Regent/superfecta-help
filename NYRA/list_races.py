import requests, json

BASE_URL = "https://brk0201-iapi-webservice.nyrabets.com"
HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}
NYRA_HEADER = {
    "header": {
        "version": 2,
        "fragmentLanguage": "Javascript",
        "fragmentVersion": "",
        "clientIdentifier": "nyra.1b"
    },
    "cohort": "A--",
    "wageringCohort": "NBI"
}

def list_races(card_ids):
    """
    Calls ListRaces.ashx for the given list of cardIds.
    Returns: list of race dicts, each containing keys like
      raceId, raceNumber, raceMeetingName, postTime, numberOfRunners, etc.
    """
    payload = NYRA_HEADER.copy()
    payload["cardIds"] = card_ids

    resp = requests.post(
        f"{BASE_URL}/ListRaces.ashx",
        data={"request": json.dumps(payload)},
        headers=HEADERS
    )
    resp.raise_for_status()
    return resp.json().get("races", [])
