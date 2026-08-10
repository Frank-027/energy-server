# --------------------------------------------------------------
# test_storage.py
#
# Test SolarEdge EnergyDetails + Storage API
#
# Vergelijkt:
#   - SolarEdge EnergyDetails
#   - SolarEdge batterijgegevens
#   - batterijvermogen per kwartier
#   - lifetime geladen/ontladen
#
# Getest voor:
#   2026-08-07
#   2026-08-08
# --------------------------------------------------------------

import requests
from datetime import datetime, timedelta

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
    return wh / 1000


def print_energie(label, waarde):
    print(f"{label:<17}: {waarde:8.0f} Wh ({kwh(waarde):.3f} kWh)")


def datetime_voor_api(datum, einde=False):
    if einde:
        return f"{datum} 23:59:59"
    else:
        return f"{datum} 00:00:00"


# --------------------------------------------------------------
# ENERGY DETAILS
# --------------------------------------------------------------

def haal_energy_details(datum):

    start = datetime_voor_api(datum)
    einde = datetime_voor_api(datum, True)

    url = f"{BASE_URL}/site/{SITE_ID}/energyDetails"

    params = {
        "startTime": start,
        "endTime": einde,
        "timeUnit": "DAY",
        "api_key": API_KEY
    }

    response = requests.get(url, params=params)

    print("EnergyDetails HTTP:", response.status_code)

    if response.status_code != 200:
        print(response.text)
        return None

    return response.json()


# --------------------------------------------------------------
# STORAGE DATA
# --------------------------------------------------------------

def haal_storage_data(datum):

    start = datetime_voor_api(datum)
    einde = datetime_voor_api(datum, True)

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
# ENERGY DETAILS UITLEZEN
# --------------------------------------------------------------

def lees_energy_details(data):

    try:
        energies = data["energyDetails"]["meters"]

        waarden = {}

        for meter in energies:

            meter_type = meter.get("type")

            details = meter.get("values", [])

            if not details:
                continue

            # Bij timeUnit=DAY is er normaal één waarde
            waarde = details[0].get("value")

            if waarde is None:
                waarde = 0

            waarden[meter_type] = float(waarde)

        return waarden

    except Exception as e:
        print("Fout bij uitlezen EnergyDetails:", e)
        return None


# --------------------------------------------------------------
# STORAGE STRUCTUUR UITLEZEN
# --------------------------------------------------------------

def haal_batterij(storage_response):

    if not storage_response:
        return None

    # ----------------------------------------------------------
    # BELANGRIJK:
    #
    # SolarEdge geeft:
    #
    # {
    #     "storageData": {
    #         "batteryCount": 1,
    #         "batteries": [...]
    #     }
    # }
    # ----------------------------------------------------------

    if "storageData" not in storage_response:

        print("Onverwachte structuur van Storage API:")
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

    # We hebben één batterij
    return batteries[0]


# --------------------------------------------------------------
# BATTERIJ TELEMETRIES
# --------------------------------------------------------------

