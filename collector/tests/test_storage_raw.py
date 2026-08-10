# --------------------------------------------------------------
# test_storage_raw.py
#
# Analyse van SolarEdge Storage API
#
# Versie 3.0
#
# Doel:
#   - RAW storageData ophalen
#   - laad- en ontlaadperioden automatisch detecteren
#   - energie vergelijken via:
#       1. lifetime counters
#       2. power x tijd
#       3. SOC x effectieve capaciteit
#   - effectieve batterijcapaciteit bepalen uit
#     fullPackEnergyAvailable
#   - primaire energiemethode automatisch bepalen
#   - afwijkingen automatisch signaleren
#
# Configuratie:
#   config.py
#   .env
#
# --------------------------------------------------------------

import json
import requests
from datetime import datetime
from ..config import laad_configuratie


# ==============================================================
# INSTELLINGEN
# ==============================================================

START_DATUM = "2026-08-07"
START_TIJD = "00:00:00"

EIND_DATUM = "2026-08-07"
EIND_TIJD = "23:59:59"

TIMEOUT = 30

# Minimale SOC-verandering om een periode te beschouwen
# als een echte laad- of ontlaadperiode.
MIN_SOC_CHANGE = 0.10

# Kleine schommelingen rond hetzelfde SOC negeren.
SOC_TOLERANTIE = 0.05

# Een periode moet minstens zo lang duren.
MIN_PERIODE_MINUTEN = 5

# Wanneer twee bruikbare energiemethodes meer dan dit
# percentage verschillen, geven we een waarschuwing.
ENERGIE_TOLERANTIE_PERCENT = 10.0


# ==============================================================
# HULPFUNCTIES
# ==============================================================

def print_lijn(teken="=", lengte=80):
    print(teken * lengte)


def parse_timestamp(value):
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def format_uur(timestamp):
    return timestamp.strftime("%H:%M")


def bereken_minuten(start, einde):
    return (einde - start).total_seconds() / 60.0


def bereken_power_energie(power_w, minuten):
    """
    Energie uit vermogen.

    Wh = W x uren
    """
    return power_w * minuten / 60.0


def procent_verschil(waarde1, waarde2):
    """
    Procentueel verschil van waarde1 t.o.v. waarde2.
    """
    if waarde2 == 0:
        return None

    return ((waarde1 - waarde2) / waarde2) * 100.0


def veilige_float(value, default=0.0):
    if value is None:
        return default

    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# ==============================================================
# API OPHALEN
# ==============================================================

def haal_storage_data(config):

    site_id = config["site_id"]
    api_key = config["api_key"]

    url = (
        f"https://monitoringapi.solaredge.com/"
        f"site/{site_id}/storageData"
    )

    params = {
        "api_key": api_key,
        "startTime": f"{START_DATUM} {START_TIJD}",
        "endTime": f"{EIND_DATUM} {EIND_TIJD}",
    }

    print()
    print("=" * 80)
    print("SolarEdge RAW Storage analyse")
    print("=" * 80)

    print()
    print(
        f"Periode : {START_DATUM} {START_TIJD} -> "
        f"{EIND_DATUM} {EIND_TIJD}"
    )

    print(f"URL     : {url}")

    try:
        response = requests.get(
            url,
            params=params,
            timeout=TIMEOUT
        )

    except requests.RequestException as fout:

        print()
        print("FOUT bij API-request:")
        print(fout)

        return None

    print()
    print(f"HTTP status: {response.status_code}")

    if response.status_code != 200:

        print()
        print("API geeft geen HTTP 200.")
        print(response.text)

        return None

    try:
        data = response.json()

    except ValueError:

        print()
        print("FOUT: antwoord is geen geldige JSON.")
        print(response.text)

        return None

    return data


# ==============================================================
# BATTERIJ SELECTEREN
# ==============================================================

def haal_batterij(data):

    try:
        storage_data = data["storageData"]
        batteries = storage_data["batteries"]

    except (KeyError, TypeError):

        print(
            "FOUT: structuur "
            "storageData/batteries niet gevonden."
        )

        return None

    if not batteries:

        print("Geen batterijen gevonden.")

        return None

    # Voorlopig analyseren we de eerste batterij.
    return batteries[0]


# ==============================================================
# TELEMETRIES NORMALISEREN
# ==============================================================

