from paho.mqtt import client as mqtt
import time

ping_table = []
ping_table_long = []
ping_min = 9999
ping_max = 0
ping_timeout = 2.5 #in seconds

broker = "192.168.0.106"
port = 1883
configreqtopic = "test/config/request"
configrepltopic = "test/config/reply"
devicetopic = "test/devices/#"
username = "mqttuser"
password = "mqtt"
client_id = "MqttControlServer1"
#mac add --- topic --- majd a tobbi
configtable = []
'''["14-D4-24-9C-FA-99", "test/devices/laptopwifi", 0, 0],
             ["AA-BB-CC-DD-EE-FF", "test/devices/doesntexist", 0, 0],
             ["3C-AB-72-96-52-F4", "test/devices/RP2040ETH_1", 0, 0]'''#a 0 a ping start, ping end

#még a pingekhez lehetne adni sorszámot, hogy tudjuk melyik pingre válaszol, mer most ha kimegy ketto ping de olyan lassan valszol h az elso timoutol de a masodik kikuldese utan jon vissza az elso akkor annak jo lesz a statja de igazabol az elsore valaszolt, majd ha nagyon belekavar akk megcsinalom
ping_tasks = [] ###mac,numberofpings(forcountdown),numberofpings,pingstart,pingend,pingtimesum,succestimer,timoutcounter


#az elejen kell emghatarozni a sor hosszat (elemszámra) nem kell dinamikusra mert egyseges hosszu kell legyen szal ha nem jo hosszusagu akkor mar ez egy fajta config ellenorzes h vmi hiba vana configba
with open("configtable.txt", 'r', encoding='UTF-8') as file:
    while line := file.readline():
        print(line.rstrip())
        configtable.append(line.rstrip().split(","))
        if len(configtable[-1]) == 2:
            configtable[-1].append("None")


print(configtable)

print(time.monotonic())

#mqtt.loop_start()

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
client.username_pw_set(username=username, password=password)
client.connect(broker, port)
client.publish(configreqtopic, "testfromserver")

def extract_address(message):
    #print(message.split("'")[1])
    for i in range(0 ,len(message)-14):
        #print(message[i])
        separator = message[i+2]
        if message[i+2] == message[i+5] == message[i+8] == message[i+11] == message[i+14]:
            address = f"{message[i]}{message[i+1]}{message[i+2]}{message[i+3]}{message[i+4]}{message[i+5]}{message[i+6]}{message[i+7]}{message[i+8]}{message[i+9]}{message[i+10]}{message[i+11]}{message[i+12]}{message[i+13]}{message[i+14]}{message[i+15]}{message[i+16]}"
            #print(f"address: {address}")
            return address

def get_device_config(address):
    #print(address)
    for i in (0, len(configtable)-1):
        if address == configtable[i][0]:
            return configtable[i]

def send_config(address, config):
    message = f"{address},{config[1]}"
    client.publish(configrepltopic, message)
    print(f"Sent config to {message}")

def ping(address, numberofpings): #ping start
    '''for i in range(0, len(configtable)): 
        if address == configtable[i][0]:
            topic = configtable[i][1]
    client.publish(topic, "ping")
    configtable[i][2] = time.monotonic()'''#ezt majd at lehet rakni a loopba
    ping_tasks.append([address, numberofpings, numberofpings, 1, 0, 0, 0, 0])

def ping_end(address):
    '''for i in range(0, len(configtable)):
        if address == configtable[i][0]:
            topic = configtable[i][1]
        pinglength = time.monotonic() - configtable[i][2]
        configtable[i][3] = pinglength
    print(configtable[i][3])'''
    ct = time.monotonic()
    for i in range(0, len(ping_tasks)):
        if address == ping_tasks[i][0]:
            ping_tasks[i][4] = ct

def on_message(client, userData, msg):
    print(f"Message ({msg.payload}) arrived from ({msg.topic})")
    if msg.topic == configreqtopic:
        device = extract_address(str(msg.payload))
        #print(f"device: {device}")
        if device == None:
            print("No device address provided, continuing")
        else:
            config = get_device_config(device)
            if config == None:
                print(f"No device config available for {device}")
            else:
                send_config(device, config)


    for i in range(0, len(configtable)):
        if msg.topic == configtable[i][1]:
            if str(msg.payload) == "b'HERE'":
                device = configtable[i][0]
                print(f"Device {device} succesfully connected to own channel")
                client.publish(msg.topic, "channel change ack")

    if "b'ping ok'" == str(msg.payload):
        print("in pingok")
        #address = extract_address(msg.payload)
        for i in range(0, len(configtable)):
            #print("infor")
            if configtable[i][1] == msg.topic:
                address = configtable[i][0]
                ping_end(address)

    if str(msg.payload) == "b'PRTCL_PINCONFIG:REQUEST'": #pinconfig request
        #PRTCL_PINCONFIG:config
        for i in range(0, len(configtable)):
            if msg.topic == configtable[i][1]:
                client.publish(configtable[i][1], f"PRTCL_PINCONFIG:{configtable[i][2]}")


    if "PRTCL_READBACK:" in str(msg.payload): #readback
        #PRTCL_READBACK:OK if ok
        #PRTCL_READBACK:NOPE if not good readback
        if "OK" not in str(msg.payload) and "NOPE" not in str(msg.payload):
            for i in range(0, len(configtable)):
                if msg.topic == configtable[i][1]:
                    if str(msg.payload).split(":")[1][:-1] == configtable[i][2]:
                        client.publish(configtable[i][1], "PRTCL_READBACK:OK")
                    else:
                        client.publish(configtable[i][1], "PRTCL_READBACK:NOPE")

