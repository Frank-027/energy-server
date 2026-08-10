# --------------------------------------------------------------
# reports.py
#
# Rapportages en analyses van Energy Server data
# --------------------------------------------------------------

# ==============================================================
# ENERGIE - DAG
# ==============================================================

def energie_dag(verbinding, datum):

    sql = """
        SELECT
            COUNT(*) AS datapunten,
            MIN(timestamp) AS eerste_meting,
            MAX(timestamp) AS laatste_meting,

            SUM(production_w) / 4 / 1000 AS production_kwh,
            SUM(consumption_w) / 4 / 1000 AS consumption_kwh,
            SUM(feed_in_w) / 4 / 1000 AS feed_in_kwh,
            SUM(purchased_w) / 4 / 1000 AS purchased_kwh,
            SUM(self_consumption_w) / 4 / 1000 AS self_consumption_kwh

        FROM energy_power
        WHERE DATE(timestamp) = %s
    """

    cursor = verbinding.cursor(dictionary=True)
    cursor.execute(sql, (datum,))
    resultaat = cursor.fetchone()
    cursor.close()

    return resultaat

# ==============================================================
# ENERGIE - PERIODE
# ==============================================================

def energie_periode(verbinding, start_datum, eind_datum):

    sql = """
        SELECT
            COUNT(*) AS datapunten,

            MIN(timestamp) AS eerste_meting,
            MAX(timestamp) AS laatste_meting,

            COUNT(DISTINCT DATE(timestamp)) AS beschikbare_dagen,

            SUM(production_w) / 4 / 1000 AS production_kwh,
            SUM(consumption_w) / 4 / 1000 AS consumption_kwh,
            SUM(feed_in_w) / 4 / 1000 AS feed_in_kwh,
            SUM(purchased_w) / 4 / 1000 AS purchased_kwh,
            SUM(self_consumption_w) / 4 / 1000 AS self_consumption_kwh

        FROM energy_power
        WHERE DATE(timestamp) BETWEEN %s AND %s
    """

    cursor = verbinding.cursor(dictionary=True)
    cursor.execute(sql, (start_datum, eind_datum))
    resultaat = cursor.fetchone()
    cursor.close()

    return resultaat

# ==============================================================
# ENERGIE - PER DAG BINNEN PERIODE
# ==============================================================

def energie_per_dag(verbinding, start_datum, eind_datum):

    sql = """
        SELECT
            DATE(timestamp) AS datum,
            COUNT(*) AS datapunten,
            MIN(timestamp) AS eerste_meting,
            MAX(timestamp) AS laatste_meting,

            SUM(production_w) / 4 / 1000 AS production_kwh,
            SUM(consumption_w) / 4 / 1000 AS consumption_kwh,
            SUM(feed_in_w) / 4 / 1000 AS feed_in_kwh,
            SUM(purchased_w) / 4 / 1000 AS purchased_kwh,
            SUM(self_consumption_w) / 4 / 1000 AS self_consumption_kwh

        FROM energy_power

        WHERE DATE(timestamp) BETWEEN %s AND %s

        GROUP BY DATE(timestamp)

        ORDER BY datum
    """

    cursor = verbinding.cursor(dictionary=True)

    cursor.execute(
        sql,
        (start_datum, eind_datum)
    )

    resultaten = cursor.fetchall()

    cursor.close()

    return resultaten

# ==============================================================
# BATTERIJ - DAG
# ==============================================================

