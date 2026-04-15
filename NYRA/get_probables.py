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
    "wageringCohort": "A2N"
}

def get_probables(pool_ids):
    """
    Calls GetProbables.ashx for the given list of poolIds.
    Returns: list of pool dicts, each containing:
      - "poolId", "poolTypeCode", "poolStatus", "currentPoolTotal"
      - "probables": list of {programNumber, winPool: {amount, currency}}
    """
    payload = NYRA_HEADER.copy()
    payload["poolIds"] = pool_ids

    resp = requests.post(
        f"{BASE_URL}/GetProbables.ashx",
        data={"request": json.dumps(payload)},
        headers=HEADERS
    )
    resp.raise_for_status()
    return resp.json().get("pools", [])
