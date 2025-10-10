from paho.mqtt import client as mqtt
import time
# for logger
from types import FrameType
from typing import cast
import datetime
import inspect

PROTOCOL_TIMEOUT_SHORT = 0.5
PROTOCOL_TIMEOUT = 5
PROTOCOL_TIMEOUT_LONG = 60
PROTOCOL_TIME_SHORT = 0
PROTOCOL_TIME = 0
PROTOCOL_TIME_LONG = 0


def setpts():
    global PROTOCOL_TIME_SHORT
    PROTOCOL_TIME_SHORT = time.time() + PROTOCOL_TIMEOUT_SHORT


def setpt():
    global PROTOCOL_TIME
    PROTOCOL_TIME = time.time() + PROTOCOL_TIMEOUT


def setptl():
    global PROTOCOL_TIME_LONG
    PROTOCOL_TIME_LONG = time.time() + PROTOCOL_TIMEOUT_LONG


ping_table = []
ping_table_long = []
ping_min = 9999
ping_max = 0
ping_timeout = 2.5  # in seconds

broker = "192.168.0.106"
port = 1883
configreqtopic = "test/config/request"
configrepltopic = "test/config/reply"
devicetopic = "test/devices/#"
username = "mqttuser"
password = "mqtt"
client_id = "MqttControlServer1"
# mac add --- topic --- majd a tobbi
configtable = []

# még a pingekhez lehetne adni sorszámot, hogy tudjuk melyik pingre válaszol, mer most ha kimegy ketto ping de olyan lassan valszol h az elso timoutol de a masodik kikuldese utan jon vissza az elso akkor annak jo lesz a statja de igazabol az elsore valaszolt, majd ha nagyon belekavar akk megcsinalom
ping_tasks = []  # mac,numberofpings(forcountdown),numberofpings,pingstart,pingend,pingtimesum,succestimer,timoutcounter


