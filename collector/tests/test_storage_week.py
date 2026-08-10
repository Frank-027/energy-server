# --------------------------------------------------------------
# test_storage_week.py
#
# SolarEdge Storage - dagelijkse audit analyse
#
# Analyseert per dag:
#   - begin- en eindwaarden van relevante SolarEdge velden
#   - verschillen van cumulatieve energietellers
#   - batterij geladen / ontladen in kWh
#   - SOC begin / einde
#   - beschikbare batterijcapaciteit
#
# Versie 1.0 F.Demonie
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


# --------------------------------------------------------------
# PERIODE
# --------------------------------------------------------------

START_DATE = "2026-08-01"
END_DATE = "2026-08-07"

START_TIME = f"{START_DATE} 00:00:00"
END_TIME = f"{END_DATE} 23:59:59"


# --------------------------------------------------------------
# SOLAREDGE API
# --------------------------------------------------------------

URL = (
    f"https://monitoringapi.solaredge.com/site/"
    f"{SITE_ID}/storageData"
)

PARAMS = {
    "api_key": API_KEY,
    "startTime": START_TIME,
    "endTime": END_TIME
}


# --------------------------------------------------------------
# HULPFUNCTIES
# --------------------------------------------------------------

def fmt_getal(value, decimalen=3):
    """Formatteert een getal voor de rapportering."""

    if value is None:
        return "-"

    if isinstance(value, (int, float)):
        return f"{value:,.{decimalen}f}"

    return str(value)


def fmt_wh(value):
    """Formatteert Wh."""

    if value is None:
        return "-"

    return f"{value:,.0f} Wh"


def fmt_kwh(value):
    """Formatteert kWh."""

    if value is None:
        return "-"

    return f"{value:,.3f} kWh"


def parse_timestamp(value):
    """Maakt een datetime van een SolarEdge timestamp."""

    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def get_value(point, field):
    """Veilige uitlezing van een veld."""

    return point.get(field)


# --------------------------------------------------------------
# DATA OPHALEN
# --------------------------------------------------------------

print()
print("=" * 110)
print("SolarEdge DAGELIJKSE STORAGE ANALYSE - AUDIT")
print("=" * 110)
print()
print(f"Periode : {START_TIME} -> {END_TIME}")
print()
print(f"URL: {URL}")
print(f"Periode: {START_TIME} -> {END_TIME}")

try:

    response = requests.get(
        URL,
        params=PARAMS,
        timeout=30
    )

    print(f"HTTP status: {response.status_code}")

    response.raise_for_status()

except requests.RequestException as fout:

    print()
    print("FOUT bij ophalen SolarEdge data:")
    print(fout)
    raise SystemExit(1)


# --------------------------------------------------------------
# JSON VERWERKEN
# --------------------------------------------------------------

try:

    data = response.json()

except ValueError:

    print()
    print("FOUT: SolarEdge antwoord bevat geen geldige JSON.")
    raise SystemExit(1)


storage_data = data.get("storageData")

if not storage_data:

    print()
    print("FOUT: storageData ontbreekt in API-response.")
    raise SystemExit(1)


batteries = storage_data.get("batteries", [])

if not batteries:

    print()
    print("FOUT: geen batterijen gevonden.")
    raise SystemExit(1)


# --------------------------------------------------------------
# EERSTE BATTERIJ
# --------------------------------------------------------------

battery = batteries[0]

name = battery.get("name")
serial = battery.get("serialNumber")
nameplate = battery.get("nameplate")
model = battery.get("modelNumber")

telemetries = battery.get("telemetries", [])

if not telemetries:

    print()
    print("FOUT: telemetrie niet gevonden.")
    print()
    print("Structuur van batterij:")
    for key, value in battery.items():

        if isinstance(value, list):
            print(f"  {key}: LIST ({len(value)} elementen)")
        else:
            print(f"  {key}: {value}")

    raise SystemExit(1)


