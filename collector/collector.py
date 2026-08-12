# --------------------------------------------------------------
# collector.py
#
# version 1.1 F.Demonie
# --------------------------------------------------------------

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