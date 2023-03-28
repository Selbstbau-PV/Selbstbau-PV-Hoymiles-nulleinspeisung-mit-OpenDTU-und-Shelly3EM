import requests, time
from requests.auth import HTTPBasicAuth

# Diese Daten müssen angepasst werden: zeile 5 - 12
serial = "112100000000" # Seriennummern der Hoymiles Wechselrichter
maximum_wr = 300 # Maximum ausgabe des wechselrichters

dtuIP = '192.100.100.20' # IP Adresse von OpenDTU
dtuNutzer = 'admin' # OpenDTU Nutzername
dtuPasswort = 'openDTU42' # OpenDTU Passwort

shellyIP = '192.100.100.30' #IP Adresse von Shelly 3EM


while True:
    # Nimmt Daten von der openDTU Rest-API und übersetzt sie in ein json-Format
    r = requests.get(url = f'http://{dtuIP}/api/livedata/status/inverters' ).json()

    # Selektiert spezifische Daten aus der json response
    reachable   = r['inverters'][0]['reachable'] # ist DTU erreichbar ?
    producing   = int(r['inverters'][0]['producing']) # produziert der Wechselrichter etwas ?
    altes_limit = int(r['inverters'][0]['limit_absolute']) # wo war das alte Limit gesetzt
    power_dc    = r['inverters'][0]['AC']['0']['Power DC']['v']  # Lieferung DC vom Panel
    power       = r['inverters'][0]['AC']['0']['Power']['v'] # Abgabe BKW AC in Watt

    # Nimmt Daten von der Shelly 3EM Rest-API und übersetzt sie in ein json-Format
    phaseA      = requests.get(f'http://{shellyIP}/emeter/0', headers={"Content-Type": "application/json"}).json()['power']
    phaseB      = requests.get(f'http://{shellyIP}/emeter/1', headers={"Content-Type": "application/json"}).json()['power']
    phaseC      = requests.get(f'http://{shellyIP}/emeter/2', headers={"Content-Type": "application/json"}).json()['power']
    grid_sum    = phaseA + phaseB + phaseC # Aktueller Bezug im Chalet - rechnet alle Phasen zusammen
    setpoint    = 0     # Neues Limit in Watt

    # Setzt ein limit auf das Wechselrichter
    def setLimit(Serial, Limit):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        payload = f'''data={{"serial":"{Serial}", "limit_type":1, "limit_value":{Limit}}}'''
        newLimit = requests.post(url=f'http://{dtuIP}/api/limit/config', data=payload, auth=HTTPBasicAuth(dtuNutzer, dtuPasswort), headers=headers)
        print('Konfiguration Stauts:', newLimit.json()['type'])

    # Werte setzen
    print("aktueller Bezug - Haus:   ",grid_sum)
    if reachable:
        # Setzen Sie den Grenzwert auf den höchsten Wert, wenn er über dem zulässigen Höchstwert liegt.
        if (altes_limit >= maximum_wr or grid_sum >= maximum_wr or setpoint >= maximum_wr):
            print("setze Limiter auf maximum")
            setpoint = maximum_wr

        # wir weniger bezogen als maximum_wr dann neues Limit ausrechnen
        if (grid_sum+altes_limit) <= maximum_wr:
            setpoint = grid_sum + altes_limit - 5
            print("setpoint:",grid_sum,"+",altes_limit,"-5 ")
            print("neues Limit berechnet auf ",setpoint)
        if setpoint <= 100:
            setpoint = 100
            print("setpoint: 100 minimum gesetzt")
            print("neues Limit festgelegt auf ",setpoint)

        print("setze Einspeiselimit auf: ",setpoint)
        # neues limit setzen
        setLimit(serial, setpoint)
        print("Solarzellenstrom:",power,"  Setpoint:",setpoint)

        time.sleep(5) # wait

    # Wenn der Wechselrichter nicht erreicht werden kann, wird der limit auf maximum gestellt
    if setpoint == 0: setpoint = grid_sum
    if not reachable: setpoint = maximum_wr