# --------------------------------------------------------------
# EERSTE TELEMETRIEPUNT
# --------------------------------------------------------------

eerste = telemetries[0]

print()
print("=" * 110)
print("EERSTE TELEMETRIEPUNT")
print("=" * 110)

for veld in [
    "timeStamp",
    "power",
    "batteryState",
    "lifeTimeEnergyDischarged",
    "lifeTimeEnergyCharged",
    "batteryPercentageState",
    "fullPackEnergyAvailable",
    "internalTemp",
    "ACGridCharging"
]:

    print(
        f"{veld:<35}: "
        f"{eerste.get(veld)}"
    )

print("=" * 110)


# --------------------------------------------------------------
# BATTERIJ
# --------------------------------------------------------------

print()
print("=" * 110)
print("BATTERIJ")
print("=" * 110)

print(f"Naam              : {name}")
print(f"Model             : {model}")
print(f"Serial            : {serial}")
print(f"Nameplate         : {nameplate:,.3f} Wh")
print(f"Telemetry count   : {len(telemetries)}")


# --------------------------------------------------------------
# TELEMETRIE PER DAG GROEPEREN
# --------------------------------------------------------------

dagen = {}

for point in telemetries:

    timestamp = parse_timestamp(
        point.get("timeStamp")
    )

    if timestamp is None:
        continue

    datum = timestamp.date()

    if datum not in dagen:
        dagen[datum] = []

    dagen[datum].append(point)


print()
print("=" * 110)
print(f"DAGEN GEVONDEN: {len(dagen)}")
print("=" * 110)


# --------------------------------------------------------------
# RELEVANTE VELDEN
# --------------------------------------------------------------

velden = [
    "batteryPercentageState",
    "batteryState",
    "fullPackEnergyAvailable",
    "internalTemp",
    "lifeTimeEnergyCharged",
    "lifeTimeEnergyDischarged",
    "power",
    "ACGridCharging"
]


# --------------------------------------------------------------
# RESULTATEN VOOR SAMENVATTING
# --------------------------------------------------------------

dagresultaten = []


# --------------------------------------------------------------
# DAGANALYSE
# --------------------------------------------------------------

