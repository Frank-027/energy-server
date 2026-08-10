# --------------------------------------------------------------
# test_energy_q.py
#
# Test SolarEdge energyDetails per kwartier
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
        "timeUnit": "QUARTER_OF_AN_HOUR",
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
    print("Energy details per kwartier")
    print("--------------------------------")

    meters = data["energyDetails"]["meters"]

    # ----------------------------------------------------------
    # Kwartierwaarden tonen
    # ----------------------------------------------------------

    for meter in meters:

        print()
        print(meter["type"])

        for value in meter["values"]:

            print(
                value["date"],
                value["value"],
                "Wh"
            )

    # ----------------------------------------------------------
    # Totalen berekenen
    # ----------------------------------------------------------

    totalen = {}

    for meter in meters:

        meter_type = meter["type"]

        totalen[meter_type] = sum(
            value["value"]
            for value in meter["values"]
        )

    print()
    print()
    print("Energy totals")
    print("--------------------------------")

    for meter_type, totaal in totalen.items():

        print(
            f"{meter_type:<16} "
            f"{totaal:>8.0f} Wh "
            f"({totaal / 1000:.3f} kWh)"
        )

    # ----------------------------------------------------------
    # Consistentiecontroles
    # ----------------------------------------------------------

    print()
    print("Consistency checks")
    print("--------------------------------")

    # We maken eerst dictionaries op basis van tijdstip.
    # Daardoor zijn de verschillende meters eenvoudig
    # met elkaar te vergelijken.

    waarden = {}

    for meter in meters:

        meter_type = meter["type"]

        waarden[meter_type] = {}

        for value in meter["values"]:

            waarden[meter_type][value["date"]] = value["value"]

    # ----------------------------------------------------------
    # Production = SelfConsumption + FeedIn
    # ----------------------------------------------------------

    production_errors = []

    if (
        "Production" in waarden
        and "SelfConsumption" in waarden
        and "FeedIn" in waarden
    ):

        for tijd in waarden["Production"]:

            production = waarden["Production"].get(tijd, 0)
            self_consumption = waarden["SelfConsumption"].get(tijd, 0)
            feed_in = waarden["FeedIn"].get(tijd, 0)

            verschil = production - (
                self_consumption + feed_in
            )

            if abs(verschil) > 1:
                production_errors.append(
                    (
                        tijd,
                        production,
                        self_consumption,
                        feed_in,
                        verschil
                    )
                )

        if not production_errors:
            print(
                "Production = SelfConsumption + FeedIn : OK"
            )
        else:
            print(
                "Production = SelfConsumption + FeedIn : "
                f"{len(production_errors)} afwijkingen"
            )

    # ----------------------------------------------------------
    # Consumption = SelfConsumption + Purchased
    # ----------------------------------------------------------

    consumption_errors = []

    if (
        "Consumption" in waarden
        and "SelfConsumption" in waarden
        and "Purchased" in waarden
    ):

        for tijd in waarden["Consumption"]:

            consumption = waarden["Consumption"].get(tijd, 0)
            self_consumption = waarden["SelfConsumption"].get(tijd, 0)
            purchased = waarden["Purchased"].get(tijd, 0)

            verschil = consumption - (
                self_consumption + purchased
            )

            if abs(verschil) > 1:
                consumption_errors.append(
                    (
                        tijd,
                        consumption,
                        self_consumption,
                        purchased,
                        verschil
                    )
                )

        if not consumption_errors:
            print(
                "Consumption = SelfConsumption + Purchased : OK"
            )
        else:
            print(
                "Consumption = SelfConsumption + Purchased : "
                f"{len(consumption_errors)} afwijkingen"
            )

    # ----------------------------------------------------------
    # Production afwijkingen tonen
    # ----------------------------------------------------------

    if production_errors:

        print()
        print("Production afwijkingen")
        print("--------------------------------")

        for (
            tijd,
            production,
            self_consumption,
            feed_in,
            verschil
        ) in production_errors:

            print(
                tijd,
                f"Production={production} Wh, "
                f"SelfConsumption={self_consumption} Wh, "
                f"FeedIn={feed_in} Wh, "
                f"verschil={verschil} Wh"
            )

    # ----------------------------------------------------------
    # Consumption afwijkingen tonen
    # ----------------------------------------------------------

    if consumption_errors:

        print()
        print("Consumption afwijkingen")
        print("--------------------------------")

        for (
            tijd,
            consumption,
            self_consumption,
            purchased,
            verschil
        ) in consumption_errors:

            print(
                tijd,
                f"Consumption={consumption} Wh, "
                f"SelfConsumption={self_consumption} Wh, "
                f"Purchased={purchased} Wh, "
                f"verschil={verschil} Wh"
            )