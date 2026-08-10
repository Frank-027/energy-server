# --------------------------------------------------------------
# test_storage_quarter.py
#
# Analyse SolarEdge batterij per kwartier
#
# Vergelijkt:
#   1. Energie volgens SOC
#   2. Energie volgens power
#   3. LifetimeEnergyCharged
#   4. LifetimeEnergyDischarged
#
# Getest voor:
#   2026-08-07
#   2026-08-08
#
# Configuratie:
#   config.py
# --------------------------------------------------------------

import requests
from datetime import datetime

from ..config import laad_configuratie


# --------------------------------------------------------------
# CONFIGURATIE
# --------------------------------------------------------------

config = laad_configuratie()

if config is None:
    raise SystemExit("Configuratie kon niet worden geladen.")

SITE_ID = config["site_id"]
API_KEY = config["api_key"]

BASE_URL = "https://monitoringapi.solaredge.com"


# --------------------------------------------------------------
# HULPFUNCTIES
# --------------------------------------------------------------

def kwh(wh):
    return wh / 1000.0


def tijd_uit_string(timestamp):
    return datetime.strptime(
        timestamp,
        "%Y-%m-%d %H:%M:%S"
    )


def energie_soc(soc_begin, soc_einde, capaciteit):
    """
    Berekent de verandering in batterij-energie op basis van SOC.

    Positief = batterij geladen
    Negatief = batterij ontladen
    """

    verschil_soc = soc_einde - soc_begin

    return verschil_soc / 100.0 * capaciteit


# --------------------------------------------------------------
# STORAGE API
# --------------------------------------------------------------

def haal_storage_data(datum):

    start = f"{datum} 00:00:00"
    einde = f"{datum} 23:59:59"

    url = f"{BASE_URL}/site/{SITE_ID}/storageData"

    params = {
        "startTime": start,
        "endTime": einde,
        "api_key": API_KEY
    }

    response = requests.get(url, params=params)

    print("Storage HTTP:", response.status_code)

    if response.status_code != 200:
        print(response.text)
        return None

    return response.json()


# --------------------------------------------------------------
# BATTERIJ UIT RESPONSE HALEN
# --------------------------------------------------------------

def haal_batterij(storage_response):

    if not storage_response:
        return None

    if "storageData" not in storage_response:

        print("Onverwachte structuur:")
        print(storage_response.keys())

        return None

    storage_data = storage_response["storageData"]

    if "batteries" not in storage_data:

        print("Onverwachte structuur binnen storageData:")
        print(storage_data.keys())

        return None

    batteries = storage_data["batteries"]

    if not batteries:
        print("Geen batterijen gevonden.")
        return None

    return batteries[0]


# --------------------------------------------------------------
# KWARTIER BEPALEN
# --------------------------------------------------------------