def batterij_dag(verbinding, datum):

    sql = """
        SELECT
            timestamp,
            lifetime_energy_charged_wh,
            lifetime_energy_discharged_wh,
            battery_percentage,
            full_pack_energy_available_wh,
            power_w

        FROM energy_battery

        WHERE DATE(timestamp) = %s

        ORDER BY timestamp
    """

    cursor = verbinding.cursor(dictionary=True)
    cursor.execute(sql, (datum,))
    rijen = cursor.fetchall()
    cursor.close()

    if not rijen:
        return None

    begin = rijen[0]
    einde = rijen[-1]

    # ----------------------------------------------------------
    # Eerste en laatste geldige SOC-waarde
    #
    # 0% is een geldige SOC en mag dus NIET worden weggefilterd.
    # Alleen NULL wordt als onbekend beschouwd.
    # ----------------------------------------------------------
    soc_rijen = [
        rij for rij in rijen
        if rij["battery_percentage"] is not None
    ]

    if soc_rijen:
        soc_begin = soc_rijen[0]["battery_percentage"]
        soc_einde = soc_rijen[-1]["battery_percentage"]
        soc_begin_timestamp = soc_rijen[0]["timestamp"]
        soc_einde_timestamp = soc_rijen[-1]["timestamp"]
    else:
        soc_begin = None
        soc_einde = None
        soc_begin_timestamp = None
        soc_einde_timestamp = None

    # ----------------------------------------------------------
    # Batterij-energie volgens SOC
    #
    # battery_percentage is uitgedrukt als percentage
    # (bv. 72.313 betekent 72.313%)
    #
    # full_pack_energy_available_wh is de beschikbare
    # batterijcapaciteit op dat moment.
    # ----------------------------------------------------------

    energie_opgeslagen_begin_kwh = None
    energie_opgeslagen_einde_kwh = None
    energie_opgeslagen_verschil_kwh = None

    if (
        soc_begin is not None
        and begin["full_pack_energy_available_wh"] is not None
    ):
        energie_opgeslagen_begin_kwh = (
            soc_begin / 100
            * begin["full_pack_energy_available_wh"]
            / 1000
        )

    if (
        soc_einde is not None
        and einde["full_pack_energy_available_wh"] is not None
    ):
        energie_opgeslagen_einde_kwh = (
            soc_einde / 100
            * einde["full_pack_energy_available_wh"]
            / 1000
        )

    if (
        energie_opgeslagen_begin_kwh is not None
        and energie_opgeslagen_einde_kwh is not None
    ):
        energie_opgeslagen_verschil_kwh = (
            energie_opgeslagen_einde_kwh
            - energie_opgeslagen_begin_kwh
        )

    return {
        # Lifetime tellers
        "charged_kwh": (
            float(einde["lifetime_energy_charged_wh"])
            - float(begin["lifetime_energy_charged_wh"])
        ) / 1000,

        "discharged_kwh": (
            float(einde["lifetime_energy_discharged_wh"])
            - float(begin["lifetime_energy_discharged_wh"])
        ) / 1000,

        # State of Charge
        "soc_begin": soc_begin,
        "soc_einde": soc_einde,

        "soc_begin_timestamp": soc_begin_timestamp,
        "soc_einde_timestamp": soc_einde_timestamp,

        # Beschikbare batterijcapaciteit
        "capaciteit_begin_kwh": (
            begin["full_pack_energy_available_wh"] / 1000
            if begin["full_pack_energy_available_wh"] is not None
            else None
        ),

        "capaciteit_einde_kwh": (
            einde["full_pack_energy_available_wh"] / 1000
            if einde["full_pack_energy_available_wh"] is not None
            else None
        ),

        # ------------------------------------------------------
        # Energie volgens SOC
        # ------------------------------------------------------

        "energie_opgeslagen_begin_kwh":
            energie_opgeslagen_begin_kwh,

        "energie_opgeslagen_einde_kwh":
            energie_opgeslagen_einde_kwh,

        "energie_opgeslagen_verschil_kwh":
            energie_opgeslagen_verschil_kwh,

        "netto_charged_kwh": (
            (
                einde["lifetime_energy_charged_wh"]
                - begin["lifetime_energy_charged_wh"]
            )
            -
            (
                einde["lifetime_energy_discharged_wh"]
                - begin["lifetime_energy_discharged_wh"]
            )
        ) / 1000,

        # Batterijvermogen
        "power_begin": begin["power_w"],
        "power_einde": einde["power_w"],

        # Metadata
        "eerste_meting": begin["timestamp"],
        "laatste_meting": einde["timestamp"],

        "datapunten": len(rijen)
    }

