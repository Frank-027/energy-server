# --------------------------------------------------------------
# reports.py
#
# Rapportages en analyses van Energy Server data
# --------------------------------------------------------------

# ==============================================================
# HULPFUNCTIES - DATATYPES VOOR API
# ==============================================================

def naar_float(waarde):
    if waarde is None:
        return None

    return float(waarde)


def naar_int(waarde):
    if waarde is None:
        return None

    return int(waarde)

def naar_timestamp(waarde):
    if waarde is None:
        return None
    return waarde.isoformat()

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

    if resultaat is None:
        return None

    return {
        "datapunten":
            naar_int(resultaat["datapunten"]),

        "eerste_meting":
            naar_timestamp(resultaat["eerste_meting"]),

        "laatste_meting":
            naar_timestamp(resultaat["laatste_meting"]),

        "production_kwh":
            naar_float(resultaat["production_kwh"]),

        "consumption_kwh":
            naar_float(resultaat["consumption_kwh"]),

        "feed_in_kwh":
            naar_float(resultaat["feed_in_kwh"]),

        "purchased_kwh":
            naar_float(resultaat["purchased_kwh"]),

        "self_consumption_kwh":
            naar_float(resultaat["self_consumption_kwh"])
    }

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

    if resultaat is None:
        return None

    return {
        "datapunten":
            naar_int(resultaat["datapunten"]),

        "eerste_meting":
            naar_timestamp(resultaat["eerste_meting"]),

        "laatste_meting":
            naar_timestamp(resultaat["laatste_meting"]),

        "beschikbare_dagen":
            naar_int(resultaat["beschikbare_dagen"]),

        "production_kwh":
            naar_float(resultaat["production_kwh"]),

        "consumption_kwh":
            naar_float(resultaat["consumption_kwh"]),

        "feed_in_kwh":
            naar_float(resultaat["feed_in_kwh"]),

        "purchased_kwh":
            naar_float(resultaat["purchased_kwh"]),

        "self_consumption_kwh":
            naar_float(resultaat["self_consumption_kwh"])
    }

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

    rijen = cursor.fetchall()

    cursor.close()

    resultaten = []

    for rij in rijen:

        resultaten.append({

            "datum":
                naar_timestamp(rij["datum"]),

            "datapunten":
                naar_int(rij["datapunten"]),

            "eerste_meting":
                naar_timestamp(rij["eerste_meting"]),

            "laatste_meting":
                naar_timestamp(rij["laatste_meting"]),

            "production_kwh":
                naar_float(rij["production_kwh"]),

            "consumption_kwh":
                naar_float(rij["consumption_kwh"]),

            "feed_in_kwh":
                naar_float(rij["feed_in_kwh"]),

            "purchased_kwh":
                naar_float(rij["purchased_kwh"]),

            "self_consumption_kwh":
                naar_float(rij["self_consumption_kwh"])
        })

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
        energie_opgeslagen_begin_kwh = round(
            soc_begin / 100
            * begin["full_pack_energy_available_wh"]
            / 1000,
            3
        )

    if (
        soc_einde is not None
        and einde["full_pack_energy_available_wh"] is not None
    ):
        energie_opgeslagen_einde_kwh = round(
            soc_einde / 100
            * einde["full_pack_energy_available_wh"]
            / 1000,
            3
        )

    if (
        energie_opgeslagen_begin_kwh is not None
        and energie_opgeslagen_einde_kwh is not None
    ):
        energie_opgeslagen_verschil_kwh = (
            energie_opgeslagen_einde_kwh
            - energie_opgeslagen_begin_kwh
        )
        # ----------------------------------------------------------
    # Energie geladen / ontladen uit batterijvermogen
    #
    # power_w > 0  = laden
    # power_w < 0  = ontladen
    #
    # We gebruiken telkens het werkelijke tijdsverschil tussen
    # twee opeenvolgende metingen.
    # ----------------------------------------------------------

    geladen_wh = 0.0
    ontladen_wh = 0.0

    for i in range(len(rijen) - 1):

        huidige = rijen[i]
        volgende = rijen[i + 1]

        power_w = naar_float(huidige["power_w"])

        if power_w is None:
            continue

        interval_seconden = (
            volgende["timestamp"] - huidige["timestamp"]
        ).total_seconds()

        if interval_seconden <= 0:
            continue

        # Een normaal interval is ongeveer 5 minuten.
        # Grote gaten in de meetreeks rekenen we niet mee.
        if interval_seconden > 600:
            continue

        energie_wh = (
            abs(power_w)
            * interval_seconden
            / 3600
        )

        if power_w > 0:
            geladen_wh += energie_wh

        elif power_w < 0:
            ontladen_wh += energie_wh

    charged_kwh = round( geladen_wh / 1000, 3)
    discharged_kwh = round( ontladen_wh / 1000, 3)

    return {

        # ------------------------------------------------------
        # Lifetime tellers
        # ------------------------------------------------------

        "charged_kwh":
            naar_float(charged_kwh),

        "discharged_kwh":
            naar_float(discharged_kwh),

        # ------------------------------------------------------
        # State of Charge
        # ------------------------------------------------------

        "soc_begin":
            naar_float(soc_begin),

        "soc_einde":
            naar_float(soc_einde),

        "soc_begin_timestamp":
            naar_timestamp(soc_begin_timestamp),

        "soc_einde_timestamp":
            naar_timestamp(soc_einde_timestamp),

        # ------------------------------------------------------
        # Beschikbare batterijcapaciteit
        # ------------------------------------------------------

        "capaciteit_begin_kwh": naar_float(
            begin["full_pack_energy_available_wh"] / 1000
            if begin["full_pack_energy_available_wh"] is not None
            else None
        ),

        "capaciteit_einde_kwh": naar_float(
            einde["full_pack_energy_available_wh"] / 1000
            if einde["full_pack_energy_available_wh"] is not None
            else None
        ),

        # ------------------------------------------------------
        # Energie volgens SOC
        # ------------------------------------------------------

        "energie_opgeslagen_begin_kwh":
            naar_float(energie_opgeslagen_begin_kwh),

        "energie_opgeslagen_einde_kwh":
            naar_float(energie_opgeslagen_einde_kwh),

        "energie_opgeslagen_verschil_kwh":
            naar_float(energie_opgeslagen_verschil_kwh),

        # ------------------------------------------------------
        # Batterijvermogen
        # ------------------------------------------------------

        "power_begin":
            naar_float(begin["power_w"]),

        "power_einde":
            naar_float(einde["power_w"]),

        # ------------------------------------------------------
        # Metadata
        # ------------------------------------------------------

        "eerste_meting":
            naar_timestamp(begin["timestamp"]),

        "laatste_meting":
            naar_timestamp(einde["timestamp"]),

        "datapunten":
            naar_int(len(rijen))
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
    # Energie geladen / ontladen uit batterijvermogen
    #
    # power_w > 0  = laden
    # power_w < 0  = ontladen
    #
    # We gebruiken het werkelijke tijdsverschil tussen
    # twee opeenvolgende metingen.
    # ----------------------------------------------------------

    geladen_wh = 0.0
    ontladen_wh = 0.0

    for i in range(len(rijen) - 1):

        huidige = rijen[i]
        volgende = rijen[i + 1]

        power_w = naar_float(huidige["power_w"])

        if power_w is None:
            continue

        # Overgang naar een volgende kalenderdag niet meerekenen.
        # Zo gebruikt batterij_periode exact dezelfde daglogica
        # als batterij_per_dag en batterij_dag.
        if (
            huidige["timestamp"].date()
            != volgende["timestamp"].date()
        ):
            continue

        interval_seconden = (
            volgende["timestamp"]
            - huidige["timestamp"]
        ).total_seconds()

        if interval_seconden <= 0:
            continue

        # Een normaal interval is ongeveer 5 minuten.
        # Grote gaten in de meetreeks rekenen we niet mee.
        if interval_seconden > 600:
            continue

        energie_wh = (
            abs(power_w)
            * interval_seconden
            / 3600
        )

        if power_w > 0:
            geladen_wh += energie_wh

        elif power_w < 0:
            ontladen_wh += energie_wh

    charged_kwh = round(
        geladen_wh / 1000,
        3
    )

    discharged_kwh = round(
        ontladen_wh / 1000,
        3
    )

    # ----------------------------------------------------------
    # Batterij-energie volgens SOC
    # ----------------------------------------------------------

    energie_opgeslagen_begin_kwh = None
    energie_opgeslagen_einde_kwh = None
    energie_opgeslagen_verschil_kwh = None

    if (
        eerste_soc is not None
        and eerste["full_pack_energy_available_wh"] is not None
    ):
        energie_opgeslagen_begin_kwh = round(
            eerste_soc["battery_percentage"]
            / 100
            * eerste["full_pack_energy_available_wh"]
            / 1000,
            3
        )

    if (
        laatste_soc is not None
        and laatste["full_pack_energy_available_wh"] is not None
    ):
        energie_opgeslagen_einde_kwh = round(
            laatste_soc["battery_percentage"]
            / 100
            * laatste["full_pack_energy_available_wh"]
            / 1000,
            3
        )

    if (
        energie_opgeslagen_begin_kwh is not None
        and energie_opgeslagen_einde_kwh is not None
    ):
        energie_opgeslagen_verschil_kwh = round(
            energie_opgeslagen_einde_kwh
            - energie_opgeslagen_begin_kwh,
            3
        )
    # ----------------------------------------------------------
    # Resultaat
    # ----------------------------------------------------------

    return {

        # ------------------------------------------------------
        # Energie geladen / ontladen
        # ------------------------------------------------------

        "charged_kwh":
            naar_float(charged_kwh),

        "discharged_kwh":
            naar_float(discharged_kwh),

        # ------------------------------------------------------
        # State of Charge
        # ------------------------------------------------------

        "soc_begin": naar_float(
            eerste_soc["battery_percentage"]
            if eerste_soc is not None
            else None
        ),

        "soc_einde": naar_float(
            laatste_soc["battery_percentage"]
            if laatste_soc is not None
            else None
        ),

        "soc_begin_timestamp": naar_timestamp(
            eerste_soc["timestamp"]
            if eerste_soc is not None
            else None
        ),

        "soc_einde_timestamp": naar_timestamp(
            laatste_soc["timestamp"]
            if laatste_soc is not None
            else None
        ),

        "soc_begin_bekend":
            eerste_soc is not None,

        # ------------------------------------------------------
        # Beschikbare batterijcapaciteit
        # ------------------------------------------------------

        "capaciteit_begin_kwh": naar_float(
            eerste["full_pack_energy_available_wh"] / 1000
            if eerste["full_pack_energy_available_wh"] is not None
            else None
        ),

        "capaciteit_einde_kwh": naar_float(
            laatste["full_pack_energy_available_wh"] / 1000
            if laatste["full_pack_energy_available_wh"] is not None
            else None
        ),

        # ------------------------------------------------------
        # Energie volgens SOC
        # ------------------------------------------------------

        "energie_opgeslagen_begin_kwh":
            naar_float(energie_opgeslagen_begin_kwh),

        "energie_opgeslagen_einde_kwh":
            naar_float(energie_opgeslagen_einde_kwh),

        "energie_opgeslagen_verschil_kwh":
            naar_float(energie_opgeslagen_verschil_kwh),

        # ------------------------------------------------------
        # Batterijvermogen
        # ------------------------------------------------------

        "power_begin":
            naar_float(eerste["power_w"]),

        "power_einde":
            naar_float(laatste["power_w"]),

        # ------------------------------------------------------
        # Metadata
        # ------------------------------------------------------

        "datapunten":
            naar_int(len(rijen)),

        "beschikbare_dagen":
            naar_int(beschikbare_dagen),

        "eerste_meting":
            naar_timestamp(eerste["timestamp"]),

        "laatste_meting":
            naar_timestamp(laatste["timestamp"])
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
                battery_percentage,
                power_w
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
        # ------------------------------------------------------

        begin = metingen[0]
        einde = metingen[-1]

        # ------------------------------------------------------
        # Energie geladen / ontladen uit batterijvermogen
        #
        # power_w > 0  = laden
        # power_w < 0  = ontladen
        # ------------------------------------------------------

        geladen_wh = 0.0
        ontladen_wh = 0.0

        for i in range(len(metingen) - 1):

            huidige = metingen[i]
            volgende = metingen[i + 1]

            power_w = naar_float(huidige["power_w"])

            if power_w is None:
                continue

            interval_seconden = (
                volgende["timestamp"]
                - huidige["timestamp"]
            ).total_seconds()

            if interval_seconden <= 0:
                continue

            # Normaal meetinterval is ongeveer 5 minuten.
            # Grote gaten rekenen we niet mee.
            if interval_seconden > 600:
                continue

            energie_wh = (
                abs(power_w)
                * interval_seconden
                / 3600
            )

            if power_w > 0:
                geladen_wh += energie_wh

            elif power_w < 0:
                ontladen_wh += energie_wh

        charged_kwh = round(
            geladen_wh / 1000,
            3
        )

        discharged_kwh = round(
            ontladen_wh / 1000,
            3
)
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
                dag["datum"].isoformat(),

            "datapunten":
                naar_int(dag["datapunten"]),

            # --------------------------------------------------
            # Energie geladen / ontladen
            # --------------------------------------------------

            "charged_kwh":
                naar_float(charged_kwh),

            "discharged_kwh":
                naar_float(discharged_kwh),

            # --------------------------------------------------
            # SOC
            # --------------------------------------------------

            "soc_begin": naar_float(
                soc_meting_begin["battery_percentage"]
                if soc_meting_begin is not None
                else None
            ),

            "soc_einde": naar_float(
                soc_meting_einde["battery_percentage"]
                if soc_meting_einde is not None
                else None
            ),

            # --------------------------------------------------
            # SOC timestamps
            # --------------------------------------------------

            "soc_begin_timestamp": naar_timestamp(
                soc_meting_begin["timestamp"]
                if soc_meting_begin is not None
                else None
            ),

            "soc_einde_timestamp": naar_timestamp(
                soc_meting_einde["timestamp"]
                if soc_meting_einde is not None
                else None
            )
        })

    return resultaten

