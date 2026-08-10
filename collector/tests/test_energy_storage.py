# --------------------------------------------------------------
# test_energy_storage.py
#
# SolarEdge EnergyDetails + Storage analyse
#
# Analyseert:
#   - EnergyDetails per dag
#   - batterij lifetime geladen/ontladen
#   - batterij power
#   - batterij-energie volgens SOC
#   - vergelijking SOC versus power
#   - batterij per kwartier
#   - vergelijking tussen meerdere dagen
#
# Getest voor:
#   2026-08-07
#   2026-08-08
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


def print_energie(label, waarde):
    print(
        f"{label:<25}: "
        f"{waarde:8.0f} Wh ({kwh(waarde):.3f} kWh)"
    )


def api_datum(datum, einde=False):

    if einde:
        return f"{datum} 23:59:59"

    return f"{datum} 00:00:00"


# --------------------------------------------------------------
# ENERGY DETAILS
# --------------------------------------------------------------

def haal_energy_details(datum):

    start = api_datum(datum)
    einde = api_datum(datum, True)

    url = f"{BASE_URL}/site/{SITE_ID}/energyDetails"

    params = {
        "startTime": start,
        "endTime": einde,

        # BELANGRIJK:
        # QUARTER wordt door deze API niet ondersteund.
        # Voor de dagbalans gebruiken we DAY.
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
# ENERGY DETAILS UITLEZEN
# --------------------------------------------------------------

def lees_energy_details(data):

    try:

        meters = data["energyDetails"]["meters"]

        waarden = {}

        for meter in meters:

            meter_type = meter.get("type")

            values = meter.get("values", [])

            if not values:
                continue

            waarde = values[0].get("value")

            if waarde is None:
                waarde = 0

            waarden[meter_type] = float(waarde)

        return waarden

    except Exception as e:

        print(
            "Fout bij uitlezen EnergyDetails:",
            e
        )

        return None


# --------------------------------------------------------------
# STORAGE DATA
# --------------------------------------------------------------

def haal_storage_data(datum):

    start = api_datum(datum)
    einde = api_datum(datum, True)

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
# BATTERIJ UIT STORAGE RESPONSE HALEN
# --------------------------------------------------------------

def haal_batterij(storage_response):

    if not storage_response:
        return None

    if "storageData" not in storage_response:

        print()
        print("Onverwachte structuur Storage API:")
        print(storage_response.keys())

        return None

    storage_data = storage_response["storageData"]

    if "batteries" not in storage_data:

        print()
        print("Onverwachte structuur binnen storageData:")
        print(storage_data.keys())

        return None

    batteries = storage_data["batteries"]

    if not batteries:

        print("Geen batterijen gevonden.")

        return None

    # We hebben één batterij.
    return batteries[0]


# --------------------------------------------------------------
# DATUM/TIJD TELEMETRY
# --------------------------------------------------------------

def telemetry_tijd(telemetry):

    return datetime.strptime(
        telemetry["timeStamp"],
        "%Y-%m-%d %H:%M:%S"
    )


# --------------------------------------------------------------
# BATTERIJ POWER BEREKENEN
# --------------------------------------------------------------

def bereken_batterij_power(telemetries):

    geladen = 0.0
    ontladen = 0.0

    kwartieren = {}

    for i in range(len(telemetries) - 1):

        huidige = telemetries[i]
        volgende = telemetries[i + 1]

        try:

            tijd1 = telemetry_tijd(huidige)
            tijd2 = telemetry_tijd(volgende)

            power = float(
                huidige.get("power", 0)
            )

        except (
            ValueError,
            TypeError,
            KeyError
        ):

            continue

        seconden = (
            tijd2 - tijd1
        ).total_seconds()

        if seconden <= 0:
            continue

        wh = (
            abs(power)
            * seconden
            / 3600.0
        )

        if power > 0:

            geladen += wh

        elif power < 0:

            ontladen += wh

        # ------------------------------------------------------
        # Kwartier bepalen
        # ------------------------------------------------------

        kwartier_minuut = (
            tijd1.minute // 15
        ) * 15

        kwartier = tijd1.replace(
            minute=kwartier_minuut,
            second=0
        )

        sleutel = kwartier.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        if sleutel not in kwartieren:

            kwartieren[sleutel] = {
                "laden": 0.0,
                "ontladen": 0.0
            }

        if power > 0:

            kwartieren[sleutel]["laden"] += wh

        elif power < 0:

            kwartieren[sleutel]["ontladen"] += wh

    return (
        geladen,
        ontladen,
        kwartieren
    )


# --------------------------------------------------------------
# SOC ENERGIE
# --------------------------------------------------------------

def bereken_soc_energie(
    eerste,
    laatste
):

    soc_begin = float(
        eerste.get(
            "batteryPercentageState",
            0
        )
    )

    soc_einde = float(
        laatste.get(
            "batteryPercentageState",
            0
        )
    )

    capaciteit_begin = float(
        eerste.get(
            "fullPackEnergyAvailable",
            0
        )
    )

    capaciteit_einde = float(
        laatste.get(
            "fullPackEnergyAvailable",
            0
        )
    )

    # We gebruiken de gemiddelde batterijcapaciteit.
    capaciteit_gemiddeld = (
        capaciteit_begin
        + capaciteit_einde
    ) / 2.0

    energie_begin = (
        soc_begin
        / 100.0
        * capaciteit_begin
    )

    energie_einde = (
        soc_einde
        / 100.0
        * capaciteit_einde
    )

    energie_verschil = (
        energie_einde
        - energie_begin
    )

    return {
        "soc_begin": soc_begin,
        "soc_einde": soc_einde,
        "capaciteit_begin": capaciteit_begin,
        "capaciteit_einde": capaciteit_einde,
        "capaciteit_gemiddeld": capaciteit_gemiddeld,
        "energie_begin": energie_begin,
        "energie_einde": energie_einde,
        "energie_verschil": energie_verschil
    }


# --------------------------------------------------------------
# LIFETIME BATTERIJ
# --------------------------------------------------------------

def bereken_lifetime(
    eerste,
    laatste
):

    charged_begin = float(
        eerste.get(
            "lifeTimeEnergyCharged",
            0
        )
    )

    charged_einde = float(
        laatste.get(
            "lifeTimeEnergyCharged",
            0
        )
    )

    discharged_begin = float(
        eerste.get(
            "lifeTimeEnergyDischarged",
            0
        )
    )

    discharged_einde = float(
        laatste.get(
            "lifeTimeEnergyDischarged",
            0
        )
    )

    geladen = (
        charged_einde
        - charged_begin
    )

    ontladen = (
        discharged_einde
        - discharged_begin
    )

    return {
        "geladen": geladen,
        "ontladen": ontladen,
        "netto": geladen - ontladen
    }


# --------------------------------------------------------------
# BATTERIJ PER KWARTIER
# --------------------------------------------------------------

def print_kwartieren(kwartieren):

    print()
    print("Batterij per kwartier")
    print("-----------------------------------------------")
    print(
        f"{'Tijd':<22}"
        f"{'Laden Wh':>12}"
        f"{'Ontladen Wh':>15}"
    )
    print("-" * 49)

    for tijd in sorted(kwartieren):

        data = kwartieren[tijd]

        # Alleen kwartieren tonen waarin iets gebeurde.
        if (
            data["laden"] == 0
            and data["ontladen"] == 0
        ):
            continue

        print(
            f"{tijd:<22}"
            f"{data['laden']:>12.1f}"
            f"{data['ontladen']:>15.1f}"
        )


# --------------------------------------------------------------
# ANALYSE DAG
# --------------------------------------------------------------

def analyseer_dag(datum):

    print()
    print("=" * 60)
    print(f"DAG: {datum}")
    print("=" * 60)

    # ==========================================================
    # ENERGY DETAILS
    # ==========================================================

    energy_data = haal_energy_details(datum)

    if energy_data is None:

        print(
            f"EnergyDetails kon niet worden "
            f"opgehaald voor {datum}."
        )

        return None

    energy = lees_energy_details(
        energy_data
    )

    if energy is None:
        return None

    production = energy.get(
        "Production",
        0
    )

    self_consumption = energy.get(
        "SelfConsumption",
        0
    )

    feed_in = energy.get(
        "FeedIn",
        0
    )

    consumption = energy.get(
        "Consumption",
        0
    )

    purchased = energy.get(
        "Purchased",
        0
    )

    print()
    print("SolarEdge energiebalans")
    print("--------------------------------")

    print_energie(
        "Production",
        production
    )

    print_energie(
        "SelfConsumption",
        self_consumption
    )

    print_energie(
        "FeedIn",
        feed_in
    )

    print_energie(
        "Consumption",
        consumption
    )

    print_energie(
        "Purchased",
        purchased
    )

    # ==========================================================
    # STORAGE
    # ==========================================================

    storage_response = haal_storage_data(
        datum
    )

    if storage_response is None:
        return None

    battery = haal_batterij(
        storage_response
    )

    if battery is None:
        return None

    print()
    print("Batterij")
    print("--------------------------------")

    nameplate = battery.get(
        "nameplate"
    )

    model = battery.get(
        "modelNumber"
    )

    telemetry_count = battery.get(
        "telemetryCount"
    )

    print(
        f"Naam: {nameplate} Wh"
    )

    print(
        f"Model: {model}"
    )

    print(
        f"Aantal telemetries: "
        f"{telemetry_count}"
    )

    telemetries = battery.get(
        "telemetries",
        []
    )

    if not telemetries:

        print(
            "Geen telemetries gevonden."
        )

        return None

    # ==========================================================
    # EERSTE / LAATSTE TELEMETRY
    # ==========================================================

    eerste = telemetries[0]
    laatste = telemetries[-1]

    # ==========================================================
    # LIFETIME
    # ==========================================================

    lifetime = bereken_lifetime(
        eerste,
        laatste
    )

    print()
    print("Lifetime batterij")
    print("--------------------------------")

    print_energie(
        "Geladen",
        lifetime["geladen"]
    )

    print_energie(
        "Ontladen",
        lifetime["ontladen"]
    )

    print_energie(
        "Netto verandering",
        lifetime["netto"]
    )

    # ==========================================================
    # POWER
    # ==========================================================

    (
        geladen_power,
        ontladen_power,
        kwartieren
    ) = bereken_batterij_power(
        telemetries
    )

    print()
    print("Batterij berekend uit power")
    print("--------------------------------")

    print_energie(
        "Geschat geladen",
        geladen_power
    )

    print_energie(
        "Geschat ontladen",
        ontladen_power
    )

    # ==========================================================
    # SOC
    # ==========================================================

    soc = bereken_soc_energie(
        eerste,
        laatste
    )

    print()
    print("Batterij volgens SOC")
    print("--------------------------------")

    print(
        f"SOC begin             : "
        f"{soc['soc_begin']:8.2f} %"
    )

    print(
        f"SOC einde             : "
        f"{soc['soc_einde']:8.2f} %"
    )

    print_energie(
        "Energieverschil SOC",
        soc["energie_verschil"]
    )

    # ==========================================================
    # VERSCHIL LIFETIME / POWER
    # ==========================================================

    verschil_laden = (
        geladen_power
        - lifetime["geladen"]
    )

    verschil_ontladen = (
        ontladen_power
        - lifetime["ontladen"]
    )

    print()
    print("Verschil lifetime / power")
    print("--------------------------------")

    print_energie(
        "Laden verschil",
        verschil_laden
    )

    print_energie(
        "Ontladen verschil",
        verschil_ontladen
    )

    # ==========================================================
    # SOC VERSUS POWER
    # ==========================================================

    netto_power = (
        geladen_power
        - ontladen_power
    )

    energie_soc = (
        soc["energie_verschil"]
    )

    verschil_soc_power = (
        energie_soc
        - netto_power
    )

    print()
    print("SOC versus power")
    print("--------------------------------")

    print_energie(
        "Energie volgens SOC",
        energie_soc
    )

    print_energie(
        "Energie volgens power",
        netto_power
    )

    print_energie(
        "Verschil SOC - power",
        verschil_soc_power
    )

    # ==========================================================
    # CONTROLES
    # ==========================================================

    controle_productie = (
        production
        - self_consumption
        - feed_in
    )

    controle_consumption = (
        consumption
        - self_consumption
        - purchased
    )

    print()
    print("Controles")
    print("--------------------------------")

    print(
        "Production = "
        "SelfConsumption + FeedIn : "
        f"verschil "
        f"{controle_productie:.0f} Wh"
    )

    print(
        "Consumption = "
        "SelfConsumption + Purchased : "
        f"verschil "
        f"{controle_consumption:.0f} Wh"
    )

    # ==========================================================
    # BATTERIJANALYSE
    # ==========================================================

    print()
    print("Batterijanalyse")
    print("--------------------------------")

    print(
        f"Production                 : "
        f"{production:8.0f} Wh"
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
        f"Production + ontladen "
        f"- geladen                 : "
        f"{production + ontladen_power - geladen_power:8.0f} Wh"
    )

    # ==========================================================
    # KWARTIERDATA
    # ==========================================================

    print_kwartieren(
        kwartieren
    )

    # ==========================================================
    # RESULTAAT
    # ==========================================================

    return {
        "production": production,
        "consumption": consumption,
        "self_consumption": self_consumption,
        "feed_in": feed_in,
        "purchased": purchased,

        "battery_lifetime_loaded":
            lifetime["geladen"],

        "battery_lifetime_discharged":
            lifetime["ontladen"],

        "battery_loaded":
            geladen_power,

        "battery_discharged":
            ontladen_power,

        "battery_net":
            netto_power,

        "soc_energy":
            energie_soc,

        "soc_difference":
            verschil_soc_power,

        "battery": battery,

        "kwartieren":
            kwartieren
    }


# ==============================================================
# HOOFDPROGRAMMA
# ==============================================================

if __name__ == "__main__":

    datums = [
        "2026-08-07",
        "2026-08-08"
    ]

    resultaten = {}

    # ==========================================================
    # DAGEN ANALYSEREN
    # ==========================================================

    for datum in datums:

        print()
        print("#" * 60)
        print(
            f"Gegevens ophalen voor {datum}"
        )
        print("#" * 60)

        resultaat = analyseer_dag(
            datum
        )

        if resultaat is not None:

            resultaten[datum] = (
                resultaat
            )

        else:

            print(
                f"Geen volledige gegevens "
                f"voor {datum}"
            )

    # ==========================================================
    # VERGELIJKING DAGEN
    # ==========================================================

    if len(resultaten) == len(datums):

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
            f"{'Bat laden':>14}"
            f"{'Bat ontladen':>16}"
        )

        print("-" * 72)

        for datum in datums:

            dag = resultaten[datum]

            print(
                f"{datum:<12}"
                f"{dag['production']:>12.0f}"
                f"{dag['consumption']:>14.0f}"
                f"{dag['battery_loaded']:>14.0f}"
                f"{dag['battery_discharged']:>16.0f}"
            )

        # ------------------------------------------------------
        # Verschil
        # ------------------------------------------------------

        if len(datums) >= 2:

            dag1 = resultaten[
                datums[0]
            ]

            dag2 = resultaten[
                datums[1]
            ]

            print()
            print(
                "Verschil dag 2 - dag 1"
            )

            print(
                "--------------------------------"
            )

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

            print()
            print(
                "SOC versus power"
            )

            print(
                "--------------------------------"
            )

            print(
                f"{datums[0]} : "
                f"{dag1['soc_energy']:8.0f} Wh SOC, "
                f"{dag1['battery_net']:8.0f} Wh power"
            )

            print(
                f"{datums[1]} : "
                f"{dag2['soc_energy']:8.0f} Wh SOC, "
                f"{dag2['battery_net']:8.0f} Wh power"
            )

    else:

        print()
        print(
            "Er zijn niet genoeg dagen "
            "beschikbaar voor de vergelijking."
        )