def normaliseer_telemetries(batterij):

    telemetries = batterij.get("telemetries", [])

    resultaat = []

    for t in telemetries:

        try:
            timestamp = parse_timestamp(
                t["timeStamp"]
            )

        except (KeyError, ValueError):
            continue

        resultaat.append({

            "timestamp": timestamp,

            "timeStamp": t.get("timeStamp"),

            "power": veilige_float(
                t.get("power")
            ),

            "batteryState": t.get(
                "batteryState"
            ),

            "charged": veilige_float(
                t.get("lifeTimeEnergyCharged")
            ),

            "discharged": veilige_float(
                t.get("lifeTimeEnergyDischarged")
            ),

            "soc": veilige_float(
                t.get("batteryPercentageState")
            ),

            "capacity": veilige_float(
                t.get("fullPackEnergyAvailable")
            ),

            "temperature": veilige_float(
                t.get("internalTemp")
            ),

            "ACGridCharging": t.get(
                "ACGridCharging"
            ),
        })

    resultaat.sort(
        key=lambda x: x["timestamp"]
    )

    return resultaat


# ==============================================================
# PERIODE-DETECTIE
# ==============================================================

def detecteer_perioden(telemetries):

    laadperioden = []
    ontlaadperioden = []

    if len(telemetries) < 2:

        return (
            laadperioden,
            ontlaadperioden
        )

    huidige_richting = None
    periode_start = None
    vorige = None

    for huidige in telemetries:

        if vorige is None:

            vorige = huidige
            continue

        delta_soc = (
            huidige["soc"] -
            vorige["soc"]
        )

        if delta_soc > SOC_TOLERANTIE:

            richting = "laden"

        elif delta_soc < -SOC_TOLERANTIE:

            richting = "ontladen"

        else:

            richting = "neutraal"

        # ------------------------------------------------------
        # Begin van een nieuwe periode
        # ------------------------------------------------------

        if richting != huidige_richting:

            # Bestaande periode afsluiten
            if huidige_richting in (
                "laden",
                "ontladen"
            ):

                periode_einde = vorige

                duur = bereken_minuten(
                    periode_start["timestamp"],
                    periode_einde["timestamp"]
                )

                delta = abs(
                    periode_einde["soc"] -
                    periode_start["soc"]
                )

                if (
                    duur >= MIN_PERIODE_MINUTEN
                    and delta >= MIN_SOC_CHANGE
                ):

                    periode = {
                        "richting":
                            huidige_richting,

                        "start":
                            periode_start,

                        "einde":
                            periode_einde,
                    }

                    if huidige_richting == "laden":

                        laadperioden.append(
                            periode
                        )

                    else:

                        ontlaadperioden.append(
                            periode
                        )

            # Nieuwe periode starten
            if richting in (
                "laden",
                "ontladen"
            ):

                periode_start = vorige
                huidige_richting = richting

            else:

                periode_start = None
                huidige_richting = None

        vorige = huidige

    # ----------------------------------------------------------
    # Laatste periode afsluiten
    # ----------------------------------------------------------

    if huidige_richting in (
        "laden",
        "ontladen"
    ):

        periode_einde = telemetries[-1]

        duur = bereken_minuten(
            periode_start["timestamp"],
            periode_einde["timestamp"]
        )

        delta = abs(
            periode_einde["soc"] -
            periode_start["soc"]
        )

        if (
            duur >= MIN_PERIODE_MINUTEN
            and delta >= MIN_SOC_CHANGE
        ):

            periode = {
                "richting":
                    huidige_richting,

                "start":
                    periode_start,

                "einde":
                    periode_einde,
            }

            if huidige_richting == "laden":

                laadperioden.append(
                    periode
                )

            else:

                ontlaadperioden.append(
                    periode
                )

    return (
        laadperioden,
        ontlaadperioden
    )


# ==============================================================
# PERIODEN TONEN
# ==============================================================