# ==============================================================
# ENERGIE - ACTUEEL
# ==============================================================

def energie_actueel(verbinding):

    # ----------------------------------------------------------
    # Laatste energiemeting
    # ----------------------------------------------------------

    sql_energie = """
        SELECT
            timestamp,
            production_w,
            consumption_w,
            feed_in_w,
            purchased_w,
            self_consumption_w

        FROM energy_power

        ORDER BY timestamp DESC

        LIMIT 1
    """

    cursor = verbinding.cursor(dictionary=True)
    cursor.execute(sql_energie)
    energie = cursor.fetchone()
    cursor.close()

    if energie is None:
        return None

    # ----------------------------------------------------------
    # Batterijmeting die het dichtst bij de energiemeting ligt
    # ----------------------------------------------------------

    sql_batterij = """
        SELECT
            timestamp,
            power_w

        FROM energy_battery

        ORDER BY ABS(
            TIMESTAMPDIFF(
                SECOND,
                timestamp,
                %s
            )
        )

        LIMIT 1
    """

    cursor = verbinding.cursor(dictionary=True)

    cursor.execute(
        sql_batterij,
        (energie["timestamp"],)
    )

    batterij = cursor.fetchone()
    cursor.close()

    # ----------------------------------------------------------
    # Batterijvermogen
    #
    # Positief = laden
    # Negatief = ontladen
    # ----------------------------------------------------------

    batterij_laden_w = 0
    batterij_ontladen_w = 0

    if batterij is not None and batterij["power_w"] is not None:

        power_w = naar_float(batterij["power_w"])

        if power_w > 0:
            batterij_laden_w = power_w

        elif power_w < 0:
            batterij_ontladen_w = abs(power_w)

    # ----------------------------------------------------------
    # Zonneproductie verdelen
    # ----------------------------------------------------------

    productie_w = naar_float(
        energie["production_w"]
    )

    injectie_w = naar_float(
        energie["feed_in_w"]
    )

    # injectie = naar net
    # batterij laden = naar batterij
    # rest = naar huis

    naar_net_w = injectie_w

    naar_batterij_w = batterij_laden_w

    naar_huis_w = round(
        productie_w
        - naar_net_w
        - naar_batterij_w,
        3
    )

    # Negatieve waarde voorkomen door afrondingsverschillen
    if naar_huis_w < 0:
        naar_huis_w = 0

    # ----------------------------------------------------------
    # Resultaat
    # ----------------------------------------------------------

    return {

        "timestamp":
            naar_timestamp(energie["timestamp"]),

        "batterij_timestamp":
            naar_timestamp(
                batterij["timestamp"]
                if batterij is not None
                else None
            ),

        "production_w":
            naar_float(energie["production_w"]),

        "consumption_w":
            naar_float(energie["consumption_w"]),

        "naar_huis_w":
            naar_float(naar_huis_w),

        "naar_batterij_w":
            naar_float(naar_batterij_w),

        "naar_net_w":
            naar_float(naar_net_w),

        "batterij_laden_w":
            naar_float(batterij_laden_w),

        "batterij_ontladen_w":
            naar_float(batterij_ontladen_w),

        "purchased_w":
            naar_float(energie["purchased_w"])
    }

