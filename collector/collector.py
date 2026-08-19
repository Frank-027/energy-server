# --------------------------------------------------------------
# collector.py
#
# version 1.1 F.Demonie
# --------------------------------------------------------------

from datetime import datetime, timedelta
import requests
from .config import laad_configuratie
from .database import ( 
  maak_databaseverbinding, 
  bewaar_power_data, 
  bewaar_battery_data 
)

# --------------------------------------------------------------
# SolarEdge API functies
#--------------------------------------------------------------
def haal_power_data_op(config, start_time, end_time):
  """
  Haalt power data op uit de SolarEdge Monitoring API.

  Parameters:
      start_time : begin van de periode
      end_time   : einde van de periode

  Returns:
      JSON-data van SolarEdge
      None indien de API-call mislukt
  """

  url = f"https://monitoringapi.solaredge.com/site/{config['site_id']}/powerDetails"

  params = {
      "startTime": start_time,
      "endTime": end_time,
      "api_key": config['api_key']
  }

  try:
    response = requests.get(url, params=params, timeout=30)

  except requests.RequestException as fout:
    print("Fout bij verbinding met SolarEdge API:", fout)
    return None

  # HTTP-status controleren
  if response.status_code != 200:
    print("SolarEdge API fout:")
    print("HTTP status:", response.status_code)
    print("Antwoord:", response.text)
    return None

  # JSON proberen te lezen
  try:
    data = response.json()
  except ValueError:
    print("Fout: SolarEdge gaf geen geldige JSON terug.")
    return None

  # Controleren of de verwachte structuur aanwezig is
  if "powerDetails" not in data:
    print("Fout: 'powerDetails' ontbreekt in het API-antwoord.")
    print(data)
    return None

  return data


def verwerk_power_data(data):
  records = []
  meters = data["powerDetails"]["meters"]

  # Tijdstippen verzamelen
  timestamps = set()

  for meter in meters:
    for value in meter["values"]:
      timestamps.add(value["date"])

  # Voor elk tijdstip één record maken
  for timestamp in sorted(timestamps):

    record = {
        "timestamp": timestamp,
        "purchased_w": None,
        "production_w": None,
        "self_consumption_w": None,
        "consumption_w": None,
        "feed_in_w": None
    }

    # Waarden van de verschillende meters invullen
    for meter in meters:

      meter_type = meter["type"]

      for value in meter["values"]:
        if value["date"] == timestamp:

          # SolarEdge laat bij nulproductie soms "value" weg
          if "value" not in value:

            if meter_type == "Production":
              record["production_w"] = 0
              continue

            elif meter_type == "SelfConsumption":
              record["self_consumption_w"] = 0
              continue

            print(
                f"WAARSCHUWING: ontbrekende value: "
                f"timestamp={timestamp}, "
                f"meter={meter_type}, "
                f"record={value}",
                flush=True
            )
            continue

          if meter_type == "Purchased":
            record["purchased_w"] = value["value"]

          elif meter_type == "Production":
            record["production_w"] = value["value"]

          elif meter_type == "SelfConsumption":
            record["self_consumption_w"] = value["value"]

          elif meter_type == "Consumption":
            record["consumption_w"] = value["value"]

          elif meter_type == "FeedIn":
            record["feed_in_w"] = value["value"]

    # Controleren of alle vijf meetwaarden aanwezig zijn
    ontbrekende_velden = [
        veldnaam
        for veldnaam, meetwaarde in record.items()
        if veldnaam != "timestamp" and meetwaarde is None
    ]

    if ontbrekende_velden:
      print(
          f"WAARSCHUWING: onvolledig power-record overgeslagen: "
          f"timestamp={timestamp}, "
          f"ontbrekend={ontbrekende_velden}",
          flush=True
      )
      continue

    records.append(record)

  return records

