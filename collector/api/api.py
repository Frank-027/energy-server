# ==============================================================
# api.py
#
# haalt SolarEdge data op en publiceert via een REST-api
# ==============================================================
from flask import Flask, jsonify, request
from flask_cors import CORS
import hashlib

from ..config import laad_configuratie
from ..database import maak_databaseverbinding
from ..reports.reports import ( 
  energie_dag, 
  energie_periode,
  batterij_dag,
  batterij_periode
)  


app = Flask(__name__)
CORS(app)

# ==============================================================
# Functie die API Keys van de leerlingen valideert.
# ==============================================================
def controleer_api_key(config):
    """
    Controleert de API-key die via de HTTP-header
    X-API-Key wordt meegestuurd.

    Returns:
        leerling_id indien geldig
        None indien ongeldig
    """

    api_key = request.headers.get("X-API-Key")

    if not api_key:
        return None

    api_key_hash = hashlib.sha256(
        api_key.encode()
    ).hexdigest()

    verbinding = maak_databaseverbinding(config)

    if verbinding is None:
        return None

    try:
        cursor = verbinding.cursor(dictionary=True)

        sql = """
            SELECT id, leerling
            FROM api_keys
            WHERE api_key_hash = %s
              AND actief = TRUE
        """

        cursor.execute(sql, (api_key_hash,))
        resultaat = cursor.fetchone()

        if resultaat is None:
            return None

        # Laatste gebruik bijwerken
        sql_update = """
            UPDATE api_keys
            SET laatste_gebruik = CURRENT_TIMESTAMP
            WHERE id = %s
        """

        cursor.execute(sql_update, (resultaat["id"],))
        verbinding.commit()

        return resultaat["leerling"]

    finally:
        cursor.close()
        verbinding.close()

# ==============================================================
# ENERGIE - DAG
# ==============================================================
@app.route("/api/energie/dag/<datum>")
def api_energie_dag(datum):

    config = laad_configuratie()

    if config is None:
        return jsonify({
            "error": "Configuratie kon niet worden geladen."
        }), 500

    # API-key controleren
    leerling = controleer_api_key(config)

    if leerling is None:
        return jsonify({
            "error": "Ongeldige of ontbrekende API-key."
        }), 401

    # Databaseverbinding voor rapport
    verbinding = maak_databaseverbinding(config)

    if verbinding is None:
        return jsonify({
            "error": "Databaseverbinding kon niet worden gemaakt."
        }), 500

    try:
        resultaat = energie_dag(
            verbinding,
            datum
        )

        return jsonify(resultaat)

    finally:
        verbinding.close()

# ==============================================================
# ENERGIE - PERIODE
# ==============================================================

@app.route("/api/energie/periode/<start_datum>/<eind_datum>")
def api_energie_periode(start_datum, eind_datum):

    config = laad_configuratie()

    if config is None:
        return jsonify({
            "error": "Configuratie kon niet worden geladen."
        }), 500

    leerling = controleer_api_key(config)

    if leerling is None:
        return jsonify({
            "error": "Ongeldige of ontbrekende API-key."
        }), 401

    verbinding = maak_databaseverbinding(config)

    if verbinding is None:
        return jsonify({
            "error": "Databaseverbinding kon niet worden gemaakt."
        }), 500

    try:
        resultaat = energie_periode(
            verbinding,
            start_datum,
            eind_datum
        )

        return jsonify(resultaat)

    finally:
        verbinding.close()    

# ==============================================================
# BATTERIJ - DAG
# ==============================================================

@app.route("/api/batterij/dag/<datum>")
def api_batterij_dag(datum):

    config = laad_configuratie()

    if config is None:
        return jsonify({
            "error": "Configuratie kon niet worden geladen."
        }), 500

    leerling = controleer_api_key(config)

    if leerling is None:
        return jsonify({
            "error": "Ongeldige of ontbrekende API-key."
        }), 401

    verbinding = maak_databaseverbinding(config)

    if verbinding is None:
        return jsonify({
            "error": "Databaseverbinding kon niet worden gemaakt."
        }), 500

    try:
        resultaat = batterij_dag(
            verbinding,
            datum
        )

        if resultaat is None:
            return jsonify({
                "error": "Geen batterijgegevens gevonden."
            }), 404

        return jsonify(resultaat)

    finally:
        verbinding.close()    

# ==============================================================
# BATTERIJ - PERIODE
# ==============================================================

@app.route("/api/batterij/periode/<start_datum>/<eind_datum>")
def api_batterij_periode(start_datum, eind_datum):

    config = laad_configuratie()

    if config is None:
        return jsonify({
            "error": "Configuratie kon niet worden geladen."
        }), 500

    leerling = controleer_api_key(config)

    if leerling is None:
        return jsonify({
            "error": "Ongeldige of ontbrekende API-key."
        }), 401

    verbinding = maak_databaseverbinding(config)

    if verbinding is None:
        return jsonify({
            "error": "Databaseverbinding kon niet worden gemaakt."
        }), 500

    try:
        resultaat = batterij_periode(
            verbinding,
            start_datum,
            eind_datum
        )

        if resultaat is None:
            return jsonify({
                "error": "Geen batterijgegevens gevonden."
            }), 404

        return jsonify(resultaat)

    finally:
        verbinding.close()                