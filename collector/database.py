# --------------------------------------------------------------
# database.py
#
# version 1.1 F.Demonie
# --------------------------------------------------------------
import mysql.connector

def maak_databaseverbinding(config):
  """
  Maakt een verbinding met de MySQL-database.

  Returns:
      mysql.connector.Connection object
      None indien de verbinding mislukt
  """
  try:
    verbinding = mysql.connector.connect(
      host=config["db_host"],
      database=config["db_name"],
      user=config["db_user"],
      password=config["db_password"]
    )

    print("Databaseverbinding OK")
    return verbinding

  except mysql.connector.Error as fout:
    print("Databasefout:", fout)
    return None

def bewaar_power_data(verbinding, records):
  """ Bewaart de power data in de MySQL-database.
  """

  sql = """
    INSERT INTO energy_power
    (
        timestamp,
        purchased_w,
        production_w,
        self_consumption_w,
        consumption_w,
        feed_in_w
    )
    VALUES (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        purchased_w = VALUES(purchased_w),
        production_w = VALUES(production_w),
        self_consumption_w = VALUES(self_consumption_w),
        consumption_w = VALUES(consumption_w),
        feed_in_w = VALUES(feed_in_w)
  """

  cursor = verbinding.cursor()

  for record in records:

    waarden = (
      record["timestamp"],
      record["purchased_w"],
      record["production_w"],
      record["self_consumption_w"],
      record["consumption_w"],
      record["feed_in_w"]
    )

    cursor.execute(sql, waarden)

  verbinding.commit()
  cursor.close()

  print(f"{len(records)} power-record(s) opgeslagen.")

def bewaar_battery_data(verbinding, records):
  """ Bewaart de batterijdata in de MySQL-database.
  """
  sql = """
    INSERT INTO energy_battery
    (
      timestamp,
      serial_number,
      power_w,
      battery_state,
      battery_percentage,
      lifetime_energy_discharged_wh,
      lifetime_energy_charged_wh,
      full_pack_energy_available_wh,
      internal_temperature_c,
      ac_grid_charging
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
      serial_number = VALUES(serial_number),
      power_w = VALUES(power_w),
      battery_state = VALUES(battery_state),
      battery_percentage = VALUES(battery_percentage),
      lifetime_energy_discharged_wh = VALUES(lifetime_energy_discharged_wh),
      lifetime_energy_charged_wh = VALUES(lifetime_energy_charged_wh),
      full_pack_energy_available_wh = VALUES(full_pack_energy_available_wh),
      internal_temperature_c = VALUES(internal_temperature_c),
      ac_grid_charging = VALUES(ac_grid_charging)
  """

  cursor = verbinding.cursor()

  for record in records:

    waarden = (
      record["timestamp"],
      record["serial_number"],
      record["power_w"],
      record["battery_state"],
      record["battery_percentage"],
      record["lifetime_energy_discharged_wh"],
      record["lifetime_energy_charged_wh"],
      record["full_pack_energy_available_wh"],
      record["internal_temperature_c"],
      record["ac_grid_charging"]
    )

    cursor.execute(sql, waarden)

  verbinding.commit()
  cursor.close()

  print(f"{len(records)} battery-record(s) opgeslagen.")