# --------------------------------------------------------------
# config.py
#
# version 1.1 F.Demonie
# --------------------------------------------------------------
import os
from dotenv import load_dotenv

#--------------------------------------------------------------
# Laad environment variables
#--------------------------------------------------------------
def laad_configuratie():
  """
  Laadt de configuratie uit het .env-bestand.

  Returns:
      dictionary met configuratie
  Raises:
        ValueError indien een verplichte variabele ontbreekt.    
  """

  load_dotenv()

  configuratie = {
    "site_id": os.getenv("SOLAREDGE_SITE_ID"),
    "api_key": os.getenv("SOLAREDGE_API_KEY"),
    "db_host": os.getenv("DB_HOST"),
    "db_name": os.getenv("DB_DATABASE"),
    "db_user": os.getenv("DB_USER"),
    "db_password": os.getenv("DB_PASSWORD")
  }

  # Controleren of alle variabelen ingevuld zijn
  ontbrekend = []

  for naam, waarde in configuratie.items():
    if waarde is None or waarde == "":
      ontbrekend.append(naam)

  if ontbrekend:
    print("Fout: volgende configuratievariabelen ontbreken:")
    for naam in ontbrekend:
      print("  -", naam)

    return None

  return configuratie