client.subscribe(configreqtopic)
client.subscribe(devicetopic)
#client.subscribe("test/config/#")

client.on_message = on_message

#client.loop_forever()
client.loop_start()

ping("3C-AB-72-96-52-F4", 16)
ping("AA-BB-CC-DD-EE-FF", 4)

while True: #loop

    if False: #og ping
        ping("3C-AB-72-96-52-F4")
        time.sleep(1)
        ping_table.append([configtable[2][3]])
        ping_table_long.append([configtable[2][3]])
        if len(ping_table) > 10:
            ping_table.pop(0)
        if len(ping_table_long) > 100:
            ping_table_long.pop(0)
        pingavarage = 0
        pingavaragelong = 0
        for i in range(0, len(ping_table)-1):
            pingavarage = pingavarage + ping_table[i][0]
        print(f"\nPing avarage ==> {pingavarage/len(ping_table)}")
        for i in range(0, len(ping_table_long)-1):
            pingavaragelong = pingavaragelong + ping_table_long[i][0]
        print(f"Ping avarage long term ==> {pingavaragelong/len(ping_table_long)}")
        if configtable[2][3] < ping_min and configtable[2][3] != 0:
            ping_min = configtable[2][3]
        if configtable[2][3] > ping_max:
            ping_max = configtable[2][3]
        print(f"Ping minimum: {ping_min}\nPing maximum: {ping_max}\n\n")
#*****************************************************************************************************************************************************************************************************************
    if len(ping_tasks) != 0: #pingelés func
        for i in reversed(range(0, len(ping_tasks))): #törlés és kiiras
            if ping_tasks[i][6] + ping_tasks[i][7] == ping_tasks[i][2]:#ping_tasks[i][1] == 0:
                #kiiras
                if ping_tasks[i][6] == 0: #nem volt válaszolt ping
                    print(f"\nPing failed: {ping_tasks[i][6]} success, {ping_tasks[i][7]} failed out of {ping_tasks[i][2]}\n")
                if ping_tasks[i][6] != 0: #volt valaszolt ping
                    print(f"\nPing results: {ping_tasks[i][6]} success, {ping_tasks[i][7]} failed out of {ping_tasks[i][2]}\nAvarage time was {ping_tasks[i][5]/ping_tasks[i][6]}\n\n")
                ping_tasks.pop(i) #torles
        for i in range(0, len(ping_tasks)):#pingtimecalc
            if ping_tasks[i][3] < ping_tasks[i][4]:#ha pingstart hamarabb volt mint pingend
                pingtime = ping_tasks[i][4] - ping_tasks[i][3] #calc pingtime
                if pingtime < ping_timeout: #ha nem timoutolt
                    print(pingtime)
                    ping_tasks[i][5] = ping_tasks[i][5] + pingtime #add to pingtimesum
                    ping_tasks[i][6] += 1 #increase succescounter by 1
                else:
                    print(f"{ping_tasks[i][0]} lassan valaszolt: {pingtime} seconds")
                    ping_tasks[i][7] += 1 #add one to timeout

            if ping_tasks[i][3] > ping_tasks[i][4] and ping_tasks[i][3] + ping_timeout < time.monotonic() and ping_tasks[i][3] != 1:#nem jött válasz timout (ha pingtart nagyobb mint pingend (elozobol) ÉS pingstart + timout kevesebb mint mostani ido ÉS nem kezdőállapot
                ping_tasks[i][7] += 1 #add one to timout
        for i in range(0, len(ping_tasks)):#send ping
            if (ping_tasks[i][3] < ping_tasks[i][4] and ping_tasks[i][4] - ping_tasks[i][3] < ping_timeout) or (ping_tasks[i][3] > ping_tasks[i][4] and ping_tasks[i][3] + ping_timeout < time.monotonic()): #ha lepingelt vagy timoutolt
                for j in range(0, len(configtable)):
                    if ping_tasks[i][0] == configtable[j][0]:
                        topic = configtable[j][1]
                print(ping_tasks)
                client.publish(topic, "ping")
                ping_tasks[i][3] = time.monotonic()
                ping_tasks[i][1] -= 1
        time.sleep(0.25)
#*****************************************************************************************************************************************************************************************************************

#client.loop_stop()

#{"msg": "14-D4-24-9C-FA-99"}
