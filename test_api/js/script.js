// ============================================================
// Test Script om API calls te testen
//
// F.Demonie 11/08/26 - Initial release
// ============================================================


// ============================================================ 
// Algemene API-aanroep 
// ============================================================ 
async function apiAanroepen(url) { 
    const response = await fetch( 
        url, 
        { 
            headers: { 
                "X-API-Key": API_KEY 
            } 
        } 
    ); 
    
    const data = await response.json(); 

    if (!response.ok) { 
        throw new Error( 
            data.error || `HTTP-fout ${response.status}` 
        ); 
    } 

    return data; 
}

// ============================================================
// EENRGIE - DAG
// ============================================================
async function haalEnergieDagOp() {
    const datum = document.getElementById("datum").value;

    try {
        const data = await apiAanroepen(
            `http://${IP_ADDRESS}:5000/api/energie/dag/${datum}`
        );

        document.getElementById("energieDagData").textContent =
            JSON.stringify(data, null, 2);
    } catch ( fout ) {
        document.getElementById("energieDagData").textContent = 
            "Fout: " + fout.message;
    }
}

// ============================================================
// ENERGIE - PERIODE
// ============================================================
async function haalEnergiePeriodeOp() {
    const startDatum = document.getElementById("startDatum").value;
    const eindDatum = document.getElementById("eindDatum").value;

    try {
        const data = await apiAanroepen(
            `http://${IP_ADDRESS}:5000/api/energie/periode/${startDatum}/${eindDatum}`
        );
        
        document.getElementById("energiePeriodeData").textContent =
            JSON.stringify(data, null, 2);
    } catch ( fout ) {
        document.getElementById("energiePeriodeData").textContent = 
            "Fout: " + fout.message;
    }
}

// ============================================================
// BATTERIJ - DAG
// ============================================================
async function haalBatterijDagOp() {
    const datum = document.getElementById("datum").value;

    try {
        const data = await apiAanroepen(
            `http://${IP_ADDRESS}:5000/api/batterij/dag/${datum}`
        );

        document.getElementById("batterijDagData").textContent =
            JSON.stringify(data, null, 2);
    } catch ( fout ) {
        document.getElementById("batterijDagData").textContent = 
            "Fout: " + fout.message;
    }
}

// ============================================================
// BATTERIJ - PERIODE
// ============================================================
async function haalBatterijPeriodeOp() {
    const startDatum = document.getElementById("startDatum").value;
    const eindDatum = document.getElementById("eindDatum").value;

    try {
        const data = await apiAanroepen(
            `http://${IP_ADDRESS}:5000/api/batterij/periode/${startDatum}/${eindDatum}`
        );
        
        document.getElementById("batterijPeriodeData").textContent =
            JSON.stringify(data, null, 2);
    } catch ( fout ) {
        document.getElementById("batterijPeriodeData").textContent = 
            "Fout: " + fout.message;
    }
}