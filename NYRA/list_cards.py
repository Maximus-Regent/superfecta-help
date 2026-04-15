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

def list_cards():
    """
    Calls ListCards.ashx to fetch all today’s cards.
    Returns: list of card dicts, each containing keys like
      cardId, cardName, cardDate, numberOfRunners, etc.
    """
    payload = NYRA_HEADER.copy()
    payload["cardDate"] = None
    payload["wantHiddenCards"] = False

    resp = requests.post(
        f"{BASE_URL}/ListCards.ashx",
        data={"request": json.dumps(payload)},
        headers=HEADERS
    )
    resp.raise_for_status()
    return resp.json().get("cards", [])
