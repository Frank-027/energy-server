# ==============================================================
# generate_api_keys.py
#
# Genereert API-keys voor leerlingen en slaat alleen de
# SHA-256 hashes op in MariaDB.
# ==============================================================

import secrets
import hashlib

from config import laad_configuratie
from database import maak_databaseverbinding


AANTAL_LEERLINGEN = 15


def maak_api_key():
    """
    Genereert een cryptografisch sterke API-key.
    """
    return secrets.token_urlsafe(32)


def hash_api_key(api_key):
    """
    Maakt een SHA-256 hash van de API-key.
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


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
# API-KEYS GENEREREN
# ==============================================================

print()
print("=" * 70)
print("API KEYS GENEREREN")
print("=" * 70)
print()

for i in range(1, AANTAL_LEERLINGEN + 1):

    leerling = f"leerling{i:02d}"

    api_key = maak_api_key()
    api_key_hash = hash_api_key(api_key)

    sql = """
        INSERT INTO api_keys
            (leerling, api_key_hash)
        VALUES
            (%s, %s)
    """

    cursor.execute(sql, (leerling, api_key_hash))

    print(f"{leerling}")
    print(f"  API-key : {api_key}")
    print()


# ==============================================================
# OPSLAAN
# ==============================================================

verbinding.commit()

print("=" * 70)
print("15 API-keys succesvol opgeslagen.")
print("=" * 70)
print()

cursor.close()
verbinding.close()