# ==============================================================
# BATTERIJ - PERIODE
# ==============================================================

def batterij_periode(verbinding, start_datum, eind_datum):

    sql = """
        SELECT
            timestamp,
            lifetime_energy_charged_wh,
            lifetime_energy_discharged_wh,
            battery_percentage,
            full_pack_energy_available_wh,
            power_w
        FROM energy_battery
        WHERE DATE(timestamp) BETWEEN %s AND %s
        ORDER BY timestamp
    """

    cursor = verbinding.cursor(dictionary=True)
    cursor.execute(sql, (start_datum, eind_datum))
    rijen = cursor.fetchall()
    cursor.close()

    if not rijen:
        return None

    eerste = rijen[0]
    laatste = rijen[-1]

    # ----------------------------------------------------------
    # Eerste en laatste geldige SOC-waarde
    #
    # 0% is een geldige waarde.
    # Alleen NULL wordt als onbekend beschouwd.
    # ----------------------------------------------------------

    geldige_soc_rijen = [
        rij for rij in rijen
        if rij["battery_percentage"] is not None
    ]

    if geldige_soc_rijen:
        eerste_soc = geldige_soc_rijen[0]
        laatste_soc = geldige_soc_rijen[-1]
    else:
        eerste_soc = None
        laatste_soc = None

    # ----------------------------------------------------------
    # Beschikbare dagen
    # ----------------------------------------------------------

    beschikbare_dagen = len(set(
        rij["timestamp"].date()
        for rij in rijen
    ))

    # ----------------------------------------------------------
    # Resultaat
    # ----------------------------------------------------------

    return {
        # Lifetime tellers
        "charged_kwh": (
            laatste["lifetime_energy_charged_wh"]
            - eerste["lifetime_energy_charged_wh"]
        ) / 1000,

        "discharged_kwh": (
            laatste["lifetime_energy_discharged_wh"]
            - eerste["lifetime_energy_discharged_wh"]
        ) / 1000,

        # State of Charge
        "soc_begin": (
            eerste_soc["battery_percentage"]
            if eerste_soc is not None
            else None
        ),

        "soc_einde": (
            laatste_soc["battery_percentage"]
            if laatste_soc is not None
            else None
        ),

        "soc_begin_timestamp": (
            eerste_soc["timestamp"]
            if eerste_soc is not None
            else None
        ),

        "soc_einde_timestamp": (
            laatste_soc["timestamp"]
            if laatste_soc is not None
            else None
        ),

        "soc_begin_bekend": eerste_soc is not None,

        # Beschikbare batterijcapaciteit
        "capaciteit_begin_kwh": (
            eerste["full_pack_energy_available_wh"] / 1000
            if eerste["full_pack_energy_available_wh"] is not None
            else None
        ),

        "capaciteit_einde_kwh": (
            laatste["full_pack_energy_available_wh"] / 1000
            if laatste["full_pack_energy_available_wh"] is not None
            else None
        ),

        # Batterijvermogen
        "power_begin":
            eerste["power_w"],

        "power_einde":
            laatste["power_w"],

        # Metadata
        "datapunten":
            len(rijen),

        "beschikbare_dagen":
            beschikbare_dagen,

        "eerste_meting":
            eerste["timestamp"],

        "laatste_meting":
            laatste["timestamp"]
    }

# ==============================================================
# BATTERIJ - PER DAG BINNEN PERIODE
# ==============================================================

