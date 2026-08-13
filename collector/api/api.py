# ==============================================================
# api.py
#
# haalt SolarEdge data op en publiceert via een REST-api
# ==============================================================
from flask import ( 
  Flask, 
  jsonify, 
  request, 
  g,
  render_template_string
)

from flask_cors import CORS
import hashlib

from ..config import laad_configuratie
from ..database import maak_databaseverbinding, log_api_request
from ..reports.reports import ( 
  energie_dag, 
  energie_periode,
  energie_per_dag,
  batterij_dag,
  batterij_periode,
  batterij_per_dag,
  energie_actueel,
  batterij_actueel
)  


app = Flask(__name__)
CORS(app)

# ===============================================
# Logging van de API-request
# ===============================================
@app.after_request
def log_request(response):

    if hasattr(g, "api_key_id"):

        config = laad_configuratie()

        if config is not None:

            verbinding = maak_databaseverbinding(config)

            if verbinding is not None:

                try:

                    log_api_request(
                        verbinding,
                        g.api_key_id,
                        request.path,
                        request.method,
                        response.status_code
                    )

                finally:
                    verbinding.close()

    return response

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

        g.api_key_id = resultaat["id"]
        g.leerling = resultaat["leerling"]

        return resultaat

    finally:
        cursor.close()
        verbinding.close()

# ==============================================================
# API: ENERGIE - DAG
# ==============================================================
@app.route("/api/energie/dag/<datum>")
def api_energie_dag(datum):

    config = laad_configuratie()

    if config is None:
        return jsonify({
            "error": "Configuratie kon niet worden geladen."
        }), 500

    # API-key controleren
    auth = controleer_api_key(config)

    if auth is None:
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

        if resultaat is None:
            return jsonify({
                "error": "Geen energiegegevens gevonden."
            }), 404

        return jsonify(resultaat)

    finally:
        verbinding.close()

# ==============================================================
# API: ENERGIE - PERIODE
# ==============================================================

@app.route("/api/energie/periode/<start_datum>/<eind_datum>")
def api_energie_periode(start_datum, eind_datum):

    config = laad_configuratie()

    if config is None:
        return jsonify({
            "error": "Configuratie kon niet worden geladen."
        }), 500

    auth = controleer_api_key(config)

    if auth is None:
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

        if resultaat is None:
            return jsonify({
                "error": "Geen energiegegevens gevonden."
            }), 404

        return jsonify(resultaat)

    finally:
        verbinding.close()    

# ==============================================================
# API: ENERGIE - PER DAG
# ==============================================================

@app.route("/api/energie/perdag/<start_datum>/<eind_datum>")
def api_energie_per_dag(start_datum, eind_datum):

    config = laad_configuratie()

    if config is None:
        return jsonify({
            "error": "Configuratie kon niet worden geladen."
        }), 500

    auth = controleer_api_key(config)

    if auth is None:
        return jsonify({
            "error": "Ongeldige of ontbrekende API-key."
        }), 401

    verbinding = maak_databaseverbinding(config)

    if verbinding is None:
        return jsonify({
            "error": "Databaseverbinding kon niet worden gemaakt."
        }), 500

    try:
        resultaat = energie_per_dag(
            verbinding,
            start_datum,
            eind_datum
        )

        if not resultaat:
            return jsonify({
                "error": "Geen energiegegevens gevonden."
            }), 404

        return jsonify(resultaat)

    finally:
        verbinding.close()    

# ==============================================================
# API: BATTERIJ - DAG
# ==============================================================

@app.route("/api/batterij/dag/<datum>")
def api_batterij_dag(datum):

    config = laad_configuratie()

    if config is None:
        return jsonify({
            "error": "Configuratie kon niet worden geladen."
        }), 500

    auth = controleer_api_key(config)

    if auth is None:
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
# API: BATTERIJ - PERIODE
# ==============================================================

@app.route("/api/batterij/periode/<start_datum>/<eind_datum>")
def api_batterij_periode(start_datum, eind_datum):

    config = laad_configuratie()

    if config is None:
        return jsonify({
            "error": "Configuratie kon niet worden geladen."
        }), 500

    auth = controleer_api_key(config)

    if auth is None:
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

