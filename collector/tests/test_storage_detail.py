# --------------------------------------------------------------
# test_storage_detail.py
#
# Analyse SolarEdge batterijtelemetrie
# Vergelijkt:
#   - Lifetime energy
#   - Power-integratie
#   - SOC-energie
#
# --------------------------------------------------------------

import requests
from datetime import datetime, timedelta

from ..config import laad_configuratie


# --------------------------------------------------------------
# Configuratie
# --------------------------------------------------------------

config = laad_configuratie()

if config is None:
    raise SystemExit("Configuratie kon niet worden geladen.")

SITE_ID = config["site_id"]
API_KEY = config["api_key"]

BASE_URL = "https://monitoringapi.solaredge.com"


DATUM = "2026-08-07"

TIJDVENSTERS = [
    ("00:00", "01:00"),
    ("10:00", "11:00"),
    ("13:00", "14:00"),
]


# --------------------------------------------------------------
# Hulpfuncties
# --------------------------------------------------------------

def wh_kwh(waarde):
    return f"{waarde:.1f} Wh ({waarde / 1000:.3f} kWh)"


def parse_timestamp(timestamp):
    return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")


def binnen_tijdvenster(timestamp, datum, begin, einde):

    dt = parse_timestamp(timestamp)

    begin_dt = datetime.strptime(
        f"{datum} {begin}:00",
        "%Y-%m-%d %H:%M:%S"
    )

    einde_dt = datetime.strptime(
        f"{datum} {einde}:00",
        "%Y-%m-%d %H:%M:%S"
    )

    return begin_dt <= dt < einde_dt


# --------------------------------------------------------------
# Storage API ophalen
# --------------------------------------------------------------

def haal_storage_data():

    url = f"{BASE_URL}/site/{SITE_ID}/storageData"

    params = {
        "api_key": API_KEY,
        "startTime": f"{DATUM} 00:00:00",
        "endTime": f"{DATUM} 23:59:59",
        "timeUnit": "QUARTER_OF_AN_HOUR",
    }

    response = requests.get(url, params=params)

    print(f"Storage HTTP: {response.status_code}")

    if response.status_code != 200:
        print(response.text)
        return None

    return response.json()


# --------------------------------------------------------------
# Batterij uitlezen
# --------------------------------------------------------------

def haal_batterij(storage_data):

    storage = storage_data.get("storageData")

    if not storage:
        print("Geen storageData gevonden.")
        return None

    # SolarEdge kan hier verschillende structuren teruggeven.
    # Zoek rechtstreeks naar batteries.

    batteries = None

    if isinstance(storage, dict):
        batteries = storage.get("batteries")

    if batteries is None:
        print("Onverwachte structuur:")
        print(storage.keys() if isinstance(storage, dict) else type(storage))
        return None

    if not batteries:
        print("Geen batterijen gevonden.")
        return None

    return batteries[0]


# --------------------------------------------------------------
# Energie volgens power
# --------------------------------------------------------------

def bereken_power_energie(telemetries):

    geladen = 0.0
    ontladen = 0.0

    if len(telemetries) < 2:
        return geladen, ontladen

    for i in range(len(telemetries) - 1):

        huidige = telemetries[i]
        volgende = telemetries[i + 1]

        tijd1 = parse_timestamp(huidige["timeStamp"])
        tijd2 = parse_timestamp(volgende["timeStamp"])

        seconden = (tijd2 - tijd1).total_seconds()

        # Power is W.
        #
        # Energie = vermogen * tijd
        #
        # W * seconden / 3600 = Wh

        vermogen = huidige.get("power")

        if vermogen is None:
            continue

        energie = abs(vermogen) * seconden / 3600

        if vermogen > 0:
            geladen += energie

        elif vermogen < 0:
            ontladen += energie

    return geladen, ontladen


# --------------------------------------------------------------
# Energie volgens SOC
# --------------------------------------------------------------

def bereken_soc_energie(telemetries):

    if len(telemetries) < 2:
        return 0.0

    eerste = telemetries[0]
    laatste = telemetries[-1]

    soc1 = eerste["batteryPercentageState"]
    soc2 = laatste["batteryPercentageState"]

    capaciteit1 = eerste.get("fullPackEnergyAvailable")
    capaciteit2 = laatste.get("fullPackEnergyAvailable")

    if capaciteit1 is None or capaciteit2 is None:
        return 0.0

    # Gebruik de gemiddelde beschikbare batterijcapaciteit.
    capaciteit = (capaciteit1 + capaciteit2) / 2

    verschil_soc = soc2 - soc1

    return verschil_soc / 100 * capaciteit


# --------------------------------------------------------------
# Analyse tijdvenster
# --------------------------------------------------------------

