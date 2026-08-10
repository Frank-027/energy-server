import requests
from ..config import laad_configuratie

config = laad_configuratie()

url = (
    f"https://monitoringapi.solaredge.com/"
    f"site/{config['site_id']}/energyDetails"
)

params = {
    "startTime": "2026-08-07 00:00:00",
    "endTime": "2026-08-07 23:59:59",
    "timeUnit": "DAY",
    "api_key": config["api_key"]
}

response = requests.get(url, params=params, timeout=30)

print("HTTP:", response.status_code)

data = response.json()

print(data)