# ==============================================================
# API: BATTERIJ - PER DAG
# ==============================================================

@app.route("/api/batterij/perdag/<start_datum>/<eind_datum>")
def api_batterij_per_dag(start_datum, eind_datum):

    config = laad_configuratie()

    if config is None:
        return jsonify({
            "error": "Configuratie kon niet worden geladen."
        }), 500

    auth = controleer_api_key(config)

    if auth is None:
        return jsonify({
            "error": "Ongeldige of ontbrekende API-key."
        }), 401

    verbinding = maak_databaseverbinding(config)

    if verbinding is None:
        return jsonify({
            "error": "Databaseverbinding kon niet worden gemaakt."
        }), 500

    try:
        resultaat = batterij_per_dag(
            verbinding,
            start_datum,
            eind_datum
        )

        if not resultaat:
            return jsonify({
                "error": "Geen batterijgegevens gevonden."
            }), 404

        return jsonify(resultaat)

    finally:
        verbinding.close()

# ==============================================================
# API: ENERGIE - ACTUEEL
# ==============================================================
@app.route("/api/energie/actueel")
def api_energie_actueel():

    config = laad_configuratie()

    if config is None:
        return jsonify({
            "error": "Configuratie kon niet worden geladen."
        }), 500

    auth = controleer_api_key(config)

    if auth is None:
        return jsonify({
            "error": "Ongeldige of ontbrekende API-key."
        }), 401

    verbinding = maak_databaseverbinding(config)

    if verbinding is None:
        return jsonify({
            "error": "Databaseverbinding kon niet worden gemaakt."
        }), 500

    try:
        resultaat = energie_actueel(verbinding)

        if resultaat is None:
            return jsonify({
                "error": "Geen actuele energiegegevens beschikbaar."
            }), 404
        
        return jsonify(resultaat)

    finally:
        verbinding.close() 

# ==============================================================
# API: BATTERIJ - ACTUEEL
# ==============================================================
@app.route("/api/batterij/actueel")
def api_batterij_actueel():

    config = laad_configuratie()

    if config is None:
        return jsonify({
            "error": "Configuratie kon niet worden geladen."
        }), 500

    auth = controleer_api_key(config)

    if auth is None:
        return jsonify({
            "error": "Ongeldige of ontbrekende API-key."
        }), 401

    verbinding = maak_databaseverbinding(config)

    if verbinding is None:
        return jsonify({
            "error": "Databaseverbinding kon niet worden gemaakt."
        }), 500

    try:
        resultaat = batterij_actueel(verbinding)

        if resultaat is None:
            return jsonify({
                "error": "Geen batterijgegevens beschikbaar."
            }), 404

        return jsonify(resultaat)

    finally:
        verbinding.close()

