# import setuptools.msvc  # nem tudom mi ez vagy hogy miert van itt
from paho.mqtt import client as mqtt
import time
# for logger
from types import FrameType
from typing import cast
import datetime
import inspect
import os
# for hass comm
from requests import get

SyncOnlyWhenOnTestServer = True  # csak akkor syneljen hassba ha a test serveren van ezt kulon en adtam meg majd el kell tavolitani, ONLY FOR DEVELOPMENT

PROTOCOL_TIMEOUT_SHORT = 0.5
PROTOCOL_TIMEOUT = 5
PROTOCOL_TIMEOUT_LONG = 60
PROTOCOL_TIME_SHORT = 0
PROTOCOL_TIME = 0
PROTOCOL_TIME_LONG = 0

TBCCONFLICTHANDLE = "error"  # options are "error"/"delete"
# hozza kell adni a device confighoz az ID-t amivel mqttre felcsatlakozi


def setpts():
    global PROTOCOL_TIME_SHORT
    PROTOCOL_TIME_SHORT = time.time() + PROTOCOL_TIMEOUT_SHORT


setpts()


def setpt():
    global PROTOCOL_TIME
    PROTOCOL_TIME = time.time() + PROTOCOL_TIMEOUT


setpt()


def setptl():
    global PROTOCOL_TIME_LONG
    PROTOCOL_TIME_LONG = time.time() + PROTOCOL_TIMEOUT_LONG


setptl()

ping_table = []
ping_table_long = []
ping_min = 9999
ping_max = 0
ping_timeout = 2.5  # in seconds

broker = "127.0.0.1"
port = 1883
configreqtopic = "test/config/request"
configrepltopic = "test/config/reply"
devicetopic = "test/devices/#"
username = ""
password = ""
client_id = "MQTTControlServer1"
# mac add --- topic --- majd a tobbi
configtable = []

HassAPIkey = ""
HassIP = ""
HaState = "OFF"

L3error_max_rep = 5
L3error_max_rep_within = 100
L3timeoutforwarning = 15
P2max_ping_storage = 25

# még a pingekhez lehetne adni sorszámot, hogy tudjuk melyik pingre válaszol, mer most ha kimegy ketto ping de olyan lassan valszol h az elso timoutol de a masodik kikuldese utan jon vissza az elso akkor annak jo lesz a statja de igazabol az elsore valaszolt, majd ha nagyon belekavar akk megcsinalom
ping_tasks = []  # mac,numberofpings(forcountdown),numberofpings,pingstart,pingend,pingtimesum,succestimer,timoutcounter