def haal_battery_data_op(config, start_time, end_time):
  """
  Haalt batterijdata op uit de SolarEdge Monitoring API.

  Parameters:
      start_time : begin van de periode
      end_time   : einde van de periode

  Returns:
      JSON-data van SolarEdge
      None indien de API-call mislukt
  """

  url = f"https://monitoringapi.solaredge.com/site/{config['site_id']}/storageData"

  params = {
      "startTime": start_time,
      "endTime": end_time,
      "api_key": config['api_key']
  }

  try:
    response = requests.get(
      url,
      params=params,
      timeout=30
    )

  except requests.RequestException as fout:
    print("Fout bij verbinding met SolarEdge API:", fout)
    return None

  # HTTP-status controleren
  if response.status_code != 200:
    print("SolarEdge API fout:")
    print("HTTP status:", response.status_code)
    print("Antwoord:", response.text)
    return None

  # JSON proberen te lezen
  try:
    data = response.json()

  except ValueError:
    print("Fout: SolarEdge gaf geen geldige JSON terug.")
    return None

  # Verwachte structuur controleren
  if "storageData" not in data:
    print("Fout: 'storageData' ontbreekt in het API-antwoord.")
    print(data)
    return None

  return data

def verwerk_battery_data(data):
  """ Verwerkt de batterijdata van de SolarEdge API.
  
  Parameters:
      data : JSON-data van SolarEdge
      Returns:
          Lijst van records met batterijdata
  """

  records = []
  storage_data = data["storageData"]

  # Er kunnen volgens de API meerdere batterijen aanwezig zijn
  for battery in storage_data["batteries"]:
    serial_number = battery["serialNumber"]

    for telemetry in battery["telemetries"]:
      record = {
        "timestamp": telemetry["timeStamp"],
        "power_w": telemetry["power"],
        "battery_state": telemetry["batteryState"],
        "battery_percentage": telemetry["batteryPercentageState"],
        "lifetime_energy_discharged_wh":
            telemetry["lifeTimeEnergyDischarged"],
        "lifetime_energy_charged_wh":
            telemetry["lifeTimeEnergyCharged"],
        "full_pack_energy_available_wh":
            telemetry["fullPackEnergyAvailable"],
        "internal_temperature_c":
            telemetry["internalTemp"],
        "ac_grid_charging":
            telemetry["ACGridCharging"],
        "serial_number": serial_number
      }

      records.append(record)

  return records

# --------------------------------------------------------------
# Verzamel en bewaar
# --------------------------------------------------------------

def verzamel_en_bewaar(config, verbinding, start_time, end_time):
    """
    Verzamelt power- en batterijdata van SolarEdge
    en bewaart deze in de database.
    """

    print(f"Data ophalen van {start_time} tot {end_time}")

    # ----------------------------------------------------------
    # Power
    # ----------------------------------------------------------

    power_data = haal_power_data_op(
        config,
        start_time,
        end_time
    )

    if power_data is not None:

        power_records = verwerk_power_data(power_data)

        print(
            f"{len(power_records)} power-record(s) verwerkt."
        )

        if power_records:
            bewaar_power_data(
                verbinding,
                power_records
            )

    # ----------------------------------------------------------
    # Battery
    # ----------------------------------------------------------

    battery_data = haal_battery_data_op(
        config,
        start_time,
        end_time
    )

    if battery_data is not None:

        battery_records = verwerk_battery_data(
            battery_data
        )

        if battery_records:
            bewaar_battery_data(
                verbinding,
                battery_records
            )

# --------------------------------------------------------------
# MAIN
# --------------------------------------------------------------

def main():

    # ----------------------------------------------------------
    # Configuratie laden
    # ----------------------------------------------------------

    config = laad_configuratie()

    if config is None:
        print("Fout: configuratie kon niet worden geladen.")
        return

    # ----------------------------------------------------------
    # Tijdvenster bepalen
    #
    # We halen telkens de laatste 30 minuten opnieuw op.
    # Door ON DUPLICATE KEY UPDATE worden bestaande records
    # bijgewerkt en ontstaan er geen dubbele records.
    # ----------------------------------------------------------

    einde = datetime.now()
    begin = einde - timedelta(minutes=30)

    start_time = begin.strftime("%Y-%m-%d %H:%M:%S")
    end_time = einde.strftime("%Y-%m-%d %H:%M:%S")

    # ----------------------------------------------------------
    # Databaseverbinding
    # ----------------------------------------------------------

    verbinding = maak_databaseverbinding(config)

    if verbinding is None:
        print("Fout: databaseverbinding kon niet worden gemaakt.")
        return

    try:

        verzamel_en_bewaar(
            config,
            verbinding,
            start_time,
            end_time
        )

    finally:
        verbinding.close()


if __name__ == "__main__":
    main()