def batterij_per_dag(verbinding, start_datum, eind_datum):

    sql = """
        SELECT
            DATE(timestamp) AS datum,
            COUNT(*) AS datapunten,
            MIN(timestamp) AS eerste_meting,
            MAX(timestamp) AS laatste_meting
        FROM energy_battery
        WHERE DATE(timestamp) BETWEEN %s AND %s
        GROUP BY DATE(timestamp)
        ORDER BY datum
    """

    cursor = verbinding.cursor(dictionary=True)

    cursor.execute(
        sql,
        (start_datum, eind_datum)
    )

    dagen = cursor.fetchall()

    cursor.close()

    resultaten = []

    for dag in dagen:

        # ------------------------------------------------------
        # Alle batterijmetingen van deze dag ophalen
        #
        # Dit laat ons toe om:
        # - lifetime counters van begin/einde te bepalen
        # - eerste geldige SOC te zoeken
        # - laatste geldige SOC te zoeken
        # ------------------------------------------------------

        sql_metingen = """
            SELECT
                timestamp,
                lifetime_energy_charged_wh,
                lifetime_energy_discharged_wh,
                battery_percentage
            FROM energy_battery
            WHERE DATE(timestamp) = %s
            ORDER BY timestamp
        """

        cursor = verbinding.cursor(dictionary=True)

        cursor.execute(
            sql_metingen,
            (dag["datum"],)
        )

        metingen = cursor.fetchall()

        cursor.close()

        if not metingen:
            continue

        # ------------------------------------------------------
        # Eerste en laatste meting
        #
        # De lifetime tellers gebruiken we voor de eerste
        # en laatste meting van de dag.
        # ------------------------------------------------------

        begin = metingen[0]
        einde = metingen[-1]

        # ------------------------------------------------------
        # Eerste en laatste geldige SOC
        #
        # 0% is geldig.
        # Alleen NULL betekent onbekend.
        # ------------------------------------------------------

        soc_meting_begin = None
        soc_meting_einde = None

        for meting in metingen:

            if meting["battery_percentage"] is not None:

                if soc_meting_begin is None:
                    soc_meting_begin = meting

                soc_meting_einde = meting

        # ------------------------------------------------------
        # Resultaat
        # ------------------------------------------------------

        resultaten.append({

            "datum":
                dag["datum"],

            "datapunten":
                dag["datapunten"],

            # --------------------------------------------------
            # Lifetime tellers
            # --------------------------------------------------

            "charged_kwh": (
                einde["lifetime_energy_charged_wh"]
                - begin["lifetime_energy_charged_wh"]
            ) / 1000,

            "discharged_kwh": (
                einde["lifetime_energy_discharged_wh"]
                - begin["lifetime_energy_discharged_wh"]
            ) / 1000,

            # --------------------------------------------------
            # SOC
            # --------------------------------------------------

            "soc_begin": (
                soc_meting_begin["battery_percentage"]
                if soc_meting_begin is not None
                else None
            ),

            "soc_einde": (
                soc_meting_einde["battery_percentage"]
                if soc_meting_einde is not None
                else None
            ),

            # --------------------------------------------------
            # SOC timestamps
            # --------------------------------------------------

            "soc_begin_timestamp": (
                soc_meting_begin["timestamp"]
                if soc_meting_begin is not None
                else None
            ),

            "soc_einde_timestamp": (
                soc_meting_einde["timestamp"]
                if soc_meting_einde is not None
                else None
            )
        })

    return resultaten

# ==============================================================
# DAGRAPPORT
# ==============================================================

