# ==============================================================
# generate_extra_api_keys.py
#
# Genereert:
# - 10 reserve API-keys
# - 1 API-key voor de leraar
#
# Alleen de SHA-256 hashes worden opgeslagen in MariaDB.
# ==============================================================

import secrets
import hashlib

from config import laad_configuratie
from database import maak_databaseverbinding


# ==============================================================
# API-KEY FUNCTIES
# ==============================================================

def maak_api_key():
    """
    Genereert een cryptografisch sterke API-key.
    """
    return secrets.token_urlsafe(32)


def hash_api_key(api_key):
    """
    Maakt een SHA-256 hash van de API-key.
    """
    return hashlib.sha256(
        api_key.encode()
    ).hexdigest()


# ==============================================================
# CONFIGURATIE
# ==============================================================

config = laad_configuratie()

if config is None:
    print("Configuratie kon niet worden geladen.")
    exit(1)


# ==============================================================
# DATABASEVERBINDING
# ==============================================================

verbinding = maak_databaseverbinding(config)

if verbinding is None:
    print("Databaseverbinding mislukt.")
    exit(1)

cursor = verbinding.cursor()


# ==============================================================
# ACCOUNTS DIE WE WILLEN AANMAKEN
# ==============================================================

accounts = [
    "reserve01",
    "reserve02",
    "reserve03",
    "reserve04",
    "reserve05",
    "reserve06",
    "reserve07",
    "reserve08",
    "reserve09",
    "reserve10",
    "leraar_frank"
]


# ==============================================================
# API-KEYS GENEREREN
# ==============================================================

print()
print("=" * 70)
print("EXTRA API-KEYS GENEREREN")
print("=" * 70)
print()

aantal_aangemaakt = 0


for account in accounts:

    # ----------------------------------------------------------
    # Eerst controleren of account reeds bestaat
    # ----------------------------------------------------------

    cursor.execute(
        """
        SELECT id
        FROM api_keys
        WHERE leerling = %s
        """,
        (account,)
    )

    bestaand = cursor.fetchone()

    if bestaand is not None:

        print(
            f"{account}: bestaat reeds - overgeslagen."
        )

        continue


    # ----------------------------------------------------------
    # Nieuwe API-key maken
    # ----------------------------------------------------------

    api_key = maak_api_key()

    api_key_hash = hash_api_key(
        api_key
    )


    # ----------------------------------------------------------
    # Hash opslaan
    # ----------------------------------------------------------

    cursor.execute(
        """
        INSERT INTO api_keys
            (leerling, api_key_hash)
        VALUES
            (%s, %s)
        """,
        (
            account,
            api_key_hash
        )
    )


    # ----------------------------------------------------------
    # Gewone key éénmalig tonen
    # ----------------------------------------------------------

    print(account)
    print(f"  API-key : {api_key}")
    print()

    aantal_aangemaakt += 1


# ==============================================================
# OPSLAAN
# ==============================================================

verbinding.commit()

print("=" * 70)
print(
    f"{aantal_aangemaakt} API-key(s) succesvol aangemaakt."
)
print("=" * 70)

cursor.close()
verbinding.close()