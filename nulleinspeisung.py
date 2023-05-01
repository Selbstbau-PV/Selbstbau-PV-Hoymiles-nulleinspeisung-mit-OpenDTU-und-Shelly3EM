import requests, time
from requests.auth import HTTPBasicAuth


# Diese Daten müssen angepasst werden:
serial = "112100000000" # Seriennummer des Hoymiles Wechselrichters
maximum_wr = 300 # Maximale Ausgabe des Wechselrichters
minimum_wr = 100 # Minimale Ausgabe des Wechselrichters

dtu_ip = '192.100.100.20' # IP Adresse von OpenDTU
dtu_nutzer = 'admin' # OpenDTU Nutzername
dtu_passwort = 'openDTU42' # OpenDTU Passwort

shelly_ip = '192.100.100.30' # IP Adresse von Shelly 3EM


while True:
    try:
        # Nimmt Daten von der openDTU Rest-API und übersetzt sie in ein json-Format
        r = requests.get(url = f'http://{dtu_ip}/api/livedata/status/inverters' ).json()

        # Selektiert spezifische Daten aus der json response
        reachable   = r['inverters'][0]['reachable'] # Ist DTU erreichbar?
        producing   = int(r['inverters'][0]['producing']) # Produziert der Wechselrichter etwas?
        altes_limit = int(r['inverters'][0]['limit_absolute']) # Altes Limit
        power_dc    = r['inverters'][0]['AC']['0']['Power DC']['v']  # Lieferung DC vom Panel
        power       = r['inverters'][0]['AC']['0']['Power']['v'] # Abgabe BKW AC in Watt
    except:
        print('Fehler beim Abrufen der Daten von openDTU')
    try:
        # Nimmt Daten von der Shelly 3EM Rest-API und übersetzt sie in ein json-Format
        phase_a     = requests.get(f'http://{shelly_ip}/emeter/0', headers={'Content-Type': 'application/json'}).json()['power']
        phase_b     = requests.get(f'http://{shelly_ip}/emeter/1', headers={'Content-Type': 'application/json'}).json()['power']
        phase_c     = requests.get(f'http://{shelly_ip}/emeter/2', headers={'Content-Type': 'application/json'}).json()['power']
        grid_sum    = phase_a + phase_b + phase_c # Aktueller Bezug - rechnet alle Phasen zusammen
    except:
        print('Fehler beim Abrufen der Daten von Shelly 3EM')

    # Werte setzen
    print(f'\nBezug: {round(grid_sum, 1)} W, Produktion: {round(power, 1)} W, Verbrauch: {round(grid_sum + power, 1)} W')
    if reachable:
        setpoint = grid_sum + altes_limit - 5 # Neues Limit in Watt

        # Fange oberes Limit ab
        if setpoint > maximum_wr:
            setpoint = maximum_wr
            print(f'Setpoint auf Maximum: {maximum_wr} W')
        # Fange unteres Limit ab
        elif setpoint < minimum_wr:
            setpoint = minimum_wr
            print(f'Setpoint auf Minimum: {minimum_wr} W')
        else:
            print(f'Setpoint berechnet: {round(grid_sum, 1)} W + {round(altes_limit, 1)} W - 5 W = {round(setpoint, 1)} W')

        if setpoint != altes_limit:
            print(f'Setze Inverterlimit von {round(altes_limit, 1)} W auf {round(setpoint, 1)} W... ', end='')
            # Neues Limit setzen
            try:
                r = requests.post(
                    url = f'http://{dtu_ip}/api/limit/config',
                    data = f'data={{"serial":"{serial}", "limit_type":0, "limit_value":{setpoint}}}',
                    auth = HTTPBasicAuth(dtu_nutzer, dtu_passwort),
                    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                )
                print(f'Konfiguration gesendet ({r.json()["type"]})')
            except:
                print('Fehler beim Senden der Konfiguration')

    time.sleep(5) # wait
