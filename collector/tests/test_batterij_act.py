# --------------------------------------------------------------
# test_batterij_act.py
#
# Test batterij_actueel() en geef laatste batterijmeting door
# --------------------------------------------------------------

from config import laad_configuratie
from database import maak_databaseverbinding
from reports.reports import batterij_actueel


config = laad_configuratie()

if config is None:
    print("Configuratie kon niet worden geladen.")
    exit()


verbinding = maak_databaseverbinding(config)

if verbinding is None:
    print("Databaseverbinding kon niet worden gemaakt.")
    exit()


try:

    resultaat = batterij_actueel(verbinding)

    print()
    print("=" * 70)
    print("ACTUELE BATTERIJDATA")
    print("=" * 70)
    print(resultaat)

finally:

    verbinding.close()