def toon_dagrapport(verbinding, datum):

    energie = energie_dag(verbinding, datum)
    batterij = batterij_dag(verbinding, datum)

    print()
    print("=" * 60)
    print(f"DAGRAPPORT {datum}")
    print("=" * 60)

    # ----------------------------------------------------------
    # ENERGIE
    # ----------------------------------------------------------

    print()
    print("ENERGIE")
    print("-" * 60)

    if energie["datapunten"] == 0:

        print("Geen energiegegevens gevonden.")

    else:

        print(
            f"Productie        : "
            f"{energie['production_kwh']:9.2f} kWh"
        )

        print(
            f"Verbruik         : "
            f"{energie['consumption_kwh']:9.2f} kWh"
        )

        print(
            f"Zelfconsumptie   : "
            f"{energie['self_consumption_kwh']:9.2f} kWh"
        )

        print(
            f"Injectie         : "
            f"{energie['feed_in_kwh']:9.2f} kWh"
        )

        print(
            f"Afname net       : "
            f"{energie['purchased_kwh']:9.2f} kWh"
        )

        print()
        print(
            f"Datapunten       : "
            f"{energie['datapunten']}"
        )

        print(
            f"Eerste meting    : "
            f"{energie['eerste_meting']}"
        )

        print(
            f"Laatste meting   : "
            f"{energie['laatste_meting']}"
        )

        # ------------------------------------------------------
        # ENERGIEBALANS
        # ------------------------------------------------------

        balans_productie = (
            energie["production_kwh"]
            - energie["self_consumption_kwh"]
            - energie["feed_in_kwh"]
        )

        balans_verbruik = (
            energie["consumption_kwh"]
            - energie["self_consumption_kwh"]
            - energie["purchased_kwh"]
        )

        print()
        print("ENERGIEBALANS")
        print("-" * 60)

        print(
            f"Productie - zelfconsumptie - injectie : "
            f"{balans_productie:9.3f} kWh"
        )

        print(
            f"Verbruik - zelfconsumptie - afname     : "
            f"{balans_verbruik:9.3f} kWh"
        )

    # ----------------------------------------------------------
    # BATTERIJ
    # ----------------------------------------------------------

    print()
    print("BATTERIJ")
    print("-" * 60)

    if batterij is None:

        print("Geen batterijgegevens gevonden.")

    else:

        print(
            f"Charged          : "
            f"{batterij['charged_kwh']:9.3f} kWh"
        )

        print(
            f"Discharged       : "
            f"{batterij['discharged_kwh']:9.3f} kWh"
        )

        print(
            f"Netto charged    : "
            f"{batterij['netto_charged_kwh']:9.3f} kWh"
        )

        # ------------------------------------------------------
        # STATE OF CHARGE
        # ------------------------------------------------------

        print()

        if batterij["soc_begin"] is not None:

            print(
                f"SOC begin        : "
                f"{batterij['soc_begin']:9.3f} %"
            )

            print(
                f"  meting         : "
                f"{batterij['soc_begin_timestamp']}"
            )

        else:

            print(
                f"SOC begin        : "
                f"{'onbekend':>9}"
            )

        if batterij["soc_einde"] is not None:

            print(
                f"SOC einde        : "
                f"{batterij['soc_einde']:9.3f} %"
            )

            print(
                f"  meting         : "
                f"{batterij['soc_einde_timestamp']}"
            )

        else:

            print(
                f"SOC einde        : "
                f"{'onbekend':>9}"
            )

        if (
            batterij["soc_begin"] is not None
            and batterij["soc_einde"] is not None
        ):

            soc_verschil = (
                batterij["soc_einde"]
                - batterij["soc_begin"]
            )

            print(
                f"SOC verschil     : "
                f"{soc_verschil:9.3f} procentpunt"
            )

        # ------------------------------------------------------
        # BATTERIJCAPACITEIT
        # ------------------------------------------------------

        print()

        if batterij["capaciteit_begin_kwh"] is not None:

            print(
                f"Capaciteit begin  : "
                f"{batterij['capaciteit_begin_kwh']:9.3f} kWh"
            )

        else:

            print(
                f"Capaciteit begin  : "
                f"{'onbekend':>9}"
            )

        if batterij["capaciteit_einde_kwh"] is not None:

            print(
                f"Capaciteit einde  : "
                f"{batterij['capaciteit_einde_kwh']:9.3f} kWh"
            )

        else:

            print(
                f"Capaciteit einde  : "
                f"{'onbekend':>9}"
            )

        # ------------------------------------------------------
        # ENERGIE-INHOUD VOLGENS SOC
        # ------------------------------------------------------

        if batterij["energie_opgeslagen_begin_kwh"] is not None:

            print()
            print(
                f"Energie opgeslagen begin : "
                f"{batterij['energie_opgeslagen_begin_kwh']:9.3f} kWh"
            )

            print(
                f"Energie opgeslagen einde : "
                f"{batterij['energie_opgeslagen_einde_kwh']:9.3f} kWh"
            )

            print(
                f"Netto opslag volgens SOC : "
                f"{batterij['energie_opgeslagen_verschil_kwh']:9.3f} kWh"
            )

            verschil = (
                float(batterij["netto_charged_kwh"])
                - float(batterij["energie_opgeslagen_verschil_kwh"])
            )

            print(
                f"Niet verklaard verschil   : "
                f"{verschil:9.3f} kWh"
            )

        # ------------------------------------------------------
        # BATTERIJVERMOGEN
        # ------------------------------------------------------

        print()

        if batterij["power_begin"] is not None:

            print(
                f"Power begin      : "
                f"{batterij['power_begin']:9.3f} W"
            )

        if batterij["power_einde"] is not None:

            print(
                f"Power einde      : "
                f"{batterij['power_einde']:9.3f} W"
            )

        # ------------------------------------------------------
        # METADATA
        # ------------------------------------------------------

        print()

        print(
            f"Datapunten       : "
            f"{batterij['datapunten']}"
        )

        print(
            f"Eerste meting    : "
            f"{batterij['eerste_meting']}"
        )

        print(
            f"Laatste meting   : "
            f"{batterij['laatste_meting']}"
        )

