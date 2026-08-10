# --------------------------------------------------------------
# test_energy_day.py
#
# Test SolarEdge energyDetails per dag
# --------------------------------------------------------------

import requests
from ..config import laad_configuratie


def haal_energy_data_op(config, start_time, end_time):

    url = (
        f"https://monitoringapi.solaredge.com/site/"
        f"{config['site_id']}/energyDetails"
    )

    params = {
        "startTime": start_time,
        "endTime": end_time,
        "timeUnit": "DAY",
        "api_key": config["api_key"]
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=30
        )

    except requests.RequestException as fout:
        print("Fout bij verbinding met SolarEdge API:")
        print(fout)
        return None

    print("HTTP:", response.status_code)

    if response.status_code != 200:
        print(response.text)
        return None

    try:
        return response.json()

    except ValueError:
        print("SolarEdge gaf geen geldige JSON terug.")
        return None


# --------------------------------------------------------------
# Test
# --------------------------------------------------------------

start_time = "2026-08-07 00:00:00"
end_time = "2026-08-08 00:00:00"

config = laad_configuratie()

if config is None:
    print("Fout: configuratie kon niet worden geladen.")
    exit(1)

data = haal_energy_data_op(
    config,
    start_time,
    end_time
)

if data is not None:

    print()
    print("Energy details per dag")
    print("--------------------------------")

    meters = data["energyDetails"]["meters"]

    for meter in meters:

        print()
        print(meter["type"])

        for value in meter["values"]:

            print(
                value["date"],
                value["value"],
                "Wh"
            )