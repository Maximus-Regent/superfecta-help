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

def get_race_detail(race_id, want_contents=True):
    """
    Calls GetRaces.ashx for a single raceId.
    Returns: list of 1 race dict with full details, including:
        - "runners": list of runner dicts (programNumber, runnerName, etc.)
        - "pools": list of pool dicts (poolId, poolTypeCode, etc.)
    """
    payload = NYRA_HEADER.copy()
    payload["raceIds"] = [race_id]
    payload["wantContents"] = want_contents

    resp = requests.post(
        f"{BASE_URL}/GetRaces.ashx",
        data={"request": json.dumps(payload)},
        headers=HEADERS
    )
    resp.raise_for_status()
    return resp.json().get("races", [])