for datum in sorted(dagen.keys()):

    punten = sorted(
        dagen[datum],
        key=lambda p: p.get("timeStamp", "")
    )

    if not punten:
        continue

    begin = punten[0]
    einde = punten[-1]

    begin_time = parse_timestamp(
        begin.get("timeStamp")
    )

    einde_time = parse_timestamp(
        einde.get("timeStamp")
    )

    print()
    print("=" * 110)
    print(f"DAGANALYSE {datum}")
    print("=" * 110)

    print()
    print(f"Telemetriepunten : {len(punten)}")
    print(
        f"Eerste punt      : "
        f"{begin.get('timeStamp')}"
    )
    print(
        f"Laatste punt      : "
        f"{einde.get('timeStamp')}"
    )
    print(
        f"Nameplate         : "
        f"{nameplate:,.3f} Wh"
    )

    # ----------------------------------------------------------
    # BEGIN / EINDE TABEL
    # ----------------------------------------------------------

    print()
    print("-" * 110)
    print("BEGIN- EN EINDWAARDEN SOLAREDGE-VELDEN")
    print("-" * 110)

    print(
        f"{'Veld':<35}"
        f"{'Begin':>20}"
        f"{'Einde':>20}"
        f"{'Verschil':>20}"
    )

    print("-" * 110)

    verschillen = {}

    for veld in velden:

        beginwaarde = get_value(begin, veld)
        eindwaarde = get_value(einde, veld)

        verschil = None

        if (
            isinstance(beginwaarde, (int, float))
            and isinstance(eindwaarde, (int, float))
        ):
            verschil = eindwaarde - beginwaarde

        verschillen[veld] = verschil

        print(
            f"{veld:<35}"
            f"{fmt_getal(beginwaarde):>20}"
            f"{fmt_getal(eindwaarde):>20}"
            f"{fmt_getal(verschil):>20}"
        )

    # ----------------------------------------------------------
    # ENERGIEANALYSE
    # ----------------------------------------------------------

    charged_begin = get_value(
        begin,
        "lifeTimeEnergyCharged"
    )

    charged_end = get_value(
        einde,
        "lifeTimeEnergyCharged"
    )

    discharged_begin = get_value(
        begin,
        "lifeTimeEnergyDischarged"
    )

    discharged_end = get_value(
        einde,
        "lifeTimeEnergyDischarged"
    )

    charged_delta = None
    discharged_delta = None

    if (
        isinstance(charged_begin, (int, float))
        and isinstance(charged_end, (int, float))
    ):
        charged_delta = charged_end - charged_begin

    if (
        isinstance(discharged_begin, (int, float))
        and isinstance(discharged_end, (int, float))
    ):
        discharged_delta = (
            discharged_end - discharged_begin
        )

    charged_kwh = (
        charged_delta / 1000
        if charged_delta is not None
        else None
    )

    discharged_kwh = (
        discharged_delta / 1000
        if discharged_delta is not None
        else None
    )

    print()
    print("-" * 110)
    print("ENERGIEANALYSE")
    print("-" * 110)

    print()
    print("BATTERIJ GELADEN")
    print(
        f"  Lifetime begin : "
        f"{fmt_wh(charged_begin)}"
    )
    print(
        f"  Lifetime einde : "
        f"{fmt_wh(charged_end)}"
    )
    print(
        f"  Verschil       : "
        f"{fmt_wh(charged_delta)}"
    )
    print(
        f"  Dagwaarde      : "
        f"{fmt_kwh(charged_kwh)}"
    )

    print()
    print("BATTERIJ ONTLADEN")
    print(
        f"  Lifetime begin : "
        f"{fmt_wh(discharged_begin)}"
    )
    print(
        f"  Lifetime einde : "
        f"{fmt_wh(discharged_end)}"
    )
    print(
        f"  Verschil       : "
        f"{fmt_wh(discharged_delta)}"
    )
    print(
        f"  Dagwaarde      : "
        f"{fmt_kwh(discharged_kwh)}"
    )

    # ----------------------------------------------------------
    # SOC
    # ----------------------------------------------------------

    soc_begin = get_value(
        begin,
        "batteryPercentageState"
    )

    soc_end = get_value(
        einde,
        "batteryPercentageState"
    )

    capaciteit_begin = get_value(
        begin,
        "fullPackEnergyAvailable"
    )

    capaciteit_end = get_value(
        einde,
        "fullPackEnergyAvailable"
    )

    print()
    print("BATTERIJSTATUS")

    print(
        f"  SOC begin      : "
        f"{fmt_getal(soc_begin)} %"
    )

    print(
        f"  SOC einde      : "
        f"{fmt_getal(soc_end)} %"
    )

    if (
        isinstance(soc_begin, (int, float))
        and isinstance(soc_end, (int, float))
    ):

        print(
            f"  SOC verschil   : "
            f"{soc_end - soc_begin:,.3f} procentpunt"
        )

    print()
    print(
        f"  Capaciteit begin : "
        f"{fmt_kwh(capaciteit_begin / 1000 if capaciteit_begin is not None else None)}"
    )

    print(
        f"  Capaciteit einde : "
        f"{fmt_kwh(capaciteit_end / 1000 if capaciteit_end is not None else None)}"
    )

    # ----------------------------------------------------------
    # POWER
    # ----------------------------------------------------------

    power_begin = get_value(
        begin,
        "power"
    )

    power_end = get_value(
        einde,
        "power"
    )

    print()
    print("POWER-VELD")

    print(
        f"  Begin : "
        f"{fmt_getal(power_begin)} W"
    )

    print(
        f"  Einde : "
        f"{fmt_getal(power_end)} W"
    )

    # ----------------------------------------------------------
    # DAGRESULTAAT OPSLAAN
    # ----------------------------------------------------------

    dagresultaten.append({
        "datum": datum,
        "punten": len(punten),
        "begin": begin,
        "einde": einde,
        "charged_begin": charged_begin,
        "charged_end": charged_end,
        "charged_kwh": charged_kwh,
        "discharged_begin": discharged_begin,
        "discharged_end": discharged_end,
        "discharged_kwh": discharged_kwh,
        "soc_begin": soc_begin,
        "soc_end": soc_end,
        "capacity_begin": capaciteit_begin,
        "capacity_end": capaciteit_end
    })