class Logger2:
    def __init__(self):
        file = open("log2.txt", "w")
        file.close()
        file = open("console2.txt", "w")
        file.close()

    def console(self, info):  # print to console only
        wherefrom = cast(FrameType, cast(FrameType, inspect.currentframe()).f_back).f_code.co_name
        print(info)
        file = open("console2.txt", "a", encoding="utf-8")
        file.write(f"\n[Console] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
        file.close()

    def info(self, info):
        wherefrom = cast(FrameType, cast(FrameType, inspect.currentframe()).f_back).f_code.co_name
        print(info)
        file = open("log2.txt", "a", encoding="utf-8")
        file.write(f"\n[Info] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
        file.close()
        file = open("console2.txt", "a", encoding="utf-8")
        file.write(f"\n[Info] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
        file.close()

    def warning(self, info):
        wherefrom = cast(FrameType, cast(FrameType, inspect.currentframe()).f_back).f_code.co_name
        print(f"\n[Warning] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
        file = open("log2.txt", "a", encoding="utf-8")
        file.write(f"\n[Warning] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
        file.close()
        file = open("console2.txt", "a", encoding="utf-8")
        file.write(f"\n[Warning] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
        file.close()

    def error(self, info):
        wherefrom = cast(FrameType, cast(FrameType, inspect.currentframe()).f_back).f_code.co_name
        print(f"\n[Error] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
        file = open("log2.txt", "a", encoding="utf-8")
        file.write(f"\n[Error] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
        file.close()
        file = open("console2.txt", "a", encoding="utf-8")
        file.write(f"\n[Error] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
        file.close()


log = Logger2()

with open("configtable.txt", 'r', encoding='UTF-8') as cfile:
    linecount = 0  # sorok számozása
    while line := cfile.readline():
        linecount += 1  # sor szám +1
        tobedeleted = False  # alapra állít a sor törlése
        log.console(line.rstrip())
        if len(line.rstrip().split(",")) < 2:  # ha nincs vessző, szóval valami biztos hiányzik
            log.error("Config invalid, not enough arguments")
        else:
            configtable.append(line.rstrip().split(","))
            if len(configtable[-1]) == 2:  # ha nincs megadva pincofnig set it to none
                configtable[-1].append("None")
            if len(configtable[-1][2]) == 0:  # ha van vessző de nincs irva semmi a pincofig reszhez set it to none
                configtable[-1][2] = "None"
            if len(configtable[-1][0]) != 17:  # ha a mac cim nem 17 karakter hosszu
                log.error(f"Mac address length is too short in line {linecount} with argument {configtable[-1][0]}")
                tobedeleted = True
            else:
                if configtable[-1][0][2] == ":" and configtable[-1][0][5] == ":" and configtable[-1][0][8] == ":" and configtable[-1][0][11] == ":" and configtable[-1][0][14] == ":":  # ha kettospontal van elválasztva rakja át kotojelre
                    log.warning(f'Mac address format mismatch, converting ":" to "-" in {configtable[-1][0]} at line {linecount }')
                    configtable[-1][0] = configtable[-1][0].replace(":", "-")
                if configtable[-1][0].count("-") != 5:  # ha nem 5 darab separator van
                    log.error(f"Mac address segment separators count is incorrect in line {linecount} with argument {configtable[-1][0]}")
                    tobedeleted = True
                for i in range(1, 18):
                    if i % 3 == 0:
                        if configtable[-1][0][i-1] != "-":
                            log.error(f"Mac address segment separators are incorrect in line {linecount} with argument {configtable[-1][0]}")
                            tobedeleted = True
                            break
                    else:
                        if (configtable[-1][0][i-1] < '0' or configtable[-1][0][i-1] > '9') and (configtable[-1][0][i-1] < 'A' or configtable[-1][0][i-1] > 'F'):
                            log.error(f"Mac address contains non hex characters in line {linecount} with argument {configtable[-1][0]}")
                            tobedeleted = True
                            break

            log.console(configtable[-1])

        if tobedeleted:
            del configtable[-1]

log.console(configtable)


class ProtocolBook:
    protocollist = []  # protocollist=[protpointer, protname, type(short,normal,long)]
    protDict = {}

    def __init__(self):
        var = 1
        for protocol in dir(ProtocolBook):
            if "__" not in protocol and protocol != "protShort" and protocol != "protNorm" and protocol != "protLong" and protocol != "protocollist" and protocol != "protDict":
                attr = getattr(ProtocolBook, protocol)
                if protocol[-1] == "s":
                    self.protocollist.append(str(f"{var}*{protocol}*short").split("*"))
                    self.protDict[str(var)] = attr
                elif protocol[-1] == "n":
                    self.protocollist.append(str(f"{var}*{protocol}*normal").split("*"))
                    self.protDict[str(var)] = attr
                elif protocol[-1] == "l":
                    self.protocollist.append(str(f"{var}*{protocol}*long").split("*"))
                    self.protDict[str(var)] = attr
                else:
                    log.error(f"Unkown protocoltype defined in {protocol}")
            var += 1
        while True:  # get protocol ID
            nothingchanged = True
            for protocol in self.protDict:
                nothingchanged = True
                oldID = protocol
                if oldID[0] < 'A' or oldID[0] > 'Z':
                    ID = self.protDict[protocol](self, "getID")
                    self.protDict[ID] = self.protDict.pop(protocol)
                    for var in range(0, len(self.protocollist)):
                        if self.protocollist[var][0] == oldID:
                            self.protocollist[var][0] = ID
                    nothingchanged = False
                    break
            if nothingchanged:
                break

    def testn(self, command):
        if command == "getID":
            return "T2"
        print("test normal")

    def tests(self, command):
        if command == "getID":
            return "T1"
        print("test short")

    def testl(self, command):
        if command == "getID":
            return "T3"
        print("test long")

    def protShort(self):
        for i in range(0, len(self.protocollist)):
            if self.protocollist[i][2] == "short":
                log.console("Executes short protocols")
                self.protDict[self.protocollist[i][0]](self, "none")

    def protNorm(self):
        for i in range(0, len(self.protocollist)):
            if self.protocollist[i][2] == "normal":
                log.console("Executes normal protocols")
                self.protDict[self.protocollist[i][0]](self, "none")

    def protLong(self):
        for i in range(0, len(self.protocollist)):
            if self.protocollist[i][2] == "long":
                log.console("Executes long protocols")
                self.protDict[self.protocollist[i][0]](self, "none")


prot = ProtocolBook()

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
client.username_pw_set(username=username, password=password)

log.info("Trying to connect to server:")
while True:
    try:
        client.connect(broker, port)
    except Exception as e:
        log.error(f"Connection failed: {e}")
        continue
    log.info("Connection succesful")
    break
client.publish(configreqtopic, "testfromserver")


def extract_address(message):
    # print(message.split("'")[1])
    for i in range(0, len(message)-14):
        if message[i+2] == message[i+5] == message[i+8] == message[i+11] == message[i+14]:
            address = f"{message[i]}{message[i+1]}{message[i+2]}{message[i+3]}{message[i+4]}{message[i+5]}{message[i+6]}{message[i+7]}{message[i+8]}{message[i+9]}{message[i+10]}{message[i+11]}{message[i+12]}{message[i+13]}{message[i+14]}{message[i+15]}{message[i+16]}"
            return address


def get_device_config(address):
    for i in (0, len(configtable)-1):
        if address == configtable[i][0]:
            return configtable[i]


def send_config(address, config):
    message = f"{address},{config[1]}"
    client.publish(configrepltopic, message)
    log.info(f"Sent config to {message}")


def ping(address, numberofpings):  # ping start
    for i in range(0, len(ping_tasks)):
        if address == ping_tasks[i][0]:
            log.info(f"Address {address} already in ping que, skipping")
            return
    ping_tasks.append([address, numberofpings, numberofpings, 1, 0, 0, 0, 0])


def ping_end(address):
    ct = time.monotonic()
    for i in range(0, len(ping_tasks)):
        if address == ping_tasks[i][0]:
            ping_tasks[i][4] = ct


def on_message(client, userData, msg):
    log.console(f"Message ({msg.payload}) arrived from ({msg.topic})")
    if msg.topic == configreqtopic:
        device = extract_address(str(msg.payload))
        if device is None:
            log.warning("No device address provided, continuing")
        else:
            config = get_device_config(device)
            if config is None:
                log.warning(f"No device config available for {device}")
            else:
                send_config(device, config)

    if str(msg.payload) == "b'HERE'":
        for i in range(0, len(configtable)):
            if msg.topic == configtable[i][1]:
                device = configtable[i][0]
                log.info(f"Device {device} succesfully connected to own channel")
                client.publish(msg.topic, "channel change ack")

    if "b'ping ok'" == str(msg.payload):
        for i in range(0, len(configtable)):
            if configtable[i][1] == msg.topic:
                address = configtable[i][0]
                ping_end(address)

    if str(msg.payload) == "b'PRTCL_PINCONFIG:REQUEST'":  # pinconfig request ---#PRTCL_PINCONFIG:config
        for i in range(0, len(configtable)):
            if msg.topic == configtable[i][1]:
                client.publish(configtable[i][1], f"PRTCL_PINCONFIG:{configtable[i][2]}")

    if "PRTCL_READBACK:" in str(msg.payload):  # readback ---#PRTCL_READBACK:OK if ok ---#PRTCL_READBACK:NOPE if not good readback
        if "OK" not in str(msg.payload) and "NOPE" not in str(msg.payload):
            for i in range(0, len(configtable)):
                if msg.topic == configtable[i][1]:
                    if str(msg.payload).split(":")[1][:-1] == configtable[i][2]:
                        client.publish(configtable[i][1], "PRTCL_READBACK:OK")
                    else:
                        client.publish(configtable[i][1], "PRTCL_READBACK:NOPE")


client.subscribe(configreqtopic)
client.subscribe(devicetopic)
client.on_message = on_message
client.loop_start()

while True:  # loop

    if PROTOCOL_TIME_SHORT < time.time():  # protocol long
        setpts()
        prot.protShort()
    if PROTOCOL_TIME < time.time():  # protocol
        setpt()
        prot.protNorm()
    if PROTOCOL_TIME_LONG < time.time():  # protocol long
        setptl()
        prot.protLong()
# *****************************************************************************************************************************************************************************************************************
    if len(ping_tasks) != 0:  # pingelés func
        for i in reversed(range(0, len(ping_tasks))):  # törlés és kiiras
            if ping_tasks[i][6] + ping_tasks[i][7] == ping_tasks[i][2]:  # kiiras
                if ping_tasks[i][6] == 0:  # nem volt válaszolt ping
                    log.warning(f"\nPing failed: {ping_tasks[i][6]} success, {ping_tasks[i][7]} failed out of {ping_tasks[i][2]}\n")
                if ping_tasks[i][6] != 0:  # volt valaszolt ping
                    log.info(f"\nPing results: {ping_tasks[i][6]} success, {ping_tasks[i][7]} failed out of {ping_tasks[i][2]}\nAvarage time was {ping_tasks[i][5]/ping_tasks[i][6]}\n\n")
                ping_tasks.pop(i)  # torles
        for i in range(0, len(ping_tasks)):  # pingtimecalc
            if ping_tasks[i][3] < ping_tasks[i][4]:  # ha pingstart hamarabb volt mint pingend
                pingtime = ping_tasks[i][4] - ping_tasks[i][3]  # calc pingtime
                if pingtime < ping_timeout:  # ha nem timoutolt
                    log.console(pingtime)
                    ping_tasks[i][5] = ping_tasks[i][5] + pingtime  # add to pingtimesum
                    ping_tasks[i][6] += 1  # increase succescounter by 1
                else:
                    log.info(f"{ping_tasks[i][0]} lassan valaszolt: {pingtime} seconds")
                    ping_tasks[i][7] += 1  # add one to timeout

            if ping_tasks[i][3] > ping_tasks[i][4] and ping_tasks[i][3] + ping_timeout < time.monotonic() and ping_tasks[i][3] != 1:  # nem jött válasz timout (ha pingtart nagyobb mint pingend (elozobol) ÉS pingstart + timout kevesebb mint mostani ido ÉS nem kezdőállapot
                ping_tasks[i][7] += 1  # add one to timout
        for i in range(0, len(ping_tasks)):  # send ping
            if (ping_tasks[i][3] < ping_tasks[i][4] and ping_tasks[i][4] - ping_tasks[i][3] < ping_timeout) or (ping_tasks[i][3] > ping_tasks[i][4] and ping_tasks[i][3] + ping_timeout < time.monotonic()):  # ha lepingelt vagy timoutolt
                for j in range(0, len(configtable)):
                    if ping_tasks[i][0] == configtable[j][0]:
                        topic = configtable[j][1]
                log.console(ping_tasks)
                client.publish(topic, "ping")
                ping_tasks[i][3] = time.monotonic()
                ping_tasks[i][1] -= 1
        time.sleep(0.25)
# *****************************************************************************************************************************************************************************************************************

# client.loop_stop()