def toon_gevonden_perioden(
    laadperioden,
    ontlaadperioden
):

    print()
    print("=" * 110)
    print("GEVONDEN LAAD- EN ONTLAADPERIODEN")
    print("=" * 110)

    print()
    print(
        f"Aantal laadperioden    : "
        f"{len(laadperioden)}"
    )

    for i, periode in enumerate(
        laadperioden,
        1
    ):

        start = periode["start"]
        einde = periode["einde"]

        print(
            f"  Laden {i}: "
            f"{format_uur(start['timestamp'])} -> "
            f"{format_uur(einde['timestamp'])} | "
            f"SOC {start['soc']:.2f}% -> "
            f"{einde['soc']:.2f}%"
        )

    print()
    print(
        f"Aantal ontlaadperioden: "
        f"{len(ontlaadperioden)}"
    )

    for i, periode in enumerate(
        ontlaadperioden,
        1
    ):

        start = periode["start"]
        einde = periode["einde"]

        print(
            f"  Ontladen {i}: "
            f"{format_uur(start['timestamp'])} -> "
            f"{format_uur(einde['timestamp'])} | "
            f"SOC {start['soc']:.2f}% -> "
            f"{einde['soc']:.2f}%"
        )


# ==============================================================
# ENERGIE PER INTERVAL
# ==============================================================

def analyseer_interval(
    vorige,
    huidige
):
    """
    Analyseer één telemetrie-interval.

    Power × tijd wordt berekend met het gemiddelde
    vermogen van begin- en eindpunt (trapeziumregel).
    """

    minuten = bereken_minuten(
        vorige["timestamp"],
        huidige["timestamp"]
    )

    delta_soc = (
        huidige["soc"] -
        vorige["soc"]
    )

    # ----------------------------------------------------------
    # Gemiddelde effectieve batterijcapaciteit
    # ----------------------------------------------------------

    capaciteit = (
        vorige["capacity"] +
        huidige["capacity"]
    ) / 2.0

    # ----------------------------------------------------------
    # Energie volgens SOC
    # ----------------------------------------------------------

    soc_energie = (
        delta_soc / 100.0
    ) * capaciteit

    # ----------------------------------------------------------
    # Energie volgens power
    #
    # Gebruik gemiddelde power van begin- en eindpunt.
    # Dit is nauwkeuriger dan alleen de power van het
    # eindpunt te gebruiken.
    # ----------------------------------------------------------

    gemiddeld_power = (
        vorige["power"] +
        huidige["power"]
    ) / 2.0

    power_energie = bereken_power_energie(
        gemiddeld_power,
        minuten
    )

    # ----------------------------------------------------------
    # Lifetime counters
    # ----------------------------------------------------------

    delta_charge = (
        huidige["charged"] -
        vorige["charged"]
    )

    delta_discharge = (
        huidige["discharged"] -
        vorige["discharged"]
    )

    return {

        "minuten":
            minuten,

        "delta_soc":
            delta_soc,

        "soc_energie":
            soc_energie,

        "gemiddeld_power":
            gemiddeld_power,

        "power_energie":
            power_energie,

        "delta_charge":
            delta_charge,

        "delta_discharge":
            delta_discharge,
    }


# ==============================================================
# EFFECTIEVE CAPACITEIT
# ==============================================================

def bereken_effectieve_capaciteit(punten):

    capaciteiten = [
        p["capacity"]
        for p in punten
        if p["capacity"] > 0
    ]

    if not capaciteiten:
        return None

    return sum(capaciteiten) / len(
        capaciteiten
    )


def toon_capaciteit(punten):

    capaciteiten = [
        p["capacity"]
        for p in punten
        if p["capacity"] > 0
    ]

    if not capaciteiten:

        print()
        print(
            "Effectieve capaciteit: "
            "niet beschikbaar"
        )

        return None

    gemiddeld = (
        sum(capaciteiten) /
        len(capaciteiten)
    )

    minimum = min(capaciteiten)
    maximum = max(capaciteiten)

    print()
    print("Effectieve capaciteit:")

    print(
        f"  Begin      : "
        f"{punten[0]['capacity']:.1f} Wh"
    )

    print(
        f"  Einde      : "
        f"{punten[-1]['capacity']:.1f} Wh"
    )

    print(
        f"  Gemiddeld  : "
        f"{gemiddeld:.1f} Wh"
    )

    print(
        f"  Min        : "
        f"{minimum:.1f} Wh"
    )

    print(
        f"  Max        : "
        f"{maximum:.1f} Wh"
    )

    return gemiddeld


# ==============================================================
# PRIMAIRE ENERGIEMETHODE BEPALEN
# ==============================================================