# ==============================================================
# BATTERIJ - ACTUEEL
# ==============================================================

def batterij_actueel(verbinding):

    sql = """
        SELECT
            timestamp,
            lifetime_energy_charged_wh,
            lifetime_energy_discharged_wh,
            battery_percentage,
            full_pack_energy_available_wh,
            power_w

        FROM energy_battery

        ORDER BY timestamp DESC

        LIMIT 1
    """

    cursor = verbinding.cursor(dictionary=True)
    cursor.execute(sql)
    batterij = cursor.fetchone()
    cursor.close()

    if batterij is None:
        return None

    # ----------------------------------------------------------
    # Batterijvermogen
    #
    # Positief = laden
    # Negatief = ontladen
    # ----------------------------------------------------------

    batterij_laden_w = 0
    batterij_ontladen_w = 0

    if batterij["power_w"] is not None:

        if batterij["power_w"] > 0:
            batterij_laden_w = batterij["power_w"]

        elif batterij["power_w"] < 0:
            batterij_ontladen_w = abs(batterij["power_w"])

    # ----------------------------------------------------------
    # Resultaat
    # ----------------------------------------------------------

    return {

        "timestamp":
            naar_timestamp(batterij["timestamp"]),

        "battery_percentage":
            naar_float(batterij["battery_percentage"]),

        "full_pack_energy_available_kwh":
            naar_float(
                batterij["full_pack_energy_available_wh"] / 1000
                if batterij["full_pack_energy_available_wh"] is not None
                else None
            ),

        "power_w":
            naar_float(batterij["power_w"]),

        "batterij_laden_w":
            naar_float(batterij_laden_w),

        "batterij_ontladen_w":
            naar_float(batterij_ontladen_w),

        "lifetime_energy_charged_kwh":
            naar_float(
                batterij["lifetime_energy_charged_wh"] / 1000
                if batterij["lifetime_energy_charged_wh"] is not None
                else None
            ),

        "lifetime_energy_discharged_kwh":
            naar_float(
                batterij["lifetime_energy_discharged_wh"] / 1000
                if batterij["lifetime_energy_discharged_wh"] is not None
                else None
            )
    }

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