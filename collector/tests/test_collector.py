from config import laad_configuratie
from database import maak_databaseverbinding
from collector import verzamel_en_bewaar


start_time = "2026-08-01 00:00:00"
end_time = "2026-08-08 00:00:00"

config = laad_configuratie()

if config is None:
    print("Fout: configuratie kon niet worden geladen.")
    exit(1)

verbinding = maak_databaseverbinding(config)

if verbinding:

    print("Databaseverbinding OK")

    verzamel_en_bewaar(
        config,
        verbinding,
        start_time,
        end_time
    )

    verbinding.close()