def analyseer_tijdvenster(telemetries, begin, einde):

    geselecteerd = [
        t for t in telemetries
        if binnen_tijdvenster(
            t["timeStamp"],
            DATUM,
            begin,
            einde
        )
    ]

    if len(geselecteerd) < 2:
        print("Te weinig telemetriegegevens.")
        return

    print()
    print("=" * 70)
    print(f"TIJDVENSTER {begin} - {einde}")
    print("=" * 70)

    print()
    print("Telemetrie")
    print("-" * 70)

    print(
        f"{'Tijd':20} "
        f"{'Power W':>10} "
        f"{'SOC %':>9} "
        f"{'Charged Wh':>14} "
        f"{'Discharged Wh':>15}"
    )

    print("-" * 70)

    for t in geselecteerd:

        print(
            f"{t['timeStamp']:20} "
            f"{t.get('power', 0):10.1f} "
            f"{t.get('batteryPercentageState', 0):9.2f} "
            f"{t.get('lifeTimeEnergyCharged', 0):14.0f} "
            f"{t.get('lifeTimeEnergyDischarged', 0):15.0f}"
        )

    eerste = geselecteerd[0]
    laatste = geselecteerd[-1]

    # ----------------------------------------------------------
    # Lifetime
    # ----------------------------------------------------------

    lifetime_laden = (
        laatste["lifeTimeEnergyCharged"]
        - eerste["lifeTimeEnergyCharged"]
    )

    lifetime_ontladen = (
        laatste["lifeTimeEnergyDischarged"]
        - eerste["lifeTimeEnergyDischarged"]
    )

    # ----------------------------------------------------------
    # Power
    # ----------------------------------------------------------

    power_laden, power_ontladen = bereken_power_energie(
        geselecteerd
    )

    # ----------------------------------------------------------
    # SOC
    # ----------------------------------------------------------

    soc_begin = eerste["batteryPercentageState"]
    soc_einde = laatste["batteryPercentageState"]

    capaciteit_begin = eerste["fullPackEnergyAvailable"]
    capaciteit_einde = laatste["fullPackEnergyAvailable"]

    capaciteit_gemiddeld = (
        capaciteit_begin + capaciteit_einde
    ) / 2

    soc_verschil = soc_einde - soc_begin

    energie_soc = (
        soc_verschil / 100
        * capaciteit_gemiddeld
    )

    # Positief = laden
    # Negatief = ontladen

    energie_power = power_laden - power_ontladen

    verschil_soc_power = energie_soc - energie_power

    # ----------------------------------------------------------
    # Resultaat
    # ----------------------------------------------------------

    print()
    print("Resultaat tijdvenster")
    print("-" * 70)

    print(f"SOC begin             : {soc_begin:8.2f} %")
    print(f"SOC einde             : {soc_einde:8.2f} %")
    print(f"SOC verandering       : {soc_verschil:8.2f} %")

    print()

    print(
        f"Energie volgens SOC   : "
        f"{energie_soc:8.1f} Wh "
        f"({energie_soc / 1000:.3f} kWh)"
    )

    print(
        f"Energie volgens power : "
        f"{energie_power:8.1f} Wh "
        f"({energie_power / 1000:.3f} kWh)"
    )

    print(
        f"Verschil SOC - power  : "
        f"{verschil_soc_power:8.1f} Wh "
        f"({verschil_soc_power / 1000:.3f} kWh)"
    )

    # ----------------------------------------------------------
    # Detail laden / ontladen
    # ----------------------------------------------------------

    print()
    print("Detail")
    print("-" * 70)

    print(
        f"Lifetime geladen      : "
        f"{lifetime_laden:8.1f} Wh"
    )

    print(
        f"Power berekend laden  : "
        f"{power_laden:8.1f} Wh"
    )

    print(
        f"Lifetime ontladen     : "
        f"{lifetime_ontladen:8.1f} Wh"
    )

    print(
        f"Power berekend ontl.  : "
        f"{power_ontladen:8.1f} Wh"
    )

    # ----------------------------------------------------------
    # SOC controle
    # ----------------------------------------------------------

    print()
    print("Controle")
    print("-" * 70)

    print(
        f"Batterijcapaciteit begin : "
        f"{capaciteit_begin:8.1f} Wh"
    )

    print(
        f"Batterijcapaciteit einde : "
        f"{capaciteit_einde:8.1f} Wh"
    )

    print(
        f"Gemiddelde capaciteit    : "
        f"{capaciteit_gemiddeld:8.1f} Wh"
    )

    print(
        f"SOC energieverschil      : "
        f"{energie_soc:8.1f} Wh"
    )

    print(
        f"Netto lifetime            : "
        f"{lifetime_laden - lifetime_ontladen:8.1f} Wh"
    )

    print(
        f"Netto power              : "
        f"{energie_power:8.1f} Wh"
    )


# --------------------------------------------------------------
# MAIN
# --------------------------------------------------------------

print()
print("#" * 70)
print(f"SolarEdge batterij detailanalyse - {DATUM}")
print("#" * 70)

storage_data = haal_storage_data()

if storage_data is None:
    raise SystemExit("Storagegegevens konden niet worden opgehaald.")

battery = haal_batterij(storage_data)

if battery is None:
    raise SystemExit("Batterij kon niet worden gevonden.")


# --------------------------------------------------------------
# Batterijgegevens
# --------------------------------------------------------------

print()
print("Batterij")
print("-" * 70)

print(f"Naam: {battery.get('nameplate')} Wh")
print(f"Model: {battery.get('modelNumber')}")

telemetries = battery.get("telemetries", [])

print(f"Aantal telemetries: {len(telemetries)}")


# --------------------------------------------------------------
# Eenhedencontrole
# --------------------------------------------------------------

if telemetries:

    eerste = telemetries[0]

    print()
    print("Eenhedencontrole")
    print("-" * 70)

    print(
        f"power                    : "
        f"{eerste.get('power')} W"
    )

    print(
        f"lifeTimeEnergyCharged   : "
        f"{eerste.get('lifeTimeEnergyCharged')} Wh"
    )

    print(
        f"lifeTimeEnergyDischarged: "
        f"{eerste.get('lifeTimeEnergyDischarged')} Wh"
    )

    print(
        f"fullPackEnergyAvailable : "
        f"{eerste.get('fullPackEnergyAvailable')} Wh"
    )

    print(
        f"batteryPercentageState  : "
        f"{eerste.get('batteryPercentageState')} %"
    )


# --------------------------------------------------------------
# Tijdvensters analyseren
# --------------------------------------------------------------

for begin, einde in TIJDVENSTERS:

    analyseer_tijdvenster(
        telemetries,
        begin,
        einde
    )


print()
print("#" * 70)
print("Einde analyse")
print("#" * 70)