# ==============================================================
# WEEKRAPPORT
# ==============================================================

def toon_weekrapport(verbinding, start_datum, eind_datum):

    energie = energie_periode(
        verbinding,
        start_datum,
        eind_datum
    )

    energie_dagen = energie_per_dag(
        verbinding,
        start_datum,
        eind_datum
    )

    batterij_dagen = batterij_per_dag(
        verbinding,
        start_datum,
        eind_datum
    )

    batterij = batterij_periode(
        verbinding,
        start_datum,
        eind_datum
    )

    print()
    print("=" * 70)
    print("WEEKRAPPORT")
    print("=" * 70)

    print()
    print(f"Periode gevraagd : {start_datum} -> {eind_datum}")

    # ----------------------------------------------------------
    # DAGOVERZICHT
    # ----------------------------------------------------------

    print()
    print("DAGOVERZICHT")
    print("-" * 70)

    print(
        f"{'Datum':<12}"
        f"{'Prod.':>10}"
        f"{'Verbruik':>11}"
        f"{'Zelfcons.':>11}"
        f"{'Injectie':>11}"
        f"{'Afname':>10}"
    )

    print("-" * 70)

    for dag in energie_dagen:

        print(
            f"{str(dag['datum']):<12}"
            f"{dag['production_kwh']:>10.2f}"
            f"{dag['consumption_kwh']:>11.2f}"
            f"{dag['self_consumption_kwh']:>11.2f}"
            f"{dag['feed_in_kwh']:>11.2f}"
            f"{dag['purchased_kwh']:>10.2f}"
        )

    print("-" * 70)

    print()
    print("BATTERIJ PER DAG")
    print("-" * 70)

    print(
        f"{'Datum':<12}"
        f"{'Charged':>11}"
        f"{'Discharged':>13}"
        f"{'SOC begin':>12}"
        f"{'SOC einde':>12}"
    )

    print("-" * 70)

    for dag in batterij_dagen:

        print(
            f"{str(dag['datum']):<12}"
            f"{dag['charged_kwh']:>11.3f}"
            f"{dag['discharged_kwh']:>13.3f}"
            f"{dag['soc_begin']:>11.3f}%"
            f"{dag['soc_einde']:>11.3f}%"
        )

    print("-" * 70)

    # ----------------------------------------------------------
    # ENERGIE
    # ----------------------------------------------------------

    print()
    print("ENERGIE")
    print("-" * 70)

    if energie["datapunten"] == 0:

        print("Geen energiedata beschikbaar.")

    else:

        print(
            f"Beschikbare dagen : "
            f"{energie['beschikbare_dagen']}"
        )

        print(
            f"Datapunten        : "
            f"{energie['datapunten']}"
        )

        print(
            f"Eerste meting     : "
            f"{energie['eerste_meting']}"
        )

        print(
            f"Laatste meting    : "
            f"{energie['laatste_meting']}"
        )

        print()

        print(
            f"Productie         : "
            f"{energie['production_kwh']:11.2f} kWh"
        )

        print(
            f"Verbruik          : "
            f"{energie['consumption_kwh']:11.2f} kWh"
        )

        print(
            f"Zelfconsumptie    : "
            f"{energie['self_consumption_kwh']:11.2f} kWh"
        )

        print(
            f"Injectie          : "
            f"{energie['feed_in_kwh']:11.2f} kWh"
        )

        print(
            f"Afname net        : "
            f"{energie['purchased_kwh']:11.2f} kWh"
        )

        balans_productie = (
            energie["production_kwh"]
            - energie["self_consumption_kwh"]
            - energie["feed_in_kwh"]
        )

        balans_verbruik = (
            energie["consumption_kwh"]
            - energie["self_consumption_kwh"]
            - energie["purchased_kwh"]
        )

        print()
        print("ENERGIEBALANS")
        print("-" * 70)

        print(
            f"Productie - zelfconsumptie - injectie : "
            f"{balans_productie:11.3f} kWh"
        )

        print(
            f"Verbruik - zelfconsumptie - afname     : "
            f"{balans_verbruik:11.3f} kWh"
        )

    # ----------------------------------------------------------
    # BATTERIJ
    # ----------------------------------------------------------

    print()
    print("BATTERIJ")
    print("-" * 70)

    if batterij is None:

        print("Geen batterijdata beschikbaar.")

    else:

        print(
            f"Beschikbare dagen : "
            f"{batterij['beschikbare_dagen']}"
        )

        print(
            f"Datapunten        : "
            f"{batterij['datapunten']}"
        )

        print(
            f"Eerste meting     : "
            f"{batterij['eerste_meting']}"
        )

        print(
            f"Laatste meting    : "
            f"{batterij['laatste_meting']}"
        )

        print()

        print(
            f"Charged           : "
            f"{batterij['charged_kwh']:11.3f} kWh"
        )

        print(
            f"Discharged        : "
            f"{batterij['discharged_kwh']:11.3f} kWh"
        )

        print()

        if batterij["soc_begin_bekend"]:

            print(
                f"SOC begin         : "
                f"{batterij['soc_begin']:11.3f} %"
            )

            print(
                f"  meting           : "
                f"{batterij['soc_begin_timestamp']}"
            )

        else:

            print(
                f"SOC begin         : {'onbekend':>11}"
            )

            print(
                f"  eerste meting    : "
                f"{batterij['soc_begin_timestamp']}"
            )

        print(
            f"SOC einde         : {batterij['soc_einde']:11.3f} %"
        )

        print(
            f"  meting           : {batterij['soc_einde_timestamp']}"
        )

        print()

        print(
            f"Capaciteit begin  : "
            f"{batterij['capaciteit_begin_kwh']:11.3f} kWh"
        )

        print(
            f"Capaciteit einde  : "
            f"{batterij['capaciteit_einde_kwh']:11.3f} kWh"
        )

        print()

        print(
            f"Power begin       : "
            f"{batterij['power_begin']:11.3f} W"
        )

        print(
            f"Power einde       : "
            f"{batterij['power_einde']:11.3f} W"
        )