# --------------------------------------------------------------
# SAMENVATTING
# --------------------------------------------------------------

print()
print()
print("=" * 110)
print("SAMENVATTING PER DAG")
print("=" * 110)

print()

print(
    f"{'Datum':<12}"
    f"{'Punten':>8}"
    f"{'Charged':>13}"
    f"{'Discharged':>14}"
    f"{'SOC begin':>12}"
    f"{'SOC einde':>12}"
)

print("-" * 110)

for resultaat in dagresultaten:

    print(
        f"{str(resultaat['datum']):<12}"
        f"{resultaat['punten']:>8}"
        f"{fmt_kwh(resultaat['charged_kwh']):>13}"
        f"{fmt_kwh(resultaat['discharged_kwh']):>14}"
        f"{fmt_getal(resultaat['soc_begin'], 2):>12}%"
        f"{fmt_getal(resultaat['soc_end'], 2):>12}%"
    )


# --------------------------------------------------------------
# TOTAAL
# --------------------------------------------------------------

totaal_charged = sum(
    r["charged_kwh"]
    for r in dagresultaten
    if r["charged_kwh"] is not None
)

totaal_discharged = sum(
    r["discharged_kwh"]
    for r in dagresultaten
    if r["discharged_kwh"] is not None
)


print()
print("-" * 110)
print("TOTALEN")
print("-" * 110)

print(
    f"Totaal batterij geladen   : "
    f"{totaal_charged:,.3f} kWh"
)

print(
    f"Totaal batterij ontladen : "
    f"{totaal_discharged:,.3f} kWh"
)


# --------------------------------------------------------------
# CONTROLE OVER VOLLEDIGE PERIODE
# --------------------------------------------------------------

if dagresultaten:

    eerste_dag = dagresultaten[0]
    laatste_dag = dagresultaten[-1]

    periode_charged = (
        laatste_dag["charged_end"]
        - eerste_dag["charged_begin"]
    )

    periode_discharged = (
        laatste_dag["discharged_end"]
        - eerste_dag["discharged_begin"]
    )

    print()
    print("-" * 110)
    print("CONTROLE VOLLEDIGE PERIODE")
    print("-" * 110)

    print()
    print("LifetimeEnergyCharged")

    print(
        f"  Begin : "
        f"{fmt_wh(eerste_dag['charged_begin'])}"
    )

    print(
        f"  Einde : "
        f"{fmt_wh(laatste_dag['charged_end'])}"
    )

    print(
        f"  Verschil : "
        f"{fmt_wh(periode_charged)}"
    )

    print(
        f"  = "
        f"{fmt_kwh(periode_charged / 1000)}"
    )

    print()
    print("LifetimeEnergyDischarged")

    print(
        f"  Begin : "
        f"{fmt_wh(eerste_dag['discharged_begin'])}"
    )

    print(
        f"  Einde : "
        f"{fmt_wh(laatste_dag['discharged_end'])}"
    )

    print(
        f"  Verschil : "
        f"{fmt_wh(periode_discharged)}"
    )

    print(
        f"  = "
        f"{fmt_kwh(periode_discharged / 1000)}"
    )


# --------------------------------------------------------------
# EINDE
# --------------------------------------------------------------

print()
print("=" * 110)
print("EINDE DAGELIJKSE STORAGE AUDIT")
print("=" * 110)
print()