def kwartier_start(tijd):

    minuut = (tijd.minute // 15) * 15

    return tijd.replace(
        minute=minuut,
        second=0,
        microsecond=0
    )


# --------------------------------------------------------------
# TELEMETRIE SORTEREN
# --------------------------------------------------------------

def sorteer_telemetries(telemetries):

    return sorted(
        telemetries,
        key=lambda x: tijd_uit_string(x["timeStamp"])
    )


# --------------------------------------------------------------
# KWARTIERANALYSE
# --------------------------------------------------------------

def analyseer_kwartieren(telemetries):

    kwartieren = {}

    for i in range(len(telemetries) - 1):

        huidige = telemetries[i]
        volgende = telemetries[i + 1]

        try:

            tijd1 = tijd_uit_string(
                huidige["timeStamp"]
            )

            tijd2 = tijd_uit_string(
                volgende["timeStamp"]
            )

            power = float(
                huidige.get("power", 0)
            )

            soc = float(
                huidige.get(
                    "batteryPercentageState",
                    0
                )
            )

            soc_volgende = float(
                volgende.get(
                    "batteryPercentageState",
                    0
                )
            )

            charged1 = float(
                huidige.get(
                    "lifeTimeEnergyCharged",
                    0
                )
            )

            charged2 = float(
                volgende.get(
                    "lifeTimeEnergyCharged",
                    0
                )
            )

            discharged1 = float(
                huidige.get(
                    "lifeTimeEnergyDischarged",
                    0
                )
            )

            discharged2 = float(
                volgende.get(
                    "lifeTimeEnergyDischarged",
                    0
                )
            )

            capaciteit1 = float(
                huidige.get(
                    "fullPackEnergyAvailable",
                    0
                )
            )

            capaciteit2 = float(
                volgende.get(
                    "fullPackEnergyAvailable",
                    capaciteit1
                )
            )

        except (ValueError, TypeError, KeyError):

            continue

        seconden = (
            tijd2 - tijd1
        ).total_seconds()

        if seconden <= 0:
            continue

        # ------------------------------------------------------
        # Energie volgens POWER
        # ------------------------------------------------------

        energie_power = (
            power * seconden / 3600.0
        )

        # Positief = laden
        # Negatief = ontladen

        # ------------------------------------------------------
        # Energie volgens SOC
        # ------------------------------------------------------

        capaciteit = (
            capaciteit1 + capaciteit2
        ) / 2.0

        energie_soc_waarde = energie_soc(
            soc,
            soc_volgende,
            capaciteit
        )

        # ------------------------------------------------------
        # Lifetime veranderingen
        # ------------------------------------------------------

        lifetime_charged = (
            charged2 - charged1
        )

        lifetime_discharged = (
            discharged2 - discharged1
        )

        # ------------------------------------------------------
        # Kwartier bepalen
        # ------------------------------------------------------

        kwartier = kwartier_start(tijd1)

        sleutel = kwartier.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        if sleutel not in kwartieren:

            kwartieren[sleutel] = {
                "tijd": kwartier,
                "soc_begin": soc,
                "soc_einde": soc_volgende,

                "energie_soc": 0.0,
                "energie_power": 0.0,

                "lifetime_charged": 0.0,
                "lifetime_discharged": 0.0,

                "capaciteit": capaciteit,

                "metingen": 0
            }

        q = kwartieren[sleutel]

        # ------------------------------------------------------
        # Energie optellen
        # ------------------------------------------------------

        q["energie_soc"] += energie_soc_waarde

        q["energie_power"] += energie_power

        q["lifetime_charged"] += lifetime_charged

        q["lifetime_discharged"] += lifetime_discharged

        q["soc_einde"] = soc_volgende

        q["capaciteit"] = capaciteit

        q["metingen"] += 1

    return kwartieren


# --------------------------------------------------------------
# KWARTIEREN AFDRUKKEN
# --------------------------------------------------------------

def print_kwartieren(kwartieren):

    print()
    print(
        "KWARTIERANALYSE"
    )
    print("-" * 125)

    print(
        f"{'Tijd':<20}"
        f"{'SOC %':>10}"
        f"{'ΔSOC %':>10}"
        f"{'SOC Wh':>12}"
        f"{'Power Wh':>12}"
        f"{'Life C':>12}"
        f"{'Life D':>12}"
        f"{'SOC-Power':>13}"
    )

    print("-" * 125)

    totaal_soc = 0.0
    totaal_power = 0.0
    totaal_charged = 0.0
    totaal_discharged = 0.0

    for sleutel in sorted(kwartieren):

        q = kwartieren[sleutel]

        soc_begin = q["soc_begin"]
        soc_einde = q["soc_einde"]

        delta_soc = (
            soc_einde - soc_begin
        )

        energie_soc_waarde = q["energie_soc"]

        energie_power = q["energie_power"]

        verschil = (
            energie_soc_waarde -
            energie_power
        )

        lifetime_charged = q[
            "lifetime_charged"
        ]

        lifetime_discharged = q[
            "lifetime_discharged"
        ]

        print(
            f"{sleutel:<20}"
            f"{soc_begin:6.2f}→{soc_einde:5.2f}"
            f"{delta_soc:>10.2f}"
            f"{energie_soc_waarde:>12.1f}"
            f"{energie_power:>12.1f}"
            f"{lifetime_charged:>12.1f}"
            f"{lifetime_discharged:>12.1f}"
            f"{verschil:>13.1f}"
        )

        totaal_soc += energie_soc_waarde
        totaal_power += energie_power
        totaal_charged += lifetime_charged
        totaal_discharged += lifetime_discharged

    # ----------------------------------------------------------
    # TOTALEN
    # ----------------------------------------------------------

    print("-" * 125)

    print(
        f"{'TOTAAL':<20}"
        f"{'':>10}"
        f"{'':>10}"
        f"{totaal_soc:>12.1f}"
        f"{totaal_power:>12.1f}"
        f"{totaal_charged:>12.1f}"
        f"{totaal_discharged:>12.1f}"
        f"{totaal_soc - totaal_power:>13.1f}"
    )

    print()
    print("Totalen in kWh")
    print("-" * 70)

    print(
        f"Energie volgens SOC   : "
        f"{kwh(totaal_soc):8.3f} kWh"
    )

    print(
        f"Energie volgens power : "
        f"{kwh(totaal_power):8.3f} kWh"
    )

    print(
        f"Verschil SOC - power   : "
        f"{kwh(totaal_soc - totaal_power):8.3f} kWh"
    )

    print(
        f"Lifetime geladen       : "
        f"{kwh(totaal_charged):8.3f} kWh"
    )

    print(
        f"Lifetime ontladen      : "
        f"{kwh(totaal_discharged):8.3f} kWh"
    )

    return {
        "soc": totaal_soc,
        "power": totaal_power,
        "lifetime_charged": totaal_charged,
        "lifetime_discharged": totaal_discharged
    }


# --------------------------------------------------------------
# DAG ANALYSEREN
# --------------------------------------------------------------

def analyseer_dag(datum):

    print()
    print("#" * 70)
    print(
        f"SolarEdge batterij kwartieranalyse - {datum}"
    )
    print("#" * 70)

    storage_response = haal_storage_data(datum)

    if storage_response is None:
        print(
            "Storage gegevens konden niet worden opgehaald."
        )
        return None

    battery = haal_batterij(storage_response)

    if battery is None:
        return None

    print()
    print("Batterij")
    print("-" * 70)

    print(
        f"Naam                 : "
        f"{battery.get('nameplate')} Wh"
    )

    print(
        f"Model                : "
        f"{battery.get('modelNumber')}"
    )

    print(
        f"Aantal telemetries   : "
        f"{battery.get('telemetryCount')}"
    )

    telemetries = battery.get(
        "telemetries",
        []
    )

    if not telemetries:

        print("Geen telemetries gevonden.")

        return None

    telemetries = sorteer_telemetries(
        telemetries
    )

    kwartieren = analyseer_kwartieren(
        telemetries
    )

    if not kwartieren:

        print("Geen kwartiergegevens gevonden.")

        return None

    totaal = print_kwartieren(
        kwartieren
    )

    return totaal


# --------------------------------------------------------------
# HOOFDPROGRAMMA
# --------------------------------------------------------------

if __name__ == "__main__":

    datums = [
        "2026-08-07",
        "2026-08-08"
    ]

    resultaten = {}

    for datum in datums:

        resultaat = analyseer_dag(
            datum
        )

        if resultaat is not None:

            resultaten[datum] = resultaat

    # ----------------------------------------------------------
    # VERGELIJKING
    # ----------------------------------------------------------

    if len(resultaten) == 2:

        print()
        print()
        print("#" * 70)
        print("VERGELIJKING DAGEN")
        print("#" * 70)

        print()

        print(
            f"{'Datum':<15}"
            f"{'SOC Wh':>14}"
            f"{'Power Wh':>14}"
            f"{'Life geladen':>16}"
            f"{'Life ontladen':>17}"
            f"{'SOC-Power':>14}"
        )

        print("-" * 90)

        for datum in datums:

            r = resultaten[datum]

            print(
                f"{datum:<15}"
                f"{r['soc']:>14.1f}"
                f"{r['power']:>14.1f}"
                f"{r['lifetime_charged']:>16.1f}"
                f"{r['lifetime_discharged']:>17.1f}"
                f"{r['soc'] - r['power']:>14.1f}"
            )

        print()
        print("In kWh")
        print("-" * 70)

        for datum in datums:

            r = resultaten[datum]

            print(
                f"{datum:<15}"
                f"SOC: {kwh(r['soc']):8.3f} kWh   "
                f"Power: {kwh(r['power']):8.3f} kWh   "
                f"Verschil: "
                f"{kwh(r['soc'] - r['power']):8.3f} kWh"
            )