from config import laad_configuratie
from database import maak_databaseverbinding
from reports.reports import (
    toon_dagrapport,
    toon_weekrapport
)


config = laad_configuratie()

verbinding = maak_databaseverbinding(config)

if verbinding:

    print("Databaseverbinding OK")

    toon_dagrapport(
        verbinding,
        "2026-08-07"
    )

    print()

    toon_weekrapport(
        verbinding,
        "2026-08-01",
        "2026-08-07"
    )

    verbinding.close()