# ==============================================================
# INFO - API DOCUMENTATIE
# ==============================================================
@app.route("/api/info")
def api_info():

    html = """
        <!DOCTYPE html>
        <html lang="nl">

        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">

            <title>Energy API - Info</title>

            <style>

                * {
                    box-sizing: border-box;
                }

                body {
                    font-family: Arial, Helvetica, sans-serif;
                    margin: 0;
                    background: #eef3f7;
                    color: #263238;
                    line-height: 1.6;
                }


                /* ==================================================
                HEADER
                ================================================== */

                header {
                    background: linear-gradient(135deg, #00695c, #00897b);
                    color: white;
                    padding: 45px 20px;
                    text-align: center;
                    box-shadow: 0 3px 10px rgba(0,0,0,0.15);
                }

                header h1 {
                    margin: 0;
                    font-size: 42px;
                }

                header p {
                    margin: 10px 0 0 0;
                    font-size: 18px;
                    opacity: 0.95;
                }


                /* ==================================================
                HOOFDINHOUD
                ================================================== */

                .container {
                    max-width: 1050px;
                    margin: 35px auto;
                    padding: 0 20px;
                }

                .card {
                    background: white;
                    border-radius: 12px;
                    padding: 30px;
                    margin-bottom: 25px;
                    box-shadow: 0 3px 12px rgba(0,0,0,0.08);
                }


                /* ==================================================
                TITELS
                ================================================== */

                h2 {
                    color: #00695c;
                    margin-top: 0;
                    padding-bottom: 8px;
                    border-bottom: 2px solid #e0e0e0;
                }

                h3 {
                    color: #00796b;
                }


                /* ==================================================
                LIJSTEN
                ================================================== */

                li {
                    margin-bottom: 7px;
                }


                /* ==================================================
                CODE
                ================================================== */

                code {
                    background: #e8f5e9;
                    color: #00695c;
                    padding: 3px 7px;
                    border-radius: 5px;
                    font-family: Consolas, Monaco, monospace;
                }

                pre {
                    background: #263238;
                    color: #eeeeee;
                    padding: 18px;
                    border-radius: 8px;
                    overflow-x: auto;
                    font-family: Consolas, Monaco, monospace;
                    font-size: 14px;
                    line-height: 1.5;
                    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.05);
                }


                /* ==================================================
                ENDPOINT TABEL
                ================================================== */

                .table-container {
                    overflow-x: auto;
                }

                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 15px;
                }

                th {
                    background: #00695c;
                    color: white;
                    padding: 13px 10px;
                    text-align: left;
                }

                td {
                    border-bottom: 1px solid #e0e0e0;
                    padding: 12px 10px;
                }

                tr:hover {
                    background: #f5f9f9;
                }


                /* ==================================================
                BADGES
                ================================================== */

                .badge {
                    display: inline-block;
                    padding: 4px 10px;
                    border-radius: 20px;
                    font-size: 13px;
                    font-weight: bold;
                }

                .get {
                    background: #e3f2fd;
                    color: #1565c0;
                }

                .openbaar {
                    background: #e8f5e9;
                    color: #2e7d32;
                }

                .beveiligd {
                    background: #ffebee;
                    color: #c62828;
                }


                /* ==================================================
                INFO BOX
                ================================================== */

                .info-box {
                    background: #e0f2f1;
                    border-left: 5px solid #00897b;
                    padding: 15px 20px;
                    border-radius: 6px;
                    margin: 20px 0;
                }

                .warning-box {
                    background: #fff8e1;
                    border-left: 5px solid #ffb300;
                    padding: 15px 20px;
                    border-radius: 6px;
                    margin: 20px 0;
                }


                /* ==================================================
                FOOTER
                ================================================== */

                footer {
                    text-align: center;
                    color: #607d8b;
                    padding: 20px;
                    margin-bottom: 30px;
                }


                /* ==================================================
                MOBIELE WEERGAVE
                ================================================== */

                @media (max-width: 700px) {

                    header h1 {
                        font-size: 32px;
                    }

                    header p {
                        font-size: 16px;
                    }

                    .card {
                        padding: 20px;
                    }

                    table {
                        font-size: 14px;
                    }

                    th, td {
                        padding: 8px;
                    }
                }

            </style>

        </head>


        <body>


            <!-- =====================================================
                HEADER
                ===================================================== -->

            <header>

                <h1>⚡ Energy API</h1>

                <p>
                    API voor energiegegevens van een SolarEdge-installatie
                </p>

            </header>



            <!-- =====================================================
                INHOUD
                ===================================================== -->

            <main class="container">


                <!-- INTRODUCTIE -->

                <section class="card">

                    <h2>Welkom</h2>

                    <p>
                        Welkom bij de Energy API.
                    </p>

                    <p>
                        Deze API geeft toegang tot gegevens van een
                        SolarEdge-energie-installatie.
                        De API werd ontwikkeld als onderdeel van een
                        lessenreeks voor 6TWE - Toegepaste elektriciteit en softwareontwikkeling.
                    </p>

                    <div class="info-box">

                        <strong>Doel van deze API</strong>

                        <p>
                            Leerlingen kunnen via HTTP-aanvragen
                            energiegegevens opvragen en deze verwerken
                            in hun eigen webapplicaties.
                        </p>

                    </div>

                </section>



                <!-- WAT KUN JE ERMEE -->

                <section class="card">

                    <h2>Wat kun je met deze API?</h2>

                    <p>
                        Via de API kunnen webapplicaties informatie
                        opvragen over onder andere:
                    </p>

                    <ul>

                        <li>☀️ energieproductie door zonnepanelen</li>

                        <li>🏠 energieverbruik</li>

                        <li>⚡ energie-injectie naar het elektriciteitsnet</li>

                        <li>🔌 energieafname van het elektriciteitsnet</li>

                        <li>🔋 de batterij</li>

                        <li>🔄 het laden en ontladen van de batterij</li>

                        <li>📊 het actuele vermogen</li>

                    </ul>

                </section>



                <!-- HOE WERKT API -->

                <section class="card">

                    <h2>Hoe werkt de API?</h2>

                    <p>
                        Een API werkt volgens het HTTP-protocol.
                        Een applicatie stuurt een HTTP-request naar een
                        bepaald endpoint.
                        De server verwerkt de aanvraag en stuurt een
                        response terug.
                    </p>

                    <p>
                        De meeste endpoints van deze API geven de gegevens
                        terug in het formaat <strong>JSON</strong>.
                    </p>

                    <p>
                        Bijvoorbeeld:
                    </p>

                    <pre>GET /api/energie/dag/2026-08-07</pre>

                </section>



                <!-- ENDPOINTS -->

                <section class="card">

                    <h2>Beschikbare endpoints</h2>

                    <div class="table-container">

                        <table>

                            <tr>

                                <th>Methode</th>

                                <th>Endpoint</th>

                                <th>Beschrijving</th>

                                <th>API-key</th>

                            </tr>


                            <tr>

                                <td>
                                    <span class="badge get">GET</span>
                                </td>

                                <td>
                                    <code>/api/info</code>
                                </td>

                                <td>
                                    Deze informatiepagina
                                </td>

                                <td>
                                    <span class="badge openbaar">
                                        Nee
                                    </span>
                                </td>

                            </tr>


                            <tr>

                                <td>
                                    <span class="badge get">GET</span>
                                </td>

                                <td>
                                    <code>/api/energie/dag/&lt;datum&gt;</code>
                                </td>

                                <td>
                                    Energiegegevens van één dag
                                </td>

                                <td>
                                    <span class="badge beveiligd">
                                        Ja
                                    </span>
                                </td>

                            </tr>


                            <tr>

                                <td>
                                    <span class="badge get">GET</span>
                                </td>

                                <td>
                                    <code>
                                        /api/energie/periode/&lt;start&gt;/&lt;einde&gt;
                                    </code>
                                </td>

                                <td>
                                    Energiegegevens van een periode
                                </td>

                                <td>
                                    <span class="badge beveiligd">
                                        Ja
                                    </span>
                                </td>

                            </tr>

                            <tr>

                                <td>
                                    <span class="badge get">GET</span>
                                </td>

                                <td>
                                    <code>
                                        /api/energie/perdag/&lt;start&gt;/&lt;einde&gt;
                                    </code>
                                </td>

                                <td>
                                    Energiegegevens per dag binnen een periode
                                </td>

                                <td>
                                    <span class="badge beveiligd">
                                        Ja
                                    </span>
                                </td>

                            </tr>


                            <tr>

                                <td>
                                    <span class="badge get">GET</span>
                                </td>

                                <td>
                                    <code>/api/energie/actueel</code>
                                </td>

                                <td>
                                    Actuele energiegegevens
                                </td>

                                <td>
                                    <span class="badge beveiligd">
                                        Ja
                                    </span>
                                </td>

                            </tr>


                            <tr>

                                <td>
                                    <span class="badge get">GET</span>
                                </td>

                                <td>
                                    <code>/api/batterij/dag/&lt;datum&gt;</code>
                                </td>

                                <td>
                                    Batterijgegevens van één dag
                                </td>

                                <td>
                                    <span class="badge beveiligd">
                                        Ja
                                    </span>
                                </td>

                            </tr>


                            <tr>

                                <td>
                                    <span class="badge get">GET</span>
                                </td>

                                <td>
                                    <code>
                                        /api/batterij/periode/&lt;start&gt;/&lt;einde&gt;
                                    </code>
                                </td>

                                <td>
                                    Batterijgegevens van een periode
                                </td>

                                <td>
                                    <span class="badge beveiligd">
                                        Ja
                                    </span>
                                </td>

                            </tr>

                            <tr>

                                <td>
                                    <span class="badge get">GET</span>
                                </td>

                                <td>
                                    <code>
                                        /api/batterij/perdag/&lt;start&gt;/&lt;einde&gt;
                                    </code>
                                </td>

                                <td>
                                    Batterijgegevens per dag binnen een periode
                                </td>

                                <td>
                                    <span class="badge beveiligd">
                                        Ja
                                    </span>
                                </td>

                            </tr>

                            <tr>

                                <td>
                                    <span class="badge get">GET</span>
                                </td>

                                <td>
                                    <code>/api/batterij/actueel</code>
                                </td>

                                <td>
                                    Actuele batterijgegevens
                                </td>

                                <td>
                                    <span class="badge beveiligd">
                                        Ja
                                    </span>
                                </td>

                            </tr>

                        </table>

                    </div>

                </section>



                <!-- API KEY -->

                <section class="card">

                    <h2>🔐 API-key</h2>

                    <p>
                        De endpoints die echte energiegegevens teruggeven
                        zijn beveiligd met een API-key.
                    </p>

                    <p>
                        De API-key moet meegestuurd worden in de
                        HTTP-header:
                    </p>

                    <pre>X-API-Key: JOUW_API_KEY</pre>

                    <div class="info-box">

                        <strong>Goed om te weten</strong>

                        <p>
                            Het endpoint <code>/api/info</code> is openbaar.
                            Hiervoor is geen API-key nodig.
                        </p>

                    </div>

                </section>



                <!-- JAVASCRIPT -->

                <section class="card">

                    <h2>💻 Voorbeeld vanuit JavaScript</h2>

                    <p>
                        Een webpagina kan de API aanspreken met
                        <code>fetch()</code>.
                    </p>

                    <pre>const antwoord = await fetch(
        "http://192.168.0.35:5000/api/energie/dag/2026-08-07",
        {
            headers: {
                "X-API-Key": "JOUW_API_KEY"
            }
        }
    );

    const data = await antwoord.json();

    console.log(data);</pre>

                        <p>
                            De beveiligde API-endpoints kun je niet zomaar rechtstreeks
                            in de adresbalk van een browser gebruiken, omdat daarbij
                            de vereiste <code>X-API-Key</code> header ontbreekt.
                        </p>

                        <p>
                            Vanuit JavaScript kun je de API-key wel meesturen via
                            <code>fetch()</code>, zoals in bovenstaand voorbeeld.
                        </p>
        
                        <p>
                            De informatie die je terugkrijgt (in het voorbeeld een JSON-object in data), is niet versleuteld (http) en kan je in een programma verder gebruiken.
                        </p>
        
                        <p>
                            Je moet ook hier IP-adres:Poort van je API-server doorgeven vooraleer je de specifieke API kan oproepen
                        </p>

                </section>

                <!-- OPENBAAR -->

                <section class="card">

                    <h2>🌐 Voorbeeld zonder API-key</h2>

                    <p>
                        De informatiepagina kun je rechtstreeks openen
                        in een browser:
                    </p>

                    <p>
                        De informatie (deze pagina) die je terugkrijgt, is niet versleuteld (http). 
                    </p>

                    <p>
                        Je moet ook hier IP-adres:Poort van je API-server doorgeven vooraleer je de specifieke API kan oproepen
                    </p>

                    <pre>http://192.168.0.35:5000/api/info</pre>

                </section>



                <!-- LEERLINGEN -->

                <section class="card">

                    <h2>🎓 Voor leerlingen</h2>

                    <p>
                        Je kunt deze API gebruiken in je eigen
                        webapplicatie.
                        Bekijk eerst de informatie op deze pagina en
                        onderzoek daarna de verschillende endpoints.
                    </p>

                    <p>
                        Probeer vervolgens zelf een JavaScript-programma
                        te maken dat gegevens uit de API opvraagt en
                        op een webpagina toont.
                    </p>

                    <div class="warning-box">

                        <strong>Uitdaging</strong>

                        <p>
                            Kun jij een webpagina maken die de actuele
                            energiegegevens van de installatie toont?
                        </p>

                    </div>

                </section>


            </main>



            <!-- =====================================================
                FOOTER
                ===================================================== -->

            <footer>

                <strong>Energy API</strong><br>
                Don Bosco Haacht - F.Demonie, aug 26

            </footer>


        </body>

        </html>
        """
    return render_template_string(html)