# ==============================================================
# api_usage_report.py
#
# Rapportering van het API-gebruik per leerling.
# ==============================================================

from config import laad_configuratie
from database import maak_databaseverbinding


# ==============================================================
# HULPFUNCTIE
# ==============================================================

def print_titel(titel):

    print()
    print("=" * 80)
    print(titel)
    print("=" * 80)


# ==============================================================
# RAPPORT 1 - TOTAAL PER LEERLING
# ==============================================================

def rapport_totaal_per_leerling(verbinding):

    sql = """
        SELECT
            k.leerling,
            COUNT(r.id) AS aantal_requests
        FROM api_keys k
        LEFT JOIN api_requests r
            ON r.api_key_id = k.id
        GROUP BY
            k.id,
            k.leerling
        ORDER BY
            aantal_requests DESC,
            k.leerling
    """

    cursor = verbinding.cursor(dictionary=True)
    cursor.execute(sql)
    rijen = cursor.fetchall()
    cursor.close()

    print_titel("API-GEBRUIK PER LEERLING")

    print(
        f"{'Leerling':<25}"
        f"{'Requests':>10}"
    )

    print("-" * 35)

    for rij in rijen:

        print(
            f"{rij['leerling']:<25}"
            f"{rij['aantal_requests']:>10}"
        )


# ==============================================================
# RAPPORT 2 - PER ENDPOINT
# ==============================================================

def rapport_per_endpoint(verbinding):

    sql = """
        SELECT
            k.leerling,
            r.endpoint,
            COUNT(*) AS aantal_requests
        FROM api_requests r
        JOIN api_keys k
            ON k.id = r.api_key_id
        GROUP BY
            k.id,
            k.leerling,
            r.endpoint
        ORDER BY
            k.leerling,
            aantal_requests DESC
    """

    cursor = verbinding.cursor(dictionary=True)
    cursor.execute(sql)
    rijen = cursor.fetchall()
    cursor.close()

    print_titel("API-GEBRUIK PER ENDPOINT")

    huidige_leerling = None

    for rij in rijen:

        if rij["leerling"] != huidige_leerling:

            huidige_leerling = rij["leerling"]

            print()
            print(huidige_leerling)
            print("-" * 60)

        print(
            f"{rij['endpoint']:<50}"
            f"{rij['aantal_requests']:>8}"
        )


# ==============================================================
# RAPPORT 3 - PER DAG
# ==============================================================

def rapport_per_dag(verbinding):

    sql = """
        SELECT
            DATE(r.aangemaakt_op) AS datum,
            k.leerling,
            COUNT(*) AS aantal_requests
        FROM api_requests r
        JOIN api_keys k
            ON k.id = r.api_key_id
        GROUP BY
            DATE(r.aangemaakt_op),
            k.id,
            k.leerling
        ORDER BY
            datum,
            k.leerling
    """

    cursor = verbinding.cursor(dictionary=True)
    cursor.execute(sql)
    rijen = cursor.fetchall()
    cursor.close()

    print_titel("API-GEBRUIK PER DAG")

    print(
        f"{'Datum':<15}"
        f"{'Leerling':<25}"
        f"{'Requests':>10}"
    )

    print("-" * 50)

    for rij in rijen:

        print(
            f"{str(rij['datum']):<15}"
            f"{rij['leerling']:<25}"
            f"{rij['aantal_requests']:>10}"
        )


# ==============================================================
# RAPPORT 4 - FOUTEN
# ==============================================================

def rapport_fouten(verbinding):

    sql = """
        SELECT
            k.leerling,
            r.status_code,
            COUNT(*) AS aantal
        FROM api_requests r
        JOIN api_keys k
            ON k.id = r.api_key_id
        WHERE r.status_code <> 200
        GROUP BY
            k.id,
            k.leerling,
            r.status_code
        ORDER BY
            k.leerling,
            r.status_code
    """

    cursor = verbinding.cursor(dictionary=True)
    cursor.execute(sql)
    rijen = cursor.fetchall()
    cursor.close()

    print_titel("API-FOUTEN PER LEERLING")

    if not rijen:

        print("Geen API-fouten geregistreerd.")
        return

    print(
        f"{'Leerling':<25}"
        f"{'Status':>10}"
        f"{'Aantal':>10}"
    )

    print("-" * 45)

    for rij in rijen:

        print(
            f"{rij['leerling']:<25}"
            f"{rij['status_code']:>10}"
            f"{rij['aantal']:>10}"
        )


# ==============================================================
# MAIN
# ==============================================================

def main():

    config = laad_configuratie()

    if config is None:
        print("Configuratie kon niet worden geladen.")
        return

    verbinding = maak_databaseverbinding(config)

    if verbinding is None:
        print("Databaseverbinding kon niet worden gemaakt.")
        return

    try:

        rapport_totaal_per_leerling(
            verbinding
        )

        rapport_per_endpoint(
            verbinding
        )

        rapport_per_dag(
            verbinding
        )

        rapport_fouten(
            verbinding
        )

    finally:

        verbinding.close()


if __name__ == "__main__":
    main()