def bepaal_primaire_methode(
    richting,
    lifetime,
    soc
):
    """
    Bepaal welke energiemeting als primaire methode
    moet worden gebruikt.
    """

    # ----------------------------------------------------------
    # LADEN
    #
    # LifetimeEnergyCharged blijkt in de huidige data
    # zeer goed overeen te komen met SOC × capaciteit.
    # ----------------------------------------------------------

    if richting == "laden":

        if soc > 0:

            verschil = abs(
                procent_verschil(
                    lifetime,
                    soc
                )
            )

            if verschil <= ENERGIE_TOLERANTIE_PERCENT:

                return "LifetimeEnergyCharged"

        # Lifetime counter wijkt te veel af.
        return "SOC × capaciteit"

    # ----------------------------------------------------------
    # ONTLADEN
    #
    # LifetimeEnergyDischarged is in de huidige SolarEdge-data
    # niet bruikbaar.
    # ----------------------------------------------------------

    if richting == "ontladen":

        return "SOC × capaciteit"

    return "SOC × capaciteit"


# ==============================================================
# PERIODE ANALYSEREN
# ==============================================================

def analyseer_periode_met_telemetries(
    periode,
    telemetries
):

    richting = periode["richting"]

    start_time = periode["start"]["timestamp"]
    einde_time = periode["einde"]["timestamp"]

    punten = [
        t
        for t in telemetries
        if start_time <= t["timestamp"] <= einde_time
    ]

    if len(punten) < 2:

        return None

    start = punten[0]
    einde = punten[-1]

    totale_power = 0.0
    totale_soc = 0.0

    totale_charge = 0.0
    totale_discharge = 0.0

    print()
    print("=" * 110)

    if richting == "laden":

        print("LAADPERIODE")

    else:

        print("ONTLAADPERIODE")

    print("=" * 110)

    duur = bereken_minuten(
        start["timestamp"],
        einde["timestamp"]
    )

    delta_soc = (
        einde["soc"] -
        start["soc"]
    )

    print()
    print(
        f"Periode      : "
        f"{start['timeStamp']} -> "
        f"{einde['timeStamp']}"
    )

    print(
        f"Duur         : "
        f"{duur:.1f} minuten"
    )

    print(
        f"SOC          : "
        f"{start['soc']:.2f}% -> "
        f"{einde['soc']:.2f}%"
    )

    print(
        f"Δ SOC        : "
        f"{delta_soc:+.2f}%"
    )

    # ----------------------------------------------------------
    # Effectieve capaciteit
    # ----------------------------------------------------------

    effectieve_capaciteit = (
        toon_capaciteit(punten)
    )

    print()
    print("-" * 110)

    print(
        "INTERVAL                          "
        "SOC       POWER     Δ CHARGE     "
        "Δ DISCH.     POWER×TIJD     SOC×CAP."
    )

    print("-" * 110)

    for i in range(
        1,
        len(punten)
    ):

        vorige = punten[i - 1]
        huidige = punten[i]

        interval = analyseer_interval(
            vorige,
            huidige
        )

        totale_power += (
            interval["power_energie"]
        )

        totale_soc += (
            interval["soc_energie"]
        )

        totale_charge += (
            interval["delta_charge"]
        )

        totale_discharge += (
            interval["delta_discharge"]
        )

        print(
            f"{format_uur(vorige['timestamp'])}-"
            f"{format_uur(huidige['timestamp'])}   "

            f"{vorige['soc']:6.2f}% → "
            f"{huidige['soc']:6.2f}%   "

            f"{interval['gemiddeld_power']:7.0f} W   "

            f"{interval['delta_charge']:10.1f}   "

            f"{interval['delta_discharge']:10.1f}   "

            f"{interval['power_energie']:12.1f}   "

            f"{interval['soc_energie']:10.1f}"
        )

    print("-" * 110)

    print(
        f"TOTAAL                                      "
        f"{totale_charge:10.1f}"
        f"{totale_discharge:12.1f}"
        f"{totale_power:15.1f}"
        f"{totale_soc:14.1f}"
    )

    # ----------------------------------------------------------
    # Energie per richting
    # ----------------------------------------------------------

    if richting == "laden":

        power_energie = totale_power

        soc_energie = totale_soc

        lifetime_energie = (
            einde["charged"] -
            start["charged"]
        )

        lifetime_naam = (
            "LifetimeEnergyCharged"
        )

    else:

        power_energie = abs(
            totale_power
        )

        soc_energie = abs(
            totale_soc
        )

        lifetime_energie = (
            einde["discharged"] -
            start["discharged"]
        )

        lifetime_naam = (
            "LifetimeEnergyDischarged"
        )

    # ----------------------------------------------------------
    # Primaire methode
    # ----------------------------------------------------------

    primaire_methode = (
        bepaal_primaire_methode(
          richting,
          lifetime_energie,
          soc_energie
        )
    )

    if primaire_methode == (
        "LifetimeEnergyCharged"
    ):

        primaire_energie = (
            lifetime_energie
        )

    elif primaire_methode == (
        "Power × tijd"
    ):

        primaire_energie = (
            power_energie
        )

    else:

        primaire_energie = (
            soc_energie
        )

    # ----------------------------------------------------------
    # Energievergelijking
    # ----------------------------------------------------------

    print()
    print("=" * 110)
    print("ENERGIEVERGELIJKING")
    print("=" * 110)

    print()

    print(
        f"1. {lifetime_naam:24s}: "
        f"{lifetime_energie:.1f} Wh"
    )

    print(
        f"2. Power × tijd            : "
        f"{power_energie:.1f} Wh"
    )

    print(
        f"3. SOC × capaciteit        : "
        f"{soc_energie:.1f} Wh"
    )

    print()

    if effectieve_capaciteit is not None:

        print(
            f"Effectieve capaciteit     : "
            f"{effectieve_capaciteit:.1f} Wh"
        )

    else:

        print(
            "Effectieve capaciteit     : "
            "niet beschikbaar"
        )

    # ----------------------------------------------------------
    # Verschillen
    # ----------------------------------------------------------

    verschil_power_soc = (
        power_energie -
        soc_energie
    )

    verschil_power_soc_pct = (
        procent_verschil(
            power_energie,
            soc_energie
        )
    )

    verschil_lifetime_power = (
        lifetime_energie -
        power_energie
    )

    verschil_lifetime_soc = (
        lifetime_energie -
        soc_energie
    )

    lifetime_power_pct = (
        procent_verschil(
            lifetime_energie,
            power_energie
        )
    )

    lifetime_soc_pct = (
        procent_verschil(
            lifetime_energie,
            soc_energie
        )
    )

    print()

    print(
        f"Power × tijd verschil      : "
        f"{verschil_power_soc:+.1f} Wh "
        f"({verschil_power_soc_pct:+.1f}%)"
    )

    print(
        f"Lifetime vs power          : "
        f"{verschil_lifetime_power:+.1f} Wh "
        f"({lifetime_power_pct:+.1f}%)"
    )

    print(
        f"Lifetime vs SOC            : "
        f"{verschil_lifetime_soc:+.1f} Wh "
        f"({lifetime_soc_pct:+.1f}%)"
    )

    # ----------------------------------------------------------
    # Gemiddeld vermogen
    # ----------------------------------------------------------

    if duur > 0:

        gemiddeld_power = (
            power_energie /
            (duur / 60.0)
        )

        gemiddeld_primaire = (
            primaire_energie /
            (duur / 60.0)
        )

    else:

        gemiddeld_power = 0
        gemiddeld_primaire = 0

    print()

    print(
        f"Gemiddeld vermogen volgens "
        f"primaire methode: "
        f"{gemiddeld_primaire:.0f} W"
    )

    print(
        f"Gemiddeld API power: "
        f"{gemiddeld_power:.0f} W"
    )

    # ----------------------------------------------------------
    # CONTROLE
    # ----------------------------------------------------------

    print()
    print("-" * 110)
    print("CONTROLE")
    print("-" * 110)

    waarschuwingen = []

    # ----------------------------------------------------------
    # Lifetime discharged is in deze data niet bruikbaar.
    # ----------------------------------------------------------

    if richting == "ontladen":

        if (
            lifetime_energie == 0
            or lifetime_energie < soc_energie * 0.1
        ):

            print()
            print(
                "ℹ LifetimeEnergyDischarged is "
                "niet bruikbaar als primaire "
                "energiemeting."
            )

    # ----------------------------------------------------------
    # Lifetime charged controleren
    # ----------------------------------------------------------

    if richting == "laden":

        if (
            lifetime_soc_pct is not None
            and abs(lifetime_soc_pct)
            > ENERGIE_TOLERANTIE_PERCENT
        ):

            waarschuwingen.append(
                f"LifetimeEnergyCharged wijkt "
                f"{abs(lifetime_soc_pct):.1f}% af "
                f"van SOC × capaciteit."
            )

    # ----------------------------------------------------------
    # Power versus SOC
    # ----------------------------------------------------------

    if (
        verschil_power_soc_pct is not None
        and abs(verschil_power_soc_pct)
        > ENERGIE_TOLERANTIE_PERCENT
    ):

        waarschuwingen.append(
            f"Power × tijd en SOC × capaciteit "
            f"verschillen "
            f"{abs(verschil_power_soc_pct):.1f}%."
        )

    # ----------------------------------------------------------
    # Resultaat controle
    # ----------------------------------------------------------

    if waarschuwingen:

        print()

        for waarschuwing in waarschuwingen:

            print(
                "⚠ WAARSCHUWING:",
                waarschuwing
            )

        print()

        if (
            richting == "laden"
            and abs(
                lifetime_soc_pct or 0
            ) <= ENERGIE_TOLERANTIE_PERCENT
        ):

            print(
                "CONCLUSIE: de primaire laadenergie "
                "is betrouwbaar; Power × tijd wijkt "
                "enigszins af."
            )

        elif richting == "ontladen":

            print(
                "CONCLUSIE: SOC × capaciteit wordt "
                "als primaire ontlaadenergie gebruikt; "
                "Power × tijd wijkt hiervan af."
            )

        else:

            print(
                "CONCLUSIE: er is een relevante "
                "afwijking tussen één of meer "
                "energiemetingen."
            )

    else:

        print()
        print(
            "OK: de primaire energiemethode "
            "is intern consistent."
        )

    print()
    print(
        f"Primaire energiemethode: "
        f"{primaire_methode}"
    )

    return {

        "richting":
            richting,

        "start":
            start,

        "einde":
            einde,

        "duur":
            duur,

        "capaciteit":
            effectieve_capaciteit,

        "lifetime":
            lifetime_energie,

        "power":
            power_energie,

        "soc":
            soc_energie,

        "primaire_methode":
            primaire_methode,

        "primaire_energie":
            primaire_energie,
    }


# ==============================================================
# AUTOMATISCHE KEUZE REPRESENTATIEVE PERIODEN
# ==============================================================

def kies_beste_periode(perioden):

    if not perioden:

        return None

    # Grootste SOC-verandering.
    beste = max(
        perioden,
        key=lambda p: abs(
            p["einde"]["soc"] -
            p["start"]["soc"]
        )
    )

    return beste


# ==============================================================
# SAMENVATTING
# ==============================================================

def toon_samenvatting(
    laad_resultaat,
    ontlaad_resultaat
):

    print()
    print("=" * 110)
    print(
        "SAMENVATTING AUTOMATISCH "
        "GEKOZEN PERIODEN"
    )
    print("=" * 110)

    # ----------------------------------------------------------
    # LADEN
    # ----------------------------------------------------------

    if laad_resultaat:

        print()
        print("LAADPERIODE")

        print(
            f"  "
            f"{laad_resultaat['start']['timeStamp']}"
            f" -> "
            f"{laad_resultaat['einde']['timeStamp']}"
        )

        print(
            f"  SOC: "
            f"{laad_resultaat['start']['soc']:.2f}% "
            f"-> "
            f"{laad_resultaat['einde']['soc']:.2f}%"
        )

        if (
            laad_resultaat["capaciteit"]
            is not None
        ):

            print(
                f"  Effectieve capaciteit: "
                f"{laad_resultaat['capaciteit']:.1f} Wh"
            )

        print(
            f"  Lifetime charged : "
            f"{laad_resultaat['lifetime']:.1f} Wh"
        )

        print(
            f"  Power × tijd     : "
            f"{laad_resultaat['power']:.1f} Wh"
        )

        print(
            f"  SOC × capaciteit : "
            f"{laad_resultaat['soc']:.1f} Wh"
        )

        print(
            f"  Primaire methode : "
            f"{laad_resultaat['primaire_methode']}"
        )

    else:

        print()
        print(
            "Geen geschikte laadperiode gevonden."
        )

    # ----------------------------------------------------------
    # ONTLADEN
    # ----------------------------------------------------------

    if ontlaad_resultaat:

        print()
        print("ONTLAADPERIODE")

        print(
            f"  "
            f"{ontlaad_resultaat['start']['timeStamp']}"
            f" -> "
            f"{ontlaad_resultaat['einde']['timeStamp']}"
        )

        print(
            f"  SOC: "
            f"{ontlaad_resultaat['start']['soc']:.2f}% "
            f"-> "
            f"{ontlaad_resultaat['einde']['soc']:.2f}%"
        )

        if (
            ontlaad_resultaat["capaciteit"]
            is not None
        ):

            print(
                f"  Effectieve capaciteit: "
                f"{ontlaad_resultaat['capaciteit']:.1f} Wh"
            )

        print(
            f"  Lifetime discharged : "
            f"{ontlaad_resultaat['lifetime']:.1f} Wh"
        )

        print(
            f"  Power × tijd        : "
            f"{ontlaad_resultaat['power']:.1f} Wh"
        )

        print(
            f"  SOC × capaciteit    : "
            f"{ontlaad_resultaat['soc']:.1f} Wh"
        )

        print(
            f"  Primaire methode    : "
            f"{ontlaad_resultaat['primaire_methode']}"
        )

    else:

        print()
        print(
            "Geen geschikte ontlaadperiode gevonden."
        )


# ==============================================================
# MAIN
# ==============================================================

def main():

    # ----------------------------------------------------------
    # Configuratie
    # ----------------------------------------------------------

    config = laad_configuratie()

    if config is None:

        print()
        print(
            "Configuratie kon niet worden geladen."
        )

        return

    # ----------------------------------------------------------
    # API
    # ----------------------------------------------------------

    data = haal_storage_data(
        config
    )

    if data is None:

        return

    # ----------------------------------------------------------
    # RAW response
    # ----------------------------------------------------------

    print()
    print("=" * 80)
    print("TOP-LEVEL RESPONSE")
    print("=" * 80)

    print(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False
        )
    )

    # ----------------------------------------------------------
    # Batterij
    # ----------------------------------------------------------

    batterij = haal_batterij(
        data
    )

    if batterij is None:

        return

    print()
    print("=" * 80)
    print("BATTERIJ")
    print("=" * 80)

    print(
        f"Naam             : "
        f"{batterij.get('modelNumber')}"
    )

    print(
        f"Serial           : "
        f"{batterij.get('serialNumber')}"
    )

    print(
        f"Nameplate        : "
        f"{batterij.get('nameplate')} Wh"
    )

    print(
        f"Telemetry count  : "
        f"{batterij.get('telemetryCount')}"
    )

    # ----------------------------------------------------------
    # Telemetries
    # ----------------------------------------------------------

    telemetries = normaliseer_telemetries(
        batterij
    )

    if len(telemetries) < 2:

        print()
        print(
            "Te weinig telemetriepunten."
        )

        return

    # ----------------------------------------------------------
    # Perioden detecteren
    # ----------------------------------------------------------

    (
        laadperioden,
        ontlaadperioden
    ) = detecteer_perioden(
        telemetries
    )

    toon_gevonden_perioden(
        laadperioden,
        ontlaadperioden
    )

    # ----------------------------------------------------------
    # Beste laad- en ontlaadperiode
    # ----------------------------------------------------------

    beste_laden = kies_beste_periode(
        laadperioden
    )

    beste_ontladen = kies_beste_periode(
        ontlaadperioden
    )

    # ----------------------------------------------------------
    # Analyse
    # ----------------------------------------------------------

    laad_resultaat = None
    ontlaad_resultaat = None

    if beste_laden:

        laad_resultaat = (
            analyseer_periode_met_telemetries(
                beste_laden,
                telemetries
            )
        )

    if beste_ontladen:

        ontlaad_resultaat = (
            analyseer_periode_met_telemetries(
                beste_ontladen,
                telemetries
            )
        )

    # ----------------------------------------------------------
    # Samenvatting
    # ----------------------------------------------------------

    toon_samenvatting(
        laad_resultaat,
        ontlaad_resultaat
    )

    # ----------------------------------------------------------
    # Einde
    # ----------------------------------------------------------

    print()
    print("=" * 80)
    print("EINDE RAW ANALYSE")
    print("=" * 80)


# ==============================================================
# START
# ==============================================================

if __name__ == "__main__":
    main()