class Logger2:

    filename = ""
    filepath = f"{os.getcwd()}/logs/"

    def __init__(self):
        self.filename = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S').replace(" ", "_").replace(":", "_")
        # self.filename = os.path.join(f"{os.getcwd()}", "logs", f"{self.filename}")
        file = open(f"{self.filepath}{self.filename}_log2.txt", "w")
        file.close()
        file = open(f"{self.filepath}{self.filename}_console2.txt", "w")
        file.close()

    def console(self, info):  # print to console only
        wherefrom = cast(FrameType, cast(FrameType, inspect.currentframe()).f_back).f_code.co_name
        print(info)
        file = open(f"{self.filepath}{self.filename}_console2.txt", "a", encoding="utf-8")
        file.write(f"\n[Console] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
        file.close()

    def info(self, info):
        wherefrom = cast(FrameType, cast(FrameType, inspect.currentframe()).f_back).f_code.co_name
        print(info)
        file = open(f"{self.filepath}{self.filename}_log2.txt", "a", encoding="utf-8")
        file.write(f"\n[Info] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
        file.close()
        file = open(f"{self.filepath}{self.filename}_console2.txt", "a", encoding="utf-8")
        file.write(f"\n[Info] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
        file.close()

    def warning(self, info):
        wherefrom = cast(FrameType, cast(FrameType, inspect.currentframe()).f_back).f_code.co_name
        print(f"\n[Warning] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
        file = open(f"{self.filepath}{self.filename}_log2.txt", "a", encoding="utf-8")
        file.write(f"\n[Warning] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
        file.close()
        file = open(f"{self.filepath}{self.filename}_console2.txt", "a", encoding="utf-8")
        file.write(f"\n[Warning] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
        file.close()

    def error(self, info):
        wherefrom = cast(FrameType, cast(FrameType, inspect.currentframe()).f_back).f_code.co_name
        print(f"\n[Error] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
        file = open(f"{self.filepath}{self.filename}_log2.txt", "a", encoding="utf-8")
        file.write(f"\n[Error] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
        file.close()
        file = open(f"{self.filepath}{self.filename}_console2.txt", "a", encoding="utf-8")
        file.write(f"\n[Error] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
        file.close()


class Logger3:

    timeoutforwarning = 15  # minutes within the same warning cant be sent
    # ammounttimeout = 25  # within last ammount cant be repeated #CURRENTLY NOT USED
    # errors are all excluded from this ruling
    error_max_rep = 5
    error_max_rep_within = 100
    error_list = []

    timeoutlist = []

    filename = ""
    filepath = f"{os.getcwd()}/logs/"
    datetime.datetime.now() - datetime.timedelta(minutes=timeoutforwarning)

    def __init__(self):
        global L3timeoutforwarning
        global L3error_max_rep_within
        global L3error_max_rep
        self.timeoutforwarning = L3timeoutforwarning
        self.error_max_rep = L3error_max_rep
        self.error_max_rep_within = L3error_max_rep_within
        self.filename = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S').replace(" ", "_").replace(":", "_")
        # self.filename = os.path.join(f"{os.getcwd()}", "logs", f"{self.filename}")
        file = open(f"{self.filepath}{self.filename}_log3.txt", "w")
        file.close()
        file = open(f"{self.filepath}{self.filename}_console3.txt", "w")
        file.close()
        self.info("Started Logger3...")

    def console(self, info):  # print to console only
        wherefrom = cast(FrameType, cast(FrameType, inspect.currentframe()).f_back).f_code.co_name
        print(info)
        file = open(f"{self.filepath}{self.filename}_console3.txt", "a", encoding="utf-8")
        file.write(f"\n[Console] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
        file.close()

    def info(self, info):
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        wherefrom = cast(FrameType, cast(FrameType, inspect.currentframe()).f_back).f_code.co_name
        print(info)
        file = open(f"{self.filepath}{self.filename}_log3.txt", "a", encoding="utf-8")
        file.write(f"\n[Info] [{timestamp}]: {info} FROM {wherefrom}")
        file.close()
        file = open(f"{self.filepath}{self.filename}_console3.txt", "a", encoding="utf-8")
        file.write(f"\n[Info] [{timestamp}]: {info} FROM {wherefrom}")
        file.close()

    def warning(self, info):
        # ---- LOGIC TO NOT SEND MULTIPLES WITHIN TIME ---- #
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        wherefrom = cast(FrameType, cast(FrameType, inspect.currentframe()).f_back).f_code.co_name
        w = 0
        while w < len(self.timeoutlist):
            if self.timeoutlist[w][0] <= datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'):
                self.timeoutlist.remove(self.timeoutlist[w])
            w += 1
        isalreadyin = False
        for line in self.timeoutlist:
            if f"[Warning]: {info} FROM {wherefrom}" == line[1]:
                isalreadyin = True
        # ---- END OF LOGIC TO NOT SEND MULTIPLES WITHIN TIME ---- #
        if isalreadyin is False:
            print(f"\n[Warning] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
            file = open(f"{self.filepath}{self.filename}_log3.txt", "a", encoding="utf-8")
            file.write(f"\n[Warning] [{timestamp}]: {info} FROM {wherefrom}")
            file.close()
            self.timeoutlist.append(f"{datetime.datetime.now() + datetime.timedelta(minutes=self.timeoutforwarning)}*[Warning]: {info} FROM {wherefrom}".split("*"))
            file = open(f"{self.filepath}{self.filename}_console3.txt", "a", encoding="utf-8")
            file.write(f"\n[Warning] [{timestamp}]: {info} FROM {wherefrom}")
            file.close()

    def error(self, info):
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        wherefrom = cast(FrameType, cast(FrameType, inspect.currentframe()).f_back).f_code.co_name

        # ---- START OF LOGIC TO NOT SEND MULTIPLES WITHIN LAST X ---- #
        self.error_list.append(f"[Error]: {info} FROM {wherefrom}")
        while len(self.error_list) > self.error_max_rep_within:
            self.error_list.pop(0)
        count = 0
        for line in self.error_list:
            if f"[Error]: {info} FROM {wherefrom}" == line:
                count += 1
        # ---- END OF LOGIC TO NOT SEND MULTIPLES WITHIN LAST X ---- #
        if count < self.error_max_rep + 1:
            print(f"\n[Error] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
            file = open(f"{self.filepath}{self.filename}_log3.txt", "a", encoding="utf-8")
            file.write(f"\n[Error] [{timestamp}]: {info} FROM {wherefrom}")
            file.close()
            file = open(f"{self.filepath}{self.filename}_console3.txt", "a", encoding="utf-8")
            file.write(f"\n[Error] [{timestamp}]: {info} FROM {wherefrom}")
            file.close()


log = Logger3()

log.info("Loading server configuration...")
with open("CONFIGURATION.txt", "a+", encoding='UTF-8') as configfile:
    configfile.seek(0)
    linecount = 0  # sorok számozása
    while line := configfile.readline():
        linecount += 1  # sor szám +1
        linecontent = line.rstrip().split(" #")[0].replace(" ", "").replace(",", "").replace('"', "")
        if linecontent[0] != "#":
            log.console(linecontent)
            if linecontent.split("=")[0] == "PROTOCOL_TIMEOUT":
                PROTOCOL_TIMEOUT = int(linecontent.split("=")[1])
            elif linecontent.split("=")[0] == "PROTOCOL_TIMEOUT_SHORT":
                PROTOCOL_TIMEOUT_SHORT = int(linecontent.split("=")[1])
            elif linecontent.split("=")[0] == "PROTOCOL_TIMEOUT_LONG":
                PROTOCOL_TIMEOUT_LONG = int(linecontent.split("=")[1])
            elif linecontent.split("=")[0] == "BROKER":
                broker = linecontent.split("=")[1]
            elif linecontent.split("=")[0] == "PORT":
                port = int(linecontent.split("=")[1])
            elif linecontent.split("=")[0] == "CONFIGREQUEST":
                configreqtopic = linecontent.split("=")[1]
            elif linecontent.split("=")[0] == "CONFIGREPLY":
                configrepltopic = linecontent.split("=")[1]
            elif linecontent.split("=")[0] == "DEVICETOPIC":
                devicetopic = linecontent.split("=")[1]
            elif linecontent.split("=")[0] == "USERNAME":
                username = linecontent.split("=")[1]
            elif linecontent.split("=")[0] == "PASSWORD":
                password = linecontent.split("=")[1]
            elif linecontent.split("=")[0] == "CLIENT_ID":
                client_id = linecontent.split("=")[1]
            elif linecontent.split("=")[0] == "TBCCONFLICTHANDLE":
                TBCCONFLICTHANDLE = linecontent.split("=")[1]
            elif linecontent.split("=")[0] == "HAK":
                HassAPIkey = linecontent.split("=")[1]
            elif linecontent.split("=")[0] == "HASS":
                if linecontent.split("=")[1] == "BROKER":
                    HassIP = broker
                else:
                    HassIP = linecontent.split("=")[1]
            elif linecontent.split("=")[0] == "L3_EMR":
                L3error_max_rep = linecontent.split("=")[1]
            elif linecontent.split("=")[0] == "L3_EMRW":
                L3error_max_rep_within = linecontent.split("=")[1]
            elif linecontent.split("=")[0] == "L3_TOF":
                L3timeoutforwarning = linecontent.split("=")[1]
            elif linecontent.split("=")[0] == "P2_MPS":
                P2max_ping_storage = linecontent.split("=")[1]
            elif linecontent.split("=")[0] == "MQTTDISCOVERY":
                HaState = linecontent.split("=")[1]

            else:
                log.error(f"Unkown variable given in CONIGURATION.txt at line {linecount} in the form of {linecontent}")

if HassIP == "":
    HassIP = broker


log.info("Loading device configurations...")
with open("configtable.txt", 'a+', encoding='UTF-8') as cfile:  # a+: Read and append. Pointer at end. Creates file if it doesn't exist. was 'r' earlier
    cfile.seek(0)
    linecount = 0  # sorok számozása
    while line := cfile.readline():
        linecount += 1  # sor szám +1
        tobedeleted = False  # alapra állít a sor törlése
        log.console(line.rstrip())
        if len(line.rstrip().split(",")) < 2:  # ha nincs vessző, szóval valami biztos hiányzik
            log.error(f"Config invalid, not enough arguments in line {linecount}")
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
            nameshelp = []
            templine = ""
            tobereplaced = ""
            for sensor in configtable[-1][2].split("/"):
                if len(sensor.split("@")) > 2:
                    alreadyin = False
                    if len(sensor.split("(")) < 2:  # no domain
                        sensorname = sensor.split("@")[1]
                    elif len(sensor.split("(")) == 2:
                        sensorname = sensor.split("@")[1].split("(")[0]
                    for entry in nameshelp:
                        if entry == sensorname:
                            alreadyin = True
                    if alreadyin:  # old was if alreadyin == True de az True == True szoval igy egyzserubb
                        log.error(f"Sensor with name {sensorname} already exist, removing from pinconfig")
                        print(len(configtable[-1][2].split(f"/{sensor}")))
                        if len(configtable[-1][2].split(f"/{sensor}")) > 2:
                            templine = f'{configtable[-1][2].split(f"/{sensor}")[0]}/{sensor}{configtable[-1][2].split(f"/{sensor}")[1].replace(f"/{sensor}", "")}'
                        elif len(configtable[-1][2].split(f"/{sensor}")) < 3:
                            templine = configtable[-1][2].replace(f"/{sensor}", "")
                        configtable[-1][2] = templine
                    else:
                        nameshelp.append(sensorname)

            log.console(configtable[-1])

        if tobedeleted:
            del configtable[-1]

# ha configfileba van es tbcbe is akkor vagy error vagy vegye ki tbcbol
# readback of tbc and send error for them
log.console(configtable)


def tbcreadback():
    alreadyaddedlist = []
    configlsit = []
    inboth = []
    with open("tbc.txt", "r", encoding="UTF-8") as tobeconfigured:
        while line := tobeconfigured.readline():
            alreadyaddedlist.append(line.rstrip())
        tobeconfigured.close()
    for tbcvar in range(0, len(configtable)-1):
        configlsit.append(configtable[tbcvar][0])
    for tbcvar in range(0, len(alreadyaddedlist)):
        if alreadyaddedlist[tbcvar] in configlsit:
            inboth.append(alreadyaddedlist[tbcvar])

    if TBCCONFLICTHANDLE == "delete":
        newtbc = []
        for address in alreadyaddedlist:
            if address not in inboth:
                newtbc.append(address)
        with open("tbc.txt", "w", encoding="UTF-8") as tbcfile:
            for address in newtbc:
                tbcfile.write(f"\n{address}")
        log.info("Modified TBC file, removed already configured entries")

    elif TBCCONFLICTHANDLE == "error":
        log.error(f"The following mac addresses are added to the list for configuring, but are already configured:{inboth}")

    else:
        log.error("Unkown setting given for TBCCONFLICTHANDLE")


def tbc(mac_address):
    with open("tbc.txt", "a", encoding="UTF-8") as tobeconfigured:
        alreadyaddedlist = []
        while line := tobeconfigured.readline():
            alreadyaddedlist.append(line.rstrip())
        if mac_address in alreadyaddedlist:
            log.warning(f"Device with mac address {mac_address} is already in the to be configured list")
        else:
            tobeconfigured.write(f"\n{mac_address}")
        tobeconfigured.close()


class Ping2:
    ping_tasks2 = []  # mac,numberofpings(forcountdown),numberofpings,pingstart,pingend,pingtimesum,succestimer,timoutcounter, ID
    ping_results2 = []  # ID, result
    max_ping_storage = 25  # max ammount of ping results to store

    def __init__(self):
        log.info("ping2 initialised")
        global P2max_ping_storage
        self.max_ping_storage = P2max_ping_storage

    def pingstart(self, address, numberofpings):  # ping start
        isok = False
        ID = int(time.monotonic() % 999999)
        while isok is False:
            ID = int(time.monotonic() % 999999)
            isok = True
            for entry in self.ping_tasks2:
                if entry[8] == ID:
                    isok = False
        for pt in range(0, len(self.ping_tasks2)):
            if address == self.ping_tasks2[pt][0]:
                log.info(f"Address {address} already in ping que, skipping")
                return
        self.ping_tasks2.append([address, numberofpings, numberofpings, 1, 0, 0, 0, 0, ID])
        return ID

    def pingend(self, address):
        ct = time.monotonic()
        for pe in range(0, len(self.ping_tasks2)):
            if address == self.ping_tasks2[pe][0]:
                self.ping_tasks2[pe][4] = ct

    def ping_runtime(self):
        while len(self.ping_results2) > self.max_ping_storage:
            self.ping_results2.pop(0)
        if len(self.ping_tasks2) != 0:  # pingelés func
            for i in reversed(range(0, len(self.ping_tasks2))):  # törlés és kiiras
                if self.ping_tasks2[i][6] + self.ping_tasks2[i][7] == self.ping_tasks2[i][2]:  # kiiras
                    if self.ping_tasks2[i][6] == 0:  # nem volt válaszolt ping
                        log.warning(f"Ping failed: {self.ping_tasks2[i][6]} success, {self.ping_tasks2[i][7]} failed out of {self.ping_tasks2[i][2]}\n")
                        self.ping_results2.append(f"{self.ping_tasks2[i][8]}*Failed".split("*"))
                    if self.ping_tasks2[i][6] != 0:  # volt valaszolt ping
                        log.console(f"Ping results: {self.ping_tasks2[i][6]} success, {self.ping_tasks2[i][7]} failed out of {self.ping_tasks2[i][2]}\nAvarage time was {self.ping_tasks2[i][5]/self.ping_tasks2[i][6]}")
                        self.ping_results2.append(f"{self.ping_tasks2[i][8]}*Successful".split("*"))
                    self.ping_tasks2.pop(i)  # torles
            for i in range(0, len(self.ping_tasks2)):  # pingtimecalc
                if self.ping_tasks2[i][3] < self.ping_tasks2[i][4]:  # ha pingstart hamarabb volt mint pingend
                    pingtime = self.ping_tasks2[i][4] - self.ping_tasks2[i][3]  # calc pingtime
                    if pingtime < ping_timeout:  # ha nem timoutolt
                        log.console(pingtime)
                        self.ping_tasks2[i][5] = self.ping_tasks2[i][5] + pingtime  # add to pingtimesum
                        self.ping_tasks2[i][6] += 1  # increase succescounter by 1
                    else:
                        log.info(f"{self.ping_tasks2[i][0]} lassan valaszolt: {pingtime} seconds")
                        self.ping_tasks2[i][7] += 1  # add one to timeout

                if self.ping_tasks2[i][3] > self.ping_tasks2[i][4] and self.ping_tasks2[i][3] + ping_timeout < time.monotonic() and self.ping_tasks2[i][3] != 1:  # nem jött válasz timout (ha pingtart nagyobb mint pingend (elozobol) ÉS pingstart + timout kevesebb mint mostani ido ÉS nem kezdőállapot
                    self.ping_tasks2[i][7] += 1  # add one to timout
            for i in range(0, len(self.ping_tasks2)):  # send ping
                if (self.ping_tasks2[i][3] < self.ping_tasks2[i][4] and self.ping_tasks2[i][4] - self.ping_tasks2[i][3] < ping_timeout) or (self.ping_tasks2[i][3] > self.ping_tasks2[i][4] and self.ping_tasks2[i][3] + ping_timeout < time.monotonic()):  # ha lepingelt vagy timoutolt
                    for j in range(0, len(configtable)):
                        if self.ping_tasks2[i][0] == configtable[j][0]:
                            topic = configtable[j][1]
                    # log.console(self.ping_tasks2)
                    client.publish(topic, "ping")
                    self.ping_tasks2[i][3] = time.monotonic()
                    self.ping_tasks2[i][1] -= 1
            time.sleep(0.25)

    def get_result(self, pid):
        for entry in self.ping_results2:
            if entry[0] == pid:
                return entry[1]
        return None


log.info("Starting Ping2...")
p = Ping2()


class HASS:

    # discovery topic : homeassistant/domain(switch,sensor,stb)/id(mac?)/config
    # send json data to create and modify device
    # send empty to delete device

    #kesz egy passziv availability check, ha eszkoz probalja olvasni de nem sikerul az error mellet visszakuld egy uzit h not avaible, ezt kene kiboviteni egy actival h rakerdez a szerver es ugy megnezi mindegyik sensort esetleg

    #we also need a protocol (probably on device end) to check if the servers data is correct regarding the device
    # (pl old sw_version got init, but since then got updated and the server should know)
    #ezt bovitve egy olyan is kell hogy a supported hardware is klappol e (pl az rpn van supportolva az nfc olvaso, de itt meg nincs naki default data megadva akkor az kideruljon, mondjuk egy warning vagy error formajaban, just some self.check

    def JSONdispatch(self, params):
        if params[0] == "SENSOR":
            return self.returnSensorJSON(params[1], params[2], params[3], params[4], params[5], params[6], params[7])
        elif params[0] == "BINARY_SENSOR":
            return self.returnBinarySensorJSON(params[1], params[2], params[3], params[4], params[5], params[6])
        elif params[0] == "SWITCH":
            return self.returnSwitchJson(params[1], params[2], params[3], params[4], params[5], params[6])
        elif params[0] == "LIGHT":
            return self.returnLightJSON(params[1], params[2], params[3], params[4], params[5], params[6])

    def returnSensorJSON(self, name, unique_id, state_topic, unit_of_measurement, entity_category, icon, availability_topic):
        if icon == "ICON":
            icon = "mdi:leak"
        return(f'"icon":"{icon}","name":"{name}","unique_id":"{unique_id}","state_topic":"{state_topic}","unit_of_measurement":"{unit_of_measurement}","availability":' + '{' + f'"topic":"{availability_topic}"' + '}')  # entity categroyt ki kellett venni mert nem ment tole a discovery ("entity_category":"{entity_category}",)

    def returnLongDeviceJSON(self, name, identifier, manufacturer, model, sw_version, hw_version, configurl):
        return(f'"device":' + '{' + f'"name":"{name}","identifiers":["{identifier}"],"manufacturer":"{manufacturer}","model":"{model}","hw_version":"{hw_version}","sw_version":"{sw_version}"' + '}')   # config urlt ki kellett venni mert nem mukodott tole a discovery (,"configuration_url":"{configurl}")

    def returnBinarySensorJSON(self, name, unique_id, state_topic, entity_category, icon, availability_topic):  # platform has to be binary sensor
        if icon == "ICON":
            icon = "mdi:leak"
        return(f'"platform":"binary_sensor","icon":"{icon}","name":"{name}","unique_id":"{unique_id}","state_topic":"{state_topic}","availability":' + '{' + f'"topic":"{availability_topic}"' + '}')  # entity categroyt ki kellett venni mert nem ment tole a discovery ("entity_category":"{entity_category}",)

    def returnLightJSON(self, name, unique_id, state_topic, entity_category, icon, availability_topic):  # rgb not supported
        if icon == "ICON":
            icon = "mdi:lightbulb"
        return(f'"platform":"light","icon":"{icon}","name":"{name}","unique_id":"{unique_id}","state_topic":"{state_topic}","brightness_command_topic":"{state_topic}/brightness_command","brightness_state_topic":"{state_topic}/brightness_state","command_topic":"{state_topic}/command","availability":' + '{' + f'"topic":"{availability_topic}"' + '}')  # entity categroyt ki kellett venni mert nem ment tole a discovery ("entity_category":"{entity_category}",)

    def returnSwitchJson(self, name, unique_id, state_topic, entity_category, icon, availability_topic):
        if icon == "ICON":
            icon = "mdi:toggle-switch-variant"
        return(f'"platform":"switch","icon":"{icon}","name":"{name}","unique_id":"{unique_id}","state_topic":"{state_topic}","command_topic":"{state_topic}/command","availability":' + '{' + f'"topic":"{availability_topic}"' + '}')  # entity categroyt ki kellett venni mert nem ment tole a discovery ("entity_category":"{entity_category}",)

    # hassImportData per line: "ENTITY",NAME,UNIQUE_ID,STATE_TOPIC,UNIT_OF_MEASUREMENT,ENTITY_CATEGORY,ICON,AVAILABILITY_TOPIC          #uniqeIDba benne van a MAC
    # hassImprotData per line: "DEVICE",NAME,IDENTIFIER,MANUFACTURER,MODEL,SWVERSION,HWVERSION,CONFIGURL                                #name-be benne van a MAC
    loadedData = []

    devices = []
    entities = []

    hassDomains = ["SENSOR", "BINARY_SENSOR", "SWITCH", "LIGHT"]
    nonDefinedVars = ["UNIT_OF_MEASUREMENT", "ENTITY_CATEGORY", "ICON", "MANUFACTURER", "MODEL", "SWVERSION", "HWVERSION", "CONFIGURL",  "UNIQUE_ID", "STATE_TOPIC"]  # , "ENTITY" ki lett véve

    defaultDataByDomainList = [["SENSOR", "Sensor", "mdi:leak"],
                               ["BINARY_SENSOR", "Sensor", "mdi:toggle-switch"],
                               ["SWITCH", "Control", "mdi:toggle-switch-variant"],
                               ["LIGHT", "Control", "mdi:lightbulb"],
                               ["ENTITY", "unkown", "mdi:help-circle-outline"]]
    defautlUOMByType = [["DHT11", "Temperature", "Humidity", "°C", "%"],
                        ["DHT22", "Temperature", "Humidity", "°C", "%"],
                        ["BMP180", "Temperature", "Pressure", "°C", "Pa"],
                        ["BMP085", "Temperature", "Pressure", "°C", "Pa"],
                        ["BH1750", "Light", "Lux"],
                        ["Rotary", "Rotation", "idkRotation"],
                        ["AnalogRead", "ADC", "adc"],
                        ["DigitalRead", "Binary", "Bin"]]
    defaultIconByType = [["DHT11", "Temperature", "Humidity", "mdi:thermometer", "mdi:water-percent"],
                         ["DHT22", "Temperature", "Humidity", "mdi:thermometer", "mdi:water-percent"],
                         ["BMP180", "Temperature", "Pressure", "mdi:thermometer", "mdi:cloud"],
                         ["BMP085", "Temperature", "Pressure", "mdi:thermometer", "mdi:cloud"],
                         ["BH1750", "Light", "mdi:ceiling-light"],
                         ["Rotary", "Rotation", "mdi:axis-z-rotate-counterclockwise"],
                         ["AnalogRead", "ADC", "mdi:leak"],
                         ["DigitalRead", "Binary", "mdi:toggle-switch-variant"]]
    dualSensor = []
    dualSensorSimple = []

    def __init__(self):
        for entry in self.defautlUOMByType:
            if len(entry) > 3:
                self.dualSensor.append(entry)
                self.dualSensorSimple.append(entry[0])
        print("HASS init")
        with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
            log.console("Reading hassImportData file")
            dfile.seek(0)
            linecount = 0  # sorok számozása
            while line := dfile.readline():
                linecount += 1  # sor szám +1
                # log.console(line.rstrip())
                self.loadedData.append(line.rstrip().split(","))
        for entry in self.loadedData:
            if entry[0] == "DEVICE":
                self.devices.append(entry)
            elif entry[0] in self.hassDomains:
                self.entities.append(entry)
            elif entry[0] in "ENTITY":
                log.warning(f"No domain type defined for {entry}")
                self.entities.append(entry)
            else:
                log.error(f"Unkown domain type given in hassImportData in the form of {entry}")

    def reloadData(self):  # should create a backup of hassImportData before updateing so if the new one would corrupt, manual rollback would be possible
        self.loadedData = []
        self.devices = []
        self.entities = []
        print("HASS Reload")
        with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
            log.console("Reading hassImportData file again")
            dfile.seek(0)
            linecount = 0  # sorok számozása
            while line := dfile.readline():
                linecount += 1  # sor szám +1
                # log.console(line.rstrip())
                self.loadedData.append(line.rstrip().split(","))
        for entry in self.loadedData:
            if entry[0] == "DEVICE":
                self.devices.append(entry)
            elif entry[0] in self.hassDomains:
                self.entities.append(entry)
            elif entry[0] in "ENTITY":
                log.warning(f"No domain type defined for {entry}")
                self.entities.append(entry)
            else:
                log.error(f"Unkown domain type given in hassImportData in the form of {entry}")

    def kiirALL(self):
        file = open("hassImportData.txt", "w", encoding='UTF-8')
        file.close()
        for i in range(0, len(configtable)):
            mac = configtable[i][0]
            topic = configtable[i][1]
            entities = configtable[i][2].split("/")
            dataLine = f"DEVICE,MCASS_{mac},mcass{mac.lower()},MANUFACTURER,MODEL,SW_VERSION,HW_VERSION,CONFIGURL\n"
            with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
                dfile.write(dataLine)
            for entity in entities:
                if len(entity.split("@")) > 2:
                    try:
                        if entity.split('@')[1].split('(')[1][:-1].upper() == "SENSOR":  # ha a domain sensor
                            if entity.split('@')[0].split("(")[0] in self.dualSensorSimple:  # ha 2 erteket mero sensor
                                measurements = []
                                for sensor in self.dualSensor:
                                    if entity.split('@')[0] == sensor[0]:
                                        measurementsAmm = int((len(sensor)-1)/2)
                                        for j in range(0+1, measurementsAmm+1):  # ez itt i volt de volt mar egy i feljebb es igy is moóukdoott
                                            measurements.append(sensor[j])  # ez itt i volt de volt mar egy i feljebb es igy is moóukdoott
                                for name in measurements:
                                    dataLine = f"{entity.split('@')[1].split('(')[1][:-1].upper()},{entity.split('@')[1].split('(')[0]}_{name},mcass_{mac.lower()}_{entity.split('@')[1].split('(')[0]}_{name},MCASS/hass/{topic.split('/')[-1]}/{entity.split('@')[1].split('(')[0]}/{name},UNIT_OF_MEASUREMENT,ENTITY_CATEGORY,ICON,mcass/hass/{topic.split('/')[-1]}/{entity.split('@')[1].split('(')[0]}/available\n"
                                    with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
                                        dfile.write(dataLine)
                            else:  # ha simpla sensor
                                try:
                                    dataLine = f"{entity.split('@')[1].split('(')[1][:-1].upper()},{entity.split('@')[1].split('(')[0]},mcass_{mac.lower()}_{entity.split('@')[1].split('(')[0]},MCASS/hass/{topic.split('/')[-1]}/{entity.split('@')[1].split('(')[0]},UNIT_OF_MEASUREMENT,ENTITY_CATEGORY,ICON,mcass/hass/{topic.split('/')[-1]}/{entity.split('@')[1].split('(')[0]}/available\n"
                                except:
                                    dataLine = f"ENTITY,{entity.split('@')[1]},mcass_{mac.lower()}_{entity.split('@')[1]},MCASS/hass/{topic.split('/')[-1]}/{entity.split('@')[1]},UNIT_OF_MEASUREMENT,ENTITY_CATEGORY,ICON,mcass/hass/{topic.split('/')[-1]}/{entity.split('@')[1]}/available\n"
                                with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
                                    dfile.write(dataLine)
                        else:  # ha nem sensor a domain
                            try:
                                dataLine = f"{entity.split('@')[1].split('(')[1][:-1].upper()},{entity.split('@')[1].split('(')[0]},mcass_{mac.lower()}_{entity.split('@')[1].split('(')[0]},MCASS/hass/{topic.split('/')[-1]}/{entity.split('@')[1].split('(')[0]},ENTITY_CATEGORY,ICON,mcass/hass/{topic.split('/')[-1]}/{entity.split('@')[1].split('(')[0]}/available\n"
                            except:
                                dataLine = f"ENTITY,{entity.split('@')[1]},mcass_{mac.lower()}_{entity.split('@')[1]},MCASS/hass/{topic.split('/')[-1]}/{entity.split('@')[1]},ENTITY_CATEGORY,ICON,mcass/hass/{topic.split('/')[-1]}/{entity.split('@')[1]}/available\n"
                            with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
                                dfile.write(dataLine)
                    except:
                        if entity.split('@')[0] in self.dualSensorSimple:  # ha 2 erteket mero sensor akkor nem kell domain mert fix h sensor
                            measurements = []
                            for sensor in self.dualSensor:
                                if entity.split('@')[0] == sensor[0]:
                                    measurementsAmm = int((len(sensor)-1)/2)
                                    for j in range(0+1, measurementsAmm):  # ez itt i volt de volt mar egy i feljebb es igy is moóukdoott
                                        measurements.append(sensor[j])  # ez itt i volt de volt mar egy i feljebb es igy is moóukdoott
                            for name in measurements:
                                dataLine = f"{entity.split('@')[1].split('(')[1][:-1].upper()},{entity.split('@')[1].split('(')[0]}_{name},mcass_{mac.lower()}_{entity.split('@')[1].split('(')[0]}_{name},MCASS/hass/{topic.split('/')[-1]}/{entity.split('@')[1].split('(')[0]},UNIT_OF_MEASUREMENT,ENTITY_CATEGORY,ICON,mcass/hass/{topic.split('/')[-1]}/{entity.split('@')[1].split('(')[0]}/available\n"
                                with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
                                    dfile.write(dataLine)
                        else:  # ha nincs domain megadva es nem is 2 erteku sensor
                            dataLine = f"ENTITY,{entity.split('@')[1]},mcass_{mac.lower()}_{entity.split('@')[1]},MCASS/hass/{topic.split('/')[-1]}/{entity.split('@')[1]},ENTITY_CATEGORY,ICON,mcass/hass/{topic.split('/')[-1]}/{entity.split('@')[1]}/available\n"
                            with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
                                dfile.write(dataLine)
                else:
                    continue

    def kiirOnlyNew(self):
        loadedDataUNIQUEs = []
        for row in self.loadedData:
            loadedDataUNIQUEs.append(row[2])
        for i in range(0, len(configtable)):
            mac = configtable[i][0]
            topic = configtable[i][1]
            entities = configtable[i][2].split("/")
            dataLine = f"DEVICE,MCASS_{mac},mcass{mac.lower()},MANUFACTURER,MODEL,SW_VERSION,HW_VERSION,CONFIGURL\n"
            if dataLine.split(",")[2] in loadedDataUNIQUEs:
                print("")
            else:
                with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
                    dfile.write(dataLine)
            for entity in entities:
                if len(entity.split("@")) > 2:
                    try:
                        if entity.split('@')[1].split('(')[1][:-1].upper() == "SENSOR":  # ha a domain sensor
                            if entity.split('@')[0].split("(")[0] in self.dualSensorSimple:  # ha 2 erteket mero sensor
                                measurements = []
                                for sensor in self.dualSensor:
                                    if entity.split('@')[0] == sensor[0]:
                                        measurementsAmm = int((len(sensor)-1)/2)
                                        for j in range(0+1, measurementsAmm+1):  # ez itt i volt de volt mar egy i feljebb es igy is moóukdoott
                                            measurements.append(sensor[j])  # ez itt i volt de volt mar egy i feljebb es igy is moóukdoott
                                for name in measurements:
                                    dataLine = f"{entity.split('@')[1].split('(')[1][:-1].upper()},{entity.split('@')[1].split('(')[0]}_{name},mcass_{mac.lower()}_{entity.split('@')[1].split('(')[0]}_{name},MCASS/hass/{topic.split('/')[-1]}/{entity.split('@')[1].split('(')[0]}/{name},UNIT_OF_MEASUREMENT,ENTITY_CATEGORY,ICON,mcass/hass/{topic.split('/')[-1]}/{entity.split('@')[1].split('(')[0]}/available\n"
                                    if dataLine.split(",")[2] in loadedDataUNIQUEs:
                                        continue
                                    else:
                                        with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
                                            dfile.write(dataLine)
                            else:  # ha simpla sensor
                                try:
                                    dataLine = f"{entity.split('@')[1].split('(')[1][:-1].upper()},{entity.split('@')[1].split('(')[0]},mcass_{mac.lower()}_{entity.split('@')[1].split('(')[0]},MCASS/hass/{topic.split('/')[-1]}/{entity.split('@')[1].split('(')[0]},UNIT_OF_MEASUREMENT,ENTITY_CATEGORY,ICON,mcass/hass/{topic.split('/')[-1]}/{entity.split('@')[1].split('(')[0]}/available\n"
                                except:
                                    dataLine = f"ENTITY,{entity.split('@')[1]},mcass_{mac.lower()}_{entity.split('@')[1]},MCASS/hass/{topic.split('/')[-1]}/{entity.split('@')[1]},UNIT_OF_MEASUREMENT,ENTITY_CATEGORY,ICON,mcass/hass/{topic.split('/')[-1]}/{entity.split('@')[1]}/available\n"
                                if dataLine.split(",")[2] in loadedDataUNIQUEs:
                                    continue
                                else:
                                    with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
                                        dfile.write(dataLine)
                        else:  # ha nem sensor a domain
                            try:
                                dataLine = f"{entity.split('@')[1].split('(')[1][:-1].upper()},{entity.split('@')[1].split('(')[0]},mcass_{mac.lower()}_{entity.split('@')[1].split('(')[0]},MCASS/hass/{topic.split('/')[-1]}/{entity.split('@')[1].split('(')[0]},ENTITY_CATEGORY,ICON,mcass/hass/{topic.split('/')[-1]}/{entity.split('@')[1].split('(')[0]}/available\n"
                            except:
                                dataLine = f"ENTITY,{entity.split('@')[1]},mcass_{mac.lower()}_{entity.split('@')[1]},MCASS/hass/{topic.split('/')[-1]}/{entity.split('@')[1]},ENTITY_CATEGORY,ICON,mcass/hass/{topic.split('/')[-1]}/{entity.split('@')[1]}/available\n"
                            if dataLine.split(",")[2] in loadedDataUNIQUEs:
                                continue
                            else:
                                with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
                                    dfile.write(dataLine)
                    except:
                        if entity.split('@')[0] in self.dualSensorSimple:  # ha 2 erteket mero sensor akkor nem kell domain mert fix h sensor
                            measurements = []
                            for sensor in self.dualSensor:
                                if entity.split('@')[0] == sensor[0]:
                                    measurementsAmm = int((len(sensor)-1)/2)
                                    for j in range(0+1, measurementsAmm):  # ez itt i volt de volt mar egy i feljebb es igy is moóukdoott
                                        measurements.append(sensor[j])  # ez itt i volt de volt mar egy i feljebb es igy is moóukdoott
                            for name in measurements:
                                dataLine = f"{entity.split('@')[1].split('(')[1][:-1].upper()},{entity.split('@')[1].split('(')[0]}_{name},mcass_{mac.lower()}_{entity.split('@')[1].split('(')[0]}_{name},MCASS/hass/{topic.split('/')[-1]}/{entity.split('@')[1].split('(')[0]},UNIT_OF_MEASUREMENT,ENTITY_CATEGORY,ICON,mcass/hass/{topic.split('/')[-1]}/{entity.split('@')[1].split('(')[0]}/available\n"
                                if dataLine.split(",")[2] in loadedDataUNIQUEs:
                                    continue
                                else:
                                    with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
                                        dfile.write(dataLine)
                        else:  # ha nincs domain megadva es nem is 2 erteku sensor
                            dataLine = f"ENTITY,{entity.split('@')[1]},mcass_{mac.lower()}_{entity.split('@')[1]},MCASS/hass/{topic.split('/')[-1]}/{entity.split('@')[1]},ENTITY_CATEGORY,ICON,mcass/hass/{topic.split('/')[-1]}/{entity.split('@')[1]}/available\n"
                            if dataLine.split(",")[2] in loadedDataUNIQUEs:
                                continue
                            else:
                                with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
                                    dfile.write(dataLine)
                else:
                    continue

    def sendToHassIndex(self, index):
        entity = self.entities[index]
        entitydata = self.JSONdispatch(entity)  # self.returnSensorJSON(entity[1],entity[2],entity[3],entity[4],entity[5],entity[6],entity[7])
        mac = entity[2].split("_")[1]
        parentDevice = ""
        for device in self.devices:
            if device[1].split("_")[1] == mac.upper():
                parentDevice = device
        devicedata = self.returnLongDeviceJSON(parentDevice[1], parentDevice[2], parentDevice[3], parentDevice[4], parentDevice[5], parentDevice[6], parentDevice[7])
        pubPayload = "{" + f"{entitydata},{devicedata}" + "}"
        # log.console(pubPayload)
        # homeassistant/domain(switch,sensor,stb)/id(mac?)/config
        try:
            pubTopic = f"homeassistant/{entity[0].lower()}/{entity[3].replace('/hass', '').replace('/', '_')}/config"
        except:
            pubTopic = f"homeassistant/{entity[1].lower()}/{entity[3].replace('/hass', '').replace('/', '_')}/config"
            log.warning(f"No domain defined for entity {entity[1]}")
        # log.console(pubTopic)
        # log.console("\n")
        send = True
        for element in self.nonDefinedVars:
            if element in pubPayload:
                send = False
                log.error(f"TBD NEED TO DO A CYCLE TO GET DATA FROM DEVICE? REVRITE hassImportData.txt AND RESEND DATA")
                log.error(f"{pubPayload}")
        if send:  # original was if send == True de az True == True szoval igy jo
            client.publish(pubTopic, pubPayload)

    def syncToHass(self):
        print("in getFromHass")
        global HassIP
        global HassAPIkey
        token = HassAPIkey
        headers = {
            "Authorization": "Bearer " + token,
            "content-type": "application/json",
        }
        url = f"http://{HassIP}:8123/api/states"

        try:
            response = get(url, headers=headers)
            inhass = []
            response = response.text.split("},{")
            for element in response:
                if "mcass" in element:
                    # print(element)
                    inhass.append(element)
            indexOfEntityToBeSentToHass = []  # currently there's no reliable way to check if a device exist in hass, since the API does not return unique id, only entity_id, which is created by "<device_name>_<entity_name>", because of this currently we are going by entity id
            for i in range(0, len(self.entities)):
                for j in range(0, len(inhass)):
                    if str(f'{"_".join(self.entities[i][2].split("_", 2)[:2])}_{self.entities[i][1].split("(")[0].lower()}'.replace("-", "_")) == str(inhass[j]).split('entity_id":"')[1].split(",")[0][:-1].split(".")[1]:
                        indexOfEntityToBeSentToHass.append(int(i))
            # print(indexOfEntityToBeSentToHass)
            for i in range(0, len(self.entities)):
                if i in indexOfEntityToBeSentToHass:
                    continue
                else:
                    self.sendToHassIndex(i)
        except Exception as e:
            log.error(e)

    def syncIconFromHass(self):
        print("in syncFromHass")
        global HassIP
        global HassAPIkey
        token = HassAPIkey
        headers = {
            "Authorization": "Bearer " + token,
            "content-type": "application/json",
        }
        url = f"http://{HassIP}:8123/api/states"
        try:
            response = get(url, headers=headers)
            inhass = []
            response = response.text.split("},{")
            for element in response:
                if "mcass" in element:
                    inhass.append(element)
            for i in range(0, len(self.entities)):
                for j in range(0, len(inhass)):
                    if self.entities[0][0] == "SENSOR":
                        if str(f'{"_".join(self.entities[i][2].split("_", 2)[:2])}_{self.entities[i][1].split("(")[0].lower()}'.replace("-", "_")) == str(inhass[j]).split('entity_id":"')[1].split(",")[0][:-1].split(".")[1]:  # ez ugyanaz az elem
                            if self.entities[i][6] == str(inhass[j]).split('"icon":"')[1].split('"')[0]:
                                continue
                            else:
                                print("calling replacedata within sensor")
                                ha.replaceData(str(inhass[j]).split('entity_id":"')[1].split(",")[0][:-1].split(".")[1], self.entities[i][6], str(inhass[j]).split('"icon":"')[1].split('"')[0])
                    else:
                        if str(f'{"_".join(self.entities[i][2].split("_", 2)[:2])}_{self.entities[i][1].split("(")[0].lower()}'.replace("-", "_")) == str(inhass[j]).split('entity_id":"')[1].split(",")[0][:-1].split(".")[1]:  # ez ugyanaz az elem
                            if self.entities[i][5] == str(inhass[j]).split('"icon":"')[1].split('"')[0]:
                                continue
                            else:
                                print("calling replacedata outside of sensor")
                                ha.replaceData(str(inhass[j]).split('entity_id":"')[1].split(",")[0][:-1].split(".")[1], self.entities[i][5], str(inhass[j]).split('"icon":"')[1].split('"')[0])
                        continue
        except Exception as e:
            log.error(e)

    def replaceData(self, uniqueid, oldval, newval):
        print("in replaceData")
        print(uniqueid, oldval, newval)
        tempHold = []
        newlist = []
        with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
            dfile.seek(0)
            linecount = 0  # sorok számozása
            while line := dfile.readline():
                linecount += 1  # sor szám +1
                # log.console(line.rstrip())
                tempHold.append(line.rstrip())
        for line in tempHold:
            if line.split(",")[2].lower().replace("-", "_") == uniqueid.lower():
                newlist.append(line.replace(oldval, newval))
            else:
                newlist.append(line)
        with open("hassImportData.txt", "w", encoding='UTF-8') as dfile:
            for entry in newlist:
                dfile.write(entry)
                dfile.write("\n")
        self.reloadData()

    def updateData(self, device, values):
        MANUFACTURER = "MANUFACTURER"
        MODEL = "MODEL"
        HW_VERSION = "HW_VERSION"
        SW_VERSION = "SW_VERSION"
        CONFIGURL = "CONFIGURL"
        ENTITY_CATEGORY = "ENTITY_CATEGORY"
        ICON = "ICON"
        UNIT_OF_MEASUREMENT = "UNIT_OF_MEASUREMENT"
        for data in values.split(","):
            if data.split("=")[0] == "MANUFACTURER":
                MANUFACTURER = data.split("=")[1]
            if data.split("=")[0] == "MODEL":
                MODEL = data.split("=")[1]
            if data.split("=")[0] == "HW_VERSION":
                HW_VERSION = data.split("=")[1]
            if data.split("=")[0] == "SW_VERSION":
                SW_VERSION = data.split("=")[1]
            if data.split("=")[0] == "CONFIGURL":
                CONFIGURL = data.split("=")[1]
            if data.split("=")[0] == "ENTITY_CATEGORY":
                ENTITY_CATEGORY = data.split("=")[1]
            if data.split("=")[0] == "ICON":
                ICON = data.split("=")[1]
            if data.split("=")[0] == "UNIT_OF_MEASUREMENT":
                UNIT_OF_MEASUREMENT = data.split("=")[1]
        tempHold = []
        newlist = []
        with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
            dfile.seek(0)
            linecount = 0  # sorok számozása
            while line := dfile.readline():
                linecount += 1  # sor szám +1
                # log.console(line.rstrip())
                tempHold.append(line.rstrip())
        if len(device.split("@")) == 2:
            for entry in tempHold:
                if entry.split(",")[0] != "DEVICE":
                    if entry.split(",")[2].split("_")[1].upper() == device.split("@")[0]:
                        if device.split("@")[1] == entry.split(",")[1]:
                            newlist.append(entry.replace("ENTITY_CATEGORY", f"{ENTITY_CATEGORY}").replace("ICON", ICON).replace("UNIT_OF_MEASUREMENT", UNIT_OF_MEASUREMENT))
                        else:
                            newlist.append(entry)
                    else:
                        newlist.append(entry)
                else:
                    newlist.append(entry)
        else:
            for entry in tempHold:
                if entry.split(",")[0] == "DEVICE":
                    if entry.split(",")[1].split("_")[1].upper() == device.upper():
                        newlist.append(entry.replace("MANUFACTURER", MANUFACTURER).replace("MODEL", MODEL).replace("HW_VERSION", HW_VERSION).replace("SW_VERSION", SW_VERSION).replace("CONFIGURL", CONFIGURL))
                    else:
                        newlist.append(entry)
                else:
                    newlist.append(entry)
        with open("hassImportData.txt", "w", encoding='UTF-8') as dfile:
            for entry in newlist:
                dfile.write(entry)
                dfile.write("\n")
        self.reloadData()

    def getAmmountOfMissing(self):
        ok = 0
        notok = 0
        joinedlist = []
        for row in self.devices:
            joinedlist.append(row)
        for row in self.entities:
            joinedlist.append(row)
        for row in joinedlist:
            for element in row:
                if element.upper() in self.nonDefinedVars:  # sosem fogy el mert a rotarynak entity a domain es az benne van a non definedba
                    notok += 1
                else:
                    ok += 1
        if ok != 0:
            result = notok/ok*100
        else:
            result = 100
        return int(result)

    asketfordev = 0
    asketforent = 0

    def getDataForRequest(self):
        if self.asketfordev > 9999 or self.asketforent > 9999:
            self.asketfordev = 0
            self.asketforent = 0
        if self.asketfordev <= self.asketforent:
            self.asketfordev += 1
            for i in range(self.asketfordev % len(self.devices), len(self.devices)):
                for element in self.devices[i]:
                    if element.upper() in self.nonDefinedVars:
                        return self.devices[i][1].split("_")[1]
                    else:
                        continue
            self.asketfordev += 10

        else:
            self.asketforent += 1
            for i in range(self.asketforent % len(self.entities), len(self.entities)):
                for element in self.entities[i]:
                    if element.upper() in self.nonDefinedVars:
                        return f"{self.entities[i][2].split('_')[1].upper()}@{self.entities[i][2][24:]}"  # mac @ peripheral name
                    else:
                        continue
            self.asketforent += 10

    def getDefaultData(self, mac, name):  # vagy nev vagy nev_egyikerzekeles
        sensi = ""
        try:
            namehelp = name.split("_")[0]
            sensi = name.split("_")[1]
            name = namehelp
        except:
            name = name
        peripheralType = ""
        domain = ""
        ENTITY_CATEGORY = "ENTITY_CATEGORY"
        ICON = "ICON"
        UNIT_OF_MEASUREMENT = "UNIT_OF_MEASUREMENT"
        for device in configtable:
            if device[0] == mac.upper():
                for peripheral in device[2].split("/"):
                    try:
                        if peripheral.split("@")[1].split("(")[0] == name:
                            # print("ok")
                            peripheralType = peripheral.split("@")[0]
                            domain = peripheral.split("@")[1].split("(")[1][:-1]
                    except:
                        # print("failed")
                        if peripheral.split("@")[1] == name:
                            peripheralType = peripheral.split("@")[0]
        if domain == "":
            domain = "ENTITY"
        for DevType in self.defautlUOMByType:
            if DevType[0] == peripheralType:
                for i in range(0, len(DevType)-1):
                    if sensi != "":
                        if DevType[i] == sensi:
                            UNIT_OF_MEASUREMENT = DevType[int((len(DevType)-1)/2+i)]
                    else:
                        UNIT_OF_MEASUREMENT = DevType[int((len(DevType)-1)/2+i)]
        for DevType in self.defaultIconByType:
            if DevType[0] == peripheralType:
                for i in range(0, len(DevType)-1):
                    if sensi != "":
                        if DevType[i] == sensi:
                            ICON = DevType[int((len(DevType)-1)/2+i)]
                    else:
                        ICON = DevType[int((len(DevType)-1)/2+i)]

        for domaintype in self.defaultDataByDomainList:
            if domain.upper() == domaintype[0]:
                ENTITY_CATEGORY = domaintype[1]
                if ICON == "ICON":
                    ICON = domaintype[2]
        # print(UNIT_OF_MEASUREMENT)
        # print(ENTITY_CATEGORY)
        # print(ICON)
        if sensi != "":
            sensi = f"_{sensi}"
        ha.updateData(f"{mac}@{name}{sensi}", f"UNIT_OF_MEASUREMENT={UNIT_OF_MEASUREMENT},ENTITY_CATEGORY={ENTITY_CATEGORY},ICON={ICON}")


    startedPings = []  # ID, unique id

    def checkAvailablity(self):
        for device in self.devices:
            self.startedPings.append(f"{p.pingstart(device[1].split('_')[1], 4)}*{device[2]}".split("*"))

    def getAvail(self):
        for entry in self.startedPings:
            result = p.get_result(entry[0])
            if result is None:
                continue
            else:
                if result == "Failed":
                    self.setAllSensorsOfDeviceToOffline(entry[1])
                    log.error(f"Availability check failed for device {entry[1]}")  # get the avail topic for it and send unavaible message
                elif result == "Successful":
                    log.warning("TBD IMPLEMENT SUCCESSUL PING TO AVAILABILITY ON habár szerintem ide nem kell semmi mert ha jon adat az entitytol akkor online lesz az entity de a tobbit azert nem huznam fel onlinera")
                    log.console(f"Availability check succeeded for device {entry[1]}")  # get the avail topic for it and send avaible message
                else:
                    log.error(f'Unknown result given to ping: "{result}"')
            self.startedPings.remove(entry)

    def setAllSensorsOfDeviceToOffline(self, device):
        print("in setAllSensorsOfDeviceToOffline")
        mac = device.replace("mcass", "")
        for entry in self.entities:
            if entry[0] == "SENSOR":
                if entry[2].split("_")[1] == mac:
                    client.publish(entry[7], "offline")
            else:
                if entry[2].split("_")[1] == mac:
                    client.publish(entry[6], "offline")

    def getStatusTopic(self, SensorName, Device, Domain):
        for entry in self.entities:
            if Domain != "":  # ha megvan a domain is
                if entry[1] == SensorName and entry[0] == Domain.upper() and entry[2] == f"mcass_{Device.lower()}_{SensorName}":
                    return entry[3]
            else:  # ha nics domain
                if entry[1] == SensorName and entry[2] == f"mcass_{Device.lower()}_{SensorName}":
                    return entry[3]

    def getAvailabilityTopic(self, SensorName, Device, Domain):
        for entry in self.entities:
            if Domain != "":  # ha megvan a domain is
                if entry[1] == SensorName and entry[0] == Domain.upper() and entry[2] == f"mcass_{Device.lower()}_{SensorName}":
                    return entry[7]
            else:  # ha nics domain
                if entry[1] == SensorName and entry[2] == f"mcass_{Device.lower()}_{SensorName}":
                    return entry[7]

    def getSubSensors(self, SensorName, Device, Domain):
        tbrnames = []
        for entry in self.entities:
            if len(entry[1].split("_")) == 2:
                if Domain != "":
                    if entry[0] == Domain and entry[1].split("_")[0] == SensorName and entry[2].split("_")[1].upper() == Device:
                        tbrnames.append(entry[1])
                else:
                    if entry[1].split("_")[0] == SensorName and entry[2].split("_")[1].upper() == Device:
                        tbrnames.append(entry[1])
        if len(tbrnames) < 2:  # ha simplasensor pl bh1750
            return SensorName
        return tbrnames


if HaState == "ON":
    log.info("Starting HASS...")
    ha = HASS()
    # ha.kiirALL()
    ha.kiirOnlyNew()
    ha.reloadData()
    # ha.syncToHass()
    # print("getDefaultData")
    # ha.getDefaultData("3C-AB-72-96-52-F4", "DHT_Humidity")
    # ha.getDefaultData("3C-AB-72-96-52-F4", "LightSensor")
    # ha.syncIconFromHass()
else:
    log.info("Skipping the startup off HASS, as it is not configured")


class ProtocolBook:
    protocollist = []  # protocollist=[protpointer, protname, type(short,normal,long,everycycle) or off]
    protDict = {}

    def __init__(self):
        var = 1
        for protocol in dir(ProtocolBook):
            if "__" not in protocol and protocol != "protShort" and protocol != "protNorm" and protocol != "protLong" and protocol != "protocollist" and protocol != "protDict" and protocol != "everyLoop":
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
                elif protocol[-1] == "e":
                    self.protocollist.append(str(f"{var}*{protocol}*every").split("*"))
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
        for protocol in self.protocollist:
            if protocol[0][0] == "H" and protocol[0][1] == "A":
                if HaState == "OFF":
                    log.info(f"Switching off protocol {protocol[1]} with id of {protocol[0]} due to MQTTDISCOVERY setting being turned off")
                    protocol[2] = "off"

    def testn(self, command):
        if command == "getID":
            return "T2"
        # print("test normal")

    def tests(self, command):
        if command == "getID":
            return "T1"
        # print("test short")

    def testl(self, command):
        if command == "getID":
            return "T3"
        # print("test long")

    def teste(self, command):
        if command == "getID":
            return "T0"
        # print("test everyloop")

    def protShort(self):
        for i in range(0, len(self.protocollist)):
            if self.protocollist[i][2] == "short":
                # log.console("Executes short protocols")
                self.protDict[self.protocollist[i][0]](self, "none")

    def protNorm(self):
        for i in range(0, len(self.protocollist)):
            if self.protocollist[i][2] == "normal":
                # log.console("Executes normal protocols")
                self.protDict[self.protocollist[i][0]](self, "none")

    def protLong(self):
        for i in range(0, len(self.protocollist)):
            if self.protocollist[i][2] == "long":
                # log.console("Executes long protocols")
                self.protDict[self.protocollist[i][0]](self, "none")

    def everyLoop(self):
        for i in range(0, len(self.protocollist)):
            if self.protocollist[i][2] == "every":
                # log.console("Executes protocols every loop")
                self.protDict[self.protocollist[i][0]](self, "none")

    def frequencyCheckern(self, command):  # !!!!!! lentebb egy ifbe ez a név van ctrl+c ctrl+v-zve, ha itt atirod ird at ott is
        if command == "getID":
            return "HA1"
        FUNCTION_NAME = "frequencyCheckern"
        NAME_OF_SISTER_FUNC = "dataGettern"
        # ha a lentebbi megy akkor normal
        # ha nem megy akkor long
        AmmOfMissingData = ha.getAmmountOfMissing()
        if AmmOfMissingData > 25:  # ha 25%nal tobb hianyzik
            for protocol in self.protocollist:  # nezd vegig a listat
                if protocol[1] == NAME_OF_SISTER_FUNC:  # ha a nev egyezik a masikeval
                    if protocol[2] != "normal":
                        protocol[2] = "normal"  # rakd at normalra
                        log.info("Ammount of missing data is high, switching dataGetter protocol to normal")
        elif AmmOfMissingData > 0:  # ha 25%nal kevesebb hianyzik
            for protocol in self.protocollist:  # nezd vegig a listat
                if protocol[1] == NAME_OF_SISTER_FUNC:  # ha a nev egyezik a masikeval
                    if protocol[2] != "long":
                        protocol[2] = "long"  # rakd at longea
                        log.info("Ammount of missing data is under 25%, switching dataGetter protocol to long")
        elif AmmOfMissingData == 0:  # semennyi enm hianyzik
            for protocol in self.protocollist:  # nezd vegig a listat
                if protocol[1] == NAME_OF_SISTER_FUNC:  # ha a nev egyezik a masikeval
                    if protocol[2] != "off":
                        protocol[2] = "off"  # kapcsold ki
                        log.info("Ammount of missing data is none, switching dataGetter off")

        for protocol in self.protocollist:  # nezd vegig a listat
            if protocol[1] == NAME_OF_SISTER_FUNC:  # ha a neve ugyanaz mint a masiknak
                if protocol[2] == "off":  # es ki van kapcsolva
                    for selfprot in self.protocollist:  # nezd vegig a listat
                        if selfprot[1] == FUNCTION_NAME:  # ha megtalaltad magad
                            if selfprot[2] != "long":  # ha eddig nem normalban voltal
                                selfprot[2] = "long"  # rakd at longra
                                log.info("dataGetter protocol is stopped, swithing frequencyChecker to long")

                if protocol[2] != "off":  # ha megy
                    for selfprot in self.protocollist:  # nezd vegig a listat
                        if selfprot[1] == FUNCTION_NAME:  # ha megtalaltad magad
                            if selfprot[2] != "normal":  # ha eddig nem normalban voltal
                                selfprot[2] = "normal"  # rakd at normalra magad
                                log.info("dataGetter protocol is going, swithing frequencyChecker to normal")

    def dataGettern(self, command):  # !!!!! a fenti protocolba stringkent ez a func name van megadva, ha itt atirod ird at ott is
        # ha az adatok 50%a hianyzik normal, ha 25%a akkor long, ha semmi akkor off
        attempts = 0
        if command == "getID":
            return "HA2"
        data = ha.getDataForRequest()
        while data is None and attempts < 6:
            data = ha.getDataForRequest()
            attempts += 1
        if len(data.split("@")) == 2:
            ha.getDefaultData(data.split("@")[0], data.split("@")[1])  # ez megy internalba
        else:
            for device in configtable:
                if device[0] == data.upper():
                    client.publish(device[1], "PRTCL_GETINFO:SELF")  # get the data of the device itself

    def avCheckerl(self, command):
        if command == "getID":
            return "HA3"
        ha.checkAvailablity()

    def avReportn(self, command):
        if command == "getID":
            return "HA4"
        ha.getAvail()

    def HassSyncl(self, command):
        if command == "getID":
            return "HA5"
        if SyncOnlyWhenOnTestServer:  # old was if SyncOnlyWhenOnTestServer == True which is if True == True
            if HassIP == "192.168.0.150":
                ha.syncToHass()
        else:
            ha.syncToHass()

    def HassSyncBackl(self, command):
        if command == "getID":
            return "HA6"
        ha.syncIconFromHass()


log.info("Starting ProtocolBook...")
prot = ProtocolBook()

log.info("Starting MQTT...")
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
log.info("Succesfully loaded and connected to MQTT broker")


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


def domainRemover(input):
    list = input.split("/")
    tbr = str(list[0])
    for i in range(1, len(list)):
        tbr = tbr + "/"
        try:
            tbr = tbr + f"{list[i].split('(')[0]}{list[i].split(')')[1]}"
        except:
            tbr = tbr + f"{list[i]}"
    return tbr


def on_message(client, userData, msg):
    log.console(f"Message ({msg.payload}) arrived from ({msg.topic})")
    if msg.topic == configreqtopic:
        device = extract_address(str(msg.payload))
        if device is None:
            log.warning(f"No device address provided in message {msg.payload}, continuing")  # nem jött mac address az uzenetben
        else:
            config = get_device_config(device)
            if config is None:  # nincs a config fajlban a mac
                log.warning(f"No device config available for {device}")
                tbc(device)  # kulon fajlba beirni a nem definialt macet, met ha a confighoz adjuk hozza ugyanugy megfogja mert nincs hozza config és azt kiüti a beolvasas amihez nincs mqtt csati
            else:  # egyebkent kuldje el
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
                # ping_end(address) old ping
                p.pingend(address)

    if str(msg.payload) == "b'PRTCL_PINCONFIG:REQUEST'":  # pinconfig request ---#PRTCL_PINCONFIG:config
        for i in range(0, len(configtable)):
            if msg.topic == configtable[i][1]:
                client.publish(configtable[i][1], f"PRTCL_PINCONFIG:{domainRemover(configtable[i][2])}")

    if "PRTCL_READBACK:" in str(msg.payload):  # readback ---#PRTCL_READBACK:OK if ok ---#PRTCL_READBACK:NOPE if not good readback
        if "OK" not in str(msg.payload) and "NOPE" not in str(msg.payload):
            for i in range(0, len(configtable)):
                if msg.topic == configtable[i][1]:
                    if str(msg.payload).split(":")[1][:-1] == domainRemover(configtable[i][2]):
                        client.publish(configtable[i][1], "PRTCL_READBACK:OK")
                    else:
                        client.publish(configtable[i][1], "PRTCL_READBACK:NOPE")

    if "PRTCL_LOG" in str(msg.payload):
        if str(msg.payload).split(":")[0] == "b'PRTCL_LOG_INFO":
            log.info(f'Log from {str(msg.topic)}: {str(msg.payload).split(":", 1)[1][:-1]}')
        elif str(msg.payload).split(":")[0] == "b'PRTCL_LOG_WARNING":
            log.warning(f'Log from {str(msg.topic)}: {str(msg.payload).split(":", 1)[1][:-1]}')
        elif str(msg.payload).split(":")[0] == "b'PRTCL_LOG_ERROR":
            log.error(f'Log from {str(msg.topic)}: {str(msg.payload).split(":", 1)[1][:-1]}')
        elif str(msg.payload).split(":")[0] == "b'PRTCL_LOG":
            log.warning(f'No error level was provided, general log protocol. Handling as warning. Error in next line')
            log.warning(f'Log from {str(msg.topic)}: {str(msg.payload).split(":", 1)[1][:-1]}')
        else:
            log.error(f'Unkown error level provided from {str(msg.topic)} with level {str(msg.payload).split(":")[0][-2:]}\nError message was: {str(msg.payload).split(":")[1][:-1]}')

    if "PRTCL_GIVEINFO:" in str(msg.payload):
        device = ""
        giveninfo = str(msg.payload).split(":", 1)[1][:-1]
        for entry in configtable:
            if str(msg.topic) == entry[1]:
                device = entry[0]
        if device != "":
            ha.updateData(device, giveninfo)

    if "PRTCL_VAL:" in str(msg.payload):  # value forwarder
        if HaState == "ON":
            if len(str(msg.payload).split("/")) < 2:  # ha single sensor
                name = str(msg.payload).split(":")[1].split("@")[0]
                value = str(msg.payload).split("@")[1][:-1]
                SensorName = name  # sensor name
                Device = ""  # mac address
                Domain = ""
                for device in configtable:
                    if str(msg.topic) == device[1]:
                        Device = device[0]
                        for entry in device[2].split("/"):
                            if "_" in name:
                                name = name.split("_")[0]
                            if name in entry:
                                if len(entry.split("(")) == 2:  # ha tud (-ra splitelni akkor van domain definialva
                                    # SensorName = entry.split("@")[1].split("(")[0]
                                    Domain = entry.split("@")[1].split("(")[1].split(")")[0]
                                else:
                                    continue
                                    # SensorName = entry.split("@")[1]

                # get status topic
                topic = ha.getStatusTopic(SensorName, Device, Domain)
                availtopic = ha.getAvailabilityTopic(SensorName, Device, Domain)
                if topic is not None:
                    client.publish(topic, value)
                    client.publish(availtopic, "online")
                else:
                    log.error(f'Failed to find status topic for sensor with name "{SensorName}" under device "{Device}" (Domain:"{Domain}")')
            else:
                log.error("Báttya itt valami nem jó mert csak 1et kéne hogy kapjak egyszerre")

    if "PRTCL_AVAILABILITY_OFF:" in str(msg.payload):
        if HaState == "ON":
            name = str(msg.payload).split(",")[0].split(":")[1]
            type = str(msg.payload).split(",")[1]
            SensorName = name
            Device = ""  # mac address
            Domain = ""
            for device in configtable:
                if str(msg.topic) == device[1]:
                    Device = device[0]
            Names = ha.getSubSensors(SensorName, Device, Domain)
            for SensorName in Names:
                availtopic = ha.getAvailabilityTopic(SensorName, Device, Domain)
                if availtopic is not None:
                    client.publish(availtopic, "offline")
                else:
                    log.error(f'Failed to find status topic for sensor with name "{SensorName}" under device "{Device}" (Domain:"{Domain}")')


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
    if False:  # og ping
        if len(ping_tasks) != 0:  # pingelés func
            for i in reversed(range(0, len(ping_tasks))):  # törlés és kiiras
                if ping_tasks[i][6] + ping_tasks[i][7] == ping_tasks[i][2]:  # kiiras
                    if ping_tasks[i][6] == 0:  # nem volt válaszolt ping
                        log.warning(f"\nPing failed: {ping_tasks[i][6]} success, {ping_tasks[i][7]} failed out of {ping_tasks[i][2]}\n")
                    if ping_tasks[i][6] != 0:  # volt valaszolt ping
                        log.console(f"\nPing results: {ping_tasks[i][6]} success, {ping_tasks[i][7]} failed out of {ping_tasks[i][2]}\nAvarage time was {ping_tasks[i][5]/ping_tasks[i][6]}\n\n")
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

    if True:  # new ping
        p.ping_runtime()

# *****************************************************************************************************************************************************************************************************************

# client.loop_stop()