def bereken_batterij_power(telemetries):

    geladen = 0.0
    ontladen = 0.0

    kwartieren = {}

    for i in range(len(telemetries) - 1):

        huidige = telemetries[i]
        volgende = telemetries[i + 1]

        try:
            tijd1 = datetime.strptime(
                huidige["timeStamp"],
                "%Y-%m-%d %H:%M:%S"
            )

            tijd2 = datetime.strptime(
                volgende["timeStamp"],
                "%Y-%m-%d %H:%M:%S"
            )

            power = float(huidige.get("power", 0))

        except (ValueError, TypeError, KeyError):
            continue

        # Werkelijke tijd tussen twee metingen
        seconden = (tijd2 - tijd1).total_seconds()

        if seconden <= 0:
            continue

        # Energie = vermogen * tijd
        wh = abs(power) * seconden / 3600

        if power > 0:
            geladen += wh
        elif power < 0:
            ontladen += wh

        # ------------------------------------------------------
        # Kwartier bepalen
        # ------------------------------------------------------

        kwartier_minuut = (tijd1.minute // 15) * 15

        kwartier = tijd1.replace(
            minute=kwartier_minuut,
            second=0
        )

        sleutel = kwartier.strftime("%Y-%m-%d %H:%M:%S")

        if sleutel not in kwartieren:
            kwartieren[sleutel] = {
                "laden": 0.0,
                "ontladen": 0.0
            }

        if power > 0:
            kwartieren[sleutel]["laden"] += wh
        elif power < 0:
            kwartieren[sleutel]["ontladen"] += wh

    return geladen, ontladen, kwartieren


# --------------------------------------------------------------
# ANALYSE DAG
# --------------------------------------------------------------

def analyseer_dag(datum):

    print()
    print("=" * 60)
    print(f"DAG: {datum}")
    print("=" * 60)

    # ----------------------------------------------------------
    # ENERGY DETAILS
    # ----------------------------------------------------------

    energy_data = haal_energy_details(datum)

    if energy_data is None:
        return None

    energy = lees_energy_details(energy_data)

    if energy is None:
        return None

    production = energy.get("Production", 0)
    self_consumption = energy.get("SelfConsumption", 0)
    feed_in = energy.get("FeedIn", 0)
    consumption = energy.get("Consumption", 0)
    purchased = energy.get("Purchased", 0)

    print()
    print("SolarEdge energiebalans")
    print("--------------------------------")

    print_energie("Production", production)
    print_energie("SelfConsumption", self_consumption)
    print_energie("FeedIn", feed_in)
    print_energie("Consumption", consumption)
    print_energie("Purchased", purchased)

    # ----------------------------------------------------------
    # STORAGE
    # ----------------------------------------------------------

    storage_response = haal_storage_data(datum)

    if storage_response is None:
        return None

    battery = haal_batterij(storage_response)

    if battery is None:
        return None

    print()
    print("Batterij")
    print("--------------------------------")

    nameplate = battery.get("nameplate")
    model = battery.get("modelNumber")
    telemetry_count = battery.get("telemetryCount")

    print(f"Naam: {nameplate} Wh")
    print(f"Model: {model}")
    print(f"Aantal telemetries: {telemetry_count}")

    telemetries = battery.get("telemetries", [])

    if not telemetries:
        print("Geen telemetries gevonden.")
        return None

    # ----------------------------------------------------------
    # LIFETIME BEGIN / EINDE
    # ----------------------------------------------------------

    eerste = telemetries[0]
    laatste = telemetries[-1]

    lifetime_charged_begin = float(
        eerste.get("lifeTimeEnergyCharged", 0)
    )

    lifetime_charged_end = float(
        laatste.get("lifeTimeEnergyCharged", 0)
    )

    lifetime_discharged_begin = float(
        eerste.get("lifeTimeEnergyDischarged", 0)
    )

    lifetime_discharged_end = float(
        laatste.get("lifeTimeEnergyDischarged", 0)
    )

    lifetime_loaded = (
        lifetime_charged_end -
        lifetime_charged_begin
    )

    lifetime_discharged = (
        lifetime_discharged_end -
        lifetime_discharged_begin
    )

    netto_lifetime = (
        lifetime_loaded -
        lifetime_discharged
    )

    print()
    print("Lifetime batterij")
    print("--------------------------------")

    print_energie("Geladen", lifetime_loaded)
    print_energie("Ontladen", lifetime_discharged)
    print_energie("Netto verandering", netto_lifetime)

    # ----------------------------------------------------------
    # BATTERIJ POWER BEREKENEN
    # ----------------------------------------------------------

    geladen_power, ontladen_power, kwartieren = \
        bereken_batterij_power(telemetries)

    print()
    print("Batterij berekend uit power")
    print("--------------------------------")

    print_energie("Geschat geladen", geladen_power)
    print_energie("Geschat ontladen", ontladen_power)

    # ----------------------------------------------------------
    # VERSCHIL LIFETIME / POWER
    # ----------------------------------------------------------

    verschil_laden = geladen_power - lifetime_loaded
    verschil_ontladen = ontladen_power - lifetime_discharged

    print()
    print("Verschil lifetime / power")
    print("--------------------------------")

    print_energie("Laden verschil", verschil_laden)
    print_energie("Ontladen verschil", verschil_ontladen)

    # ----------------------------------------------------------
    # CONTROLES ENERGY DETAILS
    # ----------------------------------------------------------

    controle_productie = (
        production -
        self_consumption -
        feed_in
    )

    controle_consumption = (
        consumption -
        self_consumption -
        purchased
    )

    print()
    print("Controles")
    print("--------------------------------")

    print(
        "Production = SelfConsumption + FeedIn : "
        f"verschil {controle_productie:.0f} Wh"
    )

    print(
        "Consumption = SelfConsumption + Purchased : "
        f"verschil {controle_consumption:.0f} Wh"
    )

    # ----------------------------------------------------------
    # BATTERIJANALYSE
    # ----------------------------------------------------------

    print()
    print("Batterijanalyse")
    print("--------------------------------")

    print(
        f"Production                 : {production:8.0f} Wh"
    )

    print(
        f"Production + ontladen      : "
        f"{production + ontladen_power:8.0f} Wh"
    )

    print(
        f"Production - geladen       : "
        f"{production - geladen_power:8.0f} Wh"
    )

    print(
        f"Production + ontladen - geladen : "
        f"{production + ontladen_power - geladen_power:8.0f} Wh"
    )

    # ----------------------------------------------------------
    # RESULTAAT TERUGGEVEN
    # ----------------------------------------------------------

    return {
        "production": production,
        "consumption": consumption,
        "self_consumption": self_consumption,
        "feed_in": feed_in,
        "purchased": purchased,

        "battery_lifetime_loaded": lifetime_loaded,
        "battery_lifetime_discharged": lifetime_discharged,

        "battery_loaded": geladen_power,
        "battery_discharged": ontladen_power,

        "battery_net": (
            geladen_power -
            ontladen_power
        ),

        "battery": battery,

        "kwartieren": kwartieren
    }


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

        print()
        print("#" * 60)
        print(f"Gegevens ophalen voor {datum}")
        print("#" * 60)

        resultaat = analyseer_dag(datum)

        if resultaat is not None:
            resultaten[datum] = resultaat
        else:
            print(
                f"Geen volledige gegevens voor {datum}"
            )

    # ----------------------------------------------------------
    # VERGELIJKING
    # ----------------------------------------------------------

    if len(resultaten) == 2:

        datum1 = datums[0]
        datum2 = datums[1]

        dag1 = resultaten[datum1]
        dag2 = resultaten[datum2]

        print()
        print()
        print("#" * 60)
        print("VERGELIJKING DAGEN")
        print("#" * 60)

        print()
        print(
            f"{'Datum':<12}"
            f"{'Production':>12}"
            f"{'Consumption':>14}"
            f"{'Bat geladen':>14}"
            f"{'Bat ontladen':>16}"
        )

        print("-" * 72)

        print(
            f"{datum1:<12}"
            f"{dag1['production']:>12.0f}"
            f"{dag1['consumption']:>14.0f}"
            f"{dag1['battery_loaded']:>14.0f}"
            f"{dag1['battery_discharged']:>16.0f}"
        )

        print(
            f"{datum2:<12}"
            f"{dag2['production']:>12.0f}"
            f"{dag2['consumption']:>14.0f}"
            f"{dag2['battery_loaded']:>14.0f}"
            f"{dag2['battery_discharged']:>16.0f}"
        )

        print()
        print("Verschil dag 2 - dag 1")
        print("--------------------------------")

        print(
            f"Production : "
            f"{dag2['production'] - dag1['production']:8.0f} Wh"
        )

        print(
            f"Consumption: "
            f"{dag2['consumption'] - dag1['consumption']:8.0f} Wh"
        )

        print(
            f"Bat laden  : "
            f"{dag2['battery_loaded'] - dag1['battery_loaded']:8.0f} Wh"
        )

        print(
            f"Bat ontladen: "
            f"{dag2['battery_discharged'] - dag1['battery_discharged']:8.0f} Wh"
        )

    else:

        print()
        print(
            "Er zijn niet genoeg dagen beschikbaar "
            "voor de vergelijking."
        )