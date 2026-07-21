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
# multithreading
import threading
finishedStartup = False
SyncOnlyWhenOnTestServer = False  # csak akkor syneljen hassba ha a test serveren van ezt kulon en adtam meg majd el kell tavolitani, ONLY FOR DEVELOPMENT
version = "0.4.2"

PROTOCOL_TIMEOUT_SHORT = 0.5
PROTOCOL_TIMEOUT = 5
PROTOCOL_TIMEOUT_LONG = 60
PROTOCOL_TIME_SHORT = 0
PROTOCOL_TIME = 0
PROTOCOL_TIME_LONG = 0

TBCCONFLICTHANDLE = "error"  # options are "error"/"delete"

webcontrol = True
webloglevel = "INFO"

activeErrors = [] #thing with error, reason for error
def activeErrorHandler(error, reason, action):
    global activeErrors
    print(activeErrors)
    #print(error, reason, action)
    if action == "add":
        for i in range(0, len(activeErrors)):
            if error == activeErrors[i][0] and reason == activeErrors[i][1]: # ha már benne van ez az a kérdés
                return False
        activeErrors.append(f"{error}*{reason}".split("*"))
        return True
    elif action == "remove":
        for i in range(0, len(activeErrors)):
            if error == activeErrors[i][0] and reason == activeErrors[i][1]:
                activeErrors.pop(i)
                return True
    else:
        log.error(f"Unkown action given in activeErrorHandler: {action}")
        return False
    return False # ez azert kell h legyen visszajelzes akkor is ha a remove nem talalja az eltavolitando dolgot


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

lastMessageTime = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
# lastMessageCap = 15 #dinamikus méretű üzenet idő megtartáshoz lenne használva
lastMessageAvgTime = 0
selfTestHang = False

ping_table = []
ping_table_long = []
ping_min = 9999
ping_max = 0
ping_timeout = 2.5  # in seconds

broker = "127.0.0.1"
port = 1883
username = ""
password = ""
client_id = "MQTTControlServer"
configreqtopic = "test/config/request"
configrepltopic = "test/config/reply"
devicetopic = "test/devices/#"
negotopic = "MCASS/negotiate"
server_id = "MQTTControlServer"
selftesttopic = f"MCASS/server/self/{server_id}"

servercontroltopic = "MCASS/server/control"


configtable = []
deviceData = []  # runtime data for web control, # mac, device_model, gateway, ip_addr, mask, last_avg_ping_time

HassAPIkey = ""
HassIP = ""
HaState = "OFF"

L3error_max_rep = 0
L3error_max_rep_within = 100
L3timeoutforwarning = 15
P2max_ping_storage = 25

# még a pingekhez lehetne adni sorszámot, hogy tudjuk melyik pingre válaszol, mer most ha kimegy ketto ping de olyan lassan valszol h az elso timoutol de a masodik kikuldese utan jon vissza az elso akkor annak jo lesz a statja de igazabol az elsore valaszolt, majd ha nagyon belekavar akk megcsinalom
ping_tasks = []  # mac,numberofpings(forcountdown),numberofpings,pingstart,pingend,pingtimesum,succestimer,timoutcounter


class Logger3:

    wll = "INFO"

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
    if not os.path.exists(filepath[:-1]):
        print("logs folder does not exist, creating...")
        os.makedirs(filepath[:-1])

    def __init__(self):
        global L3timeoutforwarning
        global L3error_max_rep_within
        global L3error_max_rep
        global webloglevel
        self.wll = webloglevel
        self.timeoutforwarning = L3timeoutforwarning
        self.error_max_rep = L3error_max_rep
        if self.error_max_rep == 0:
            self.error_max_rep = 9
            self.error_max_rep_within = 1
        else:
            self.error_max_rep_within = L3error_max_rep_within
        self.filename = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S').replace(" ", "_").replace(":", "_")
        file = open(f"{self.filepath}{self.filename}_log3.txt", "w")
        file.close()
        file = open(f"{self.filepath}{self.filename}_console3.txt", "w")
        file.close()
        self.info("Started Logger3...")


    def updateWLL(self):
        global webloglevel
        self.wll = webloglevel

    @staticmethod
    def printOnly(info):
        print(info)

    def forwardToWeb(self, info, level):
        add = False
        if finishedStartup:
            if self.wll == "INFO":
                add = True
            elif self.wll == "WARNING":
                if level.upper() == "WARNING" or level.upper() == "ERROR":
                    add = True
            elif self.wll == "ERROR":
                if level.upper() == "ERROR":
                    add = True

            if add:
                add_log(info, level)  # for sending logs to webpage
            else:
                return

    def console(self, info):  # print to console only
        wherefrom = cast(FrameType, cast(FrameType, inspect.currentframe()).f_back).f_code.co_name
        print(info)
        with open(f"{self.filepath}{self.filename}_console3.txt", "a", encoding="utf-8") as file:
            file.write(f"\n[Console] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")

    def info(self, info):
        self.forwardToWeb(info, "info")
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        wherefrom = cast(FrameType, cast(FrameType, inspect.currentframe()).f_back).f_code.co_name
        print(info)
        with open(f"{self.filepath}{self.filename}_log3.txt", "a", encoding="utf-8") as file:
            file.write(f"\n[Info] [{timestamp}]: {info} FROM {wherefrom}")
        with open(f"{self.filepath}{self.filename}_console3.txt", "a", encoding="utf-8") as file:
            file.write(f"\n[Info] [{timestamp}]: {info} FROM {wherefrom}")

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
            self.forwardToWeb(info, "warning")
            print(f"\n[Warning] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
            with open(f"{self.filepath}{self.filename}_log3.txt", "a", encoding="utf-8") as file:
                file.write(f"\n[Warning] [{timestamp}]: {info} FROM {wherefrom}")
            self.timeoutlist.append(f"{datetime.datetime.now() + datetime.timedelta(minutes=self.timeoutforwarning)}*[Warning]: {info} FROM {wherefrom}".split("*"))
            with open(f"{self.filepath}{self.filename}_console3.txt", "a", encoding="utf-8") as file:
                file.write(f"\n[Warning] [{timestamp}]: {info} FROM {wherefrom}")

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
            self.forwardToWeb(info, "error")
            print(f"\n[Error] [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {info} FROM {wherefrom}")
            with open(f"{self.filepath}{self.filename}_log3.txt", "a", encoding="utf-8") as file:
                file.write(f"\n[Error] [{timestamp}]: {info} FROM {wherefrom}")
            with open(f"{self.filepath}{self.filename}_console3.txt", "a", encoding="utf-8") as file:
                file.write(f"\n[Error] [{timestamp}]: {info} FROM {wherefrom}")

    def inLastX(self, x, text, returnNumber = False, maxOccurance = 2):
        lastlines = []
        with open(f"{self.filepath}{self.filename}_log3.txt", encoding='UTF-8') as file:
            for line in (file.readlines()[-x:]):
                lastlines.append(line)
        for i in range(0, len(lastlines)):
            if text in lastlines[i]:
                if returnNumber:
                    return i
                else:
                    return True
        #for line in lastlines:
            #if text in line:
                #return True
        return False

    def inLastXConsole(self, x, text, returnNumber = False, maxOccurance = 1):
        lastlines = []
        occurance = 0
        with open(f"{self.filepath}{self.filename}_console3.txt", encoding='UTF-8') as file:
            for line in (file.readlines()[-x:]):
                lastlines.append(line)
        for i in range(0, len(lastlines)):
            if text in lastlines[i]:
                occurance += 1
                if occurance >= maxOccurance:
                    if returnNumber:
                        return i
                    else:
                        return True
        #for line in lastlines:
            #if text in line:
                #return True
        return False


log = Logger3()

log.info("Loading server configuration...")


def disableHass():
    global HaState
    global ha
    #del ha  # # # kicommentelve, itt még nincs létrehozva a hass class
    HaState = "OFF"

def enableHass():
    global HaState
    HaState = "ON"
    # run HA startup process


def testHassKey():
    global HassIP
    global HassAPIkey
    token = HassAPIkey
    headers = {
        "Authorization": "Bearer " + token,
        "content-type": "application/json",
    }
    url = f"http://{HassIP}:8123/api/"
    try:
        response = get(url, headers=headers)

        if "[200]" in str(response):
            log.info("Hass Key OK")
            if response.text == '{"message":"API running."}':
                log.info("Hass API OK")
            else:
                log.error("Hass API not running")
                disableHass()
        else:
            log.error(f"Hass API error: response: {response}, error: {response.text}")
            disableHass()

    except Exception as e:
        log.error("Something went wrong while testing HASS API key... (Error found in next line)")
        log.error(e)
        disableHass()

def loadConfig():
    log.info("Loading server config...")
    global PROTOCOL_TIMEOUT, PROTOCOL_TIMEOUT_SHORT, PROTOCOL_TIMEOUT_LONG, broker, port, configreqtopic, configrepltopic, devicetopic, username, password, TBCCONFLICTHANDLE, HassAPIkey, client_id, HassIP, L3timeoutforwarning, L3error_max_rep, L3error_max_rep_within, P2max_ping_storage, HaState, webcontrol, webloglevel,server_id
    with open("CONFIGURATION.txt", "a+", encoding='UTF-8') as configfile:
        configfile.seek(0)
        linecount = 0  # sorok számozása
        while line := configfile.readline():
            linecount += 1  # sor szám +1
            linecontent = line.rstrip().split(" #")[0].replace(" ", "").replace(",", "").replace('"', "")
            if len(linecontent) == 0:
                continue
            if linecontent[0] != "#":
                log.console(linecontent)
                param = linecontent.split("=")[0].upper()
                if param == "PROTOCOL_TIMEOUT":
                    PROTOCOL_TIMEOUT = int(linecontent.split("=")[1])
                elif param == "PROTOCOL_TIMEOUT_SHORT":
                    PROTOCOL_TIMEOUT_SHORT = int(linecontent.split("=")[1])
                elif param == "PROTOCOL_TIMEOUT_LONG":
                    PROTOCOL_TIMEOUT_LONG = int(linecontent.split("=")[1])
                elif param == "BROKER":
                    broker = linecontent.split("=")[1]
                elif param == "PORT":
                    port = int(linecontent.split("=")[1])
                elif param == "CONFIGREQUEST":
                    configreqtopic = linecontent.split("=")[1]
                elif param == "CONFIGREPLY":
                    configrepltopic = linecontent.split("=")[1]
                elif param == "DEVICETOPIC":
                    devicetopic = linecontent.split("=")[1]
                elif param == "USERNAME":
                    username = linecontent.split("=")[1]
                elif param == "PASSWORD":
                    password = linecontent.split("=")[1]
                elif param == "CLIENT_ID":
                    client_id = linecontent.split("=")[1]
                elif param == "TBCCONFLICTHANDLE":
                    TBCCONFLICTHANDLE = linecontent.split("=")[1]
                elif param == "HAK":
                    HassAPIkey = linecontent.split("=")[1]
                elif param == "HASS":
                    if linecontent.split("=")[1] == "BROKER":
                        HassIP = broker
                    else:
                        HassIP = linecontent.split("=")[1]
                elif param == "L3_EMR":
                    L3error_max_rep = linecontent.split("=")[1]
                elif param == "L3_EMRW":
                    L3error_max_rep_within = linecontent.split("=")[1]
                elif param == "L3_TOF":
                    L3timeoutforwarning = linecontent.split("=")[1]
                elif param == "P2_MPS":
                    P2max_ping_storage = linecontent.split("=")[1]
                elif param == "MQTTDISCOVERY":
                    HaState = linecontent.split("=")[1]
                elif param == "WEBCONTROL":
                    if linecontent.split("=")[1] == "ON":
                        webcontrol = True
                    elif linecontent.split("=")[1] == "OFF":
                        webcontrol = False
                elif param == "WLL":
                    webloglevel = linecontent.split("=")[1].upper()
                    log.updateWLL()
                elif param == "SERVERID":
                    server_id = linecontent.split("=")[1].upper()

                else:
                    log.error(f"Unkown variable given in CONIGURATION.txt at line {linecount} in the form of {linecontent}")
        log.info("Server config data loaded")
        if broker == "127.0.0.1":
            log.error("Minimal config not fullfilled, broker not set")
            log.info("Exiting...")
            exit(999)

        testHassKey()

loadConfig()


if HassIP == "":
    HassIP = broker


log.info("Loading device configurations...")


def loadConfigTable():
    with open("configtable.txt", 'a+', encoding='UTF-8') as cfile:  # a+: Read and append. Pointer at end. Creates file if it doesn't exist. was 'r' earlier
        cfile.seek(0)
        linecount = 0  # sorok számozása
        while line := cfile.readline():
            linecount += 1  # sor szám +1
            tobedeleted = False  # alapra állít a sor törlése
            log.console(line.rstrip())
            if line.rstrip()[0] != "#":  # kezelje le ha ures a configtable.txt
                if len(line.rstrip().split(",")) < 2:  # ha nincs vessző, szóval valami biztos hiányzik
                    log.error(f"Config invalid, not enough arguments in line {linecount}")
                else:
                    configtable.append(line.rstrip().split(','))
                    deviceData.append(f"{line.rstrip().split(',')[0]}*n/a*n/a*n/a*n/a*n/a".split("*"))
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
                                if (configtable[-1][0][i-1] < '0' or configtable[-1][0][i-1] > '9') and (configtable[-1][0][i-1] < 'A' or configtable[-1][0][i-1] > 'F') and (configtable[-1][0][i-1] < 'a' or configtable[-1][0][i-1] > 'f'):
                                    log.error(f"Mac address contains non hex characters in line {linecount} with argument {configtable[-1][0]}")
                                    tobedeleted = True
                                    break
                                if 'a' < configtable[-1][0][i-1] < 'f':
                                    log.warning(f'Mac address format mismatch, converting lower case characters to upper case in {configtable[-1][0]} at line {linecount }')
                                    configtable[-1][0] = configtable[-1][0].upper()
                    nameshelp = []
                    templine = ""
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

                    existing_topics = []
                    matchcount = 0
                    for entry in configtable:  # ha nem minden ciklusban toltjuk ujra fel 0rol akkor jobb lenne
                        existing_topics.append(entry[1])
                    for et in existing_topics:
                        if configtable[-1][1] == et:
                            matchcount += 1
                    if matchcount > 1:
                        tobedeleted = True
                        log.error(f"Duplicate device topic in line {linecount}. Removing from configtable")

                    log.console(configtable[-1])
            else:
                log.info(f"Line {linecount} commented out, skipping")

            if tobedeleted:
                del configtable[-1]
                del deviceData[-1]
    log.info(f"Ammount of entries in configtable: {len(configtable)}")


loadConfigTable()


def reloadConfigTable():
    log.info("Reloading configtable")
    try:
        global configtable
        global deviceData
        configtable = []
        deviceData = []
        loadConfigTable()
        return "OK"
    except Exception as e:
        log.error(f"Error occurred while reloading configtable.txt: {e}")
        return "ERROR"


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


def setRuntimeDataPing(mac, result):
    for i in range(0, len(deviceData)):
        if deviceData[i][0] == mac:
            if result == "Failed":
                deviceData[i][5] = result
            else:
                deviceData[i][5] = f"{result} ms"
                if ha.getAvailabilityTopic("Ping", mac, "SENSOR") is not None: # ez a 3 csak azert kell h hassba elkuldje
                    client.publish(ha.getAvailabilityTopic("Ping", mac, "SENSOR"), "online")
                    client.publish(ha.getStatusTopic("Ping", mac, "SENSOR"), result)
                else:
                    log.error(f"Tried to update Ping status of device {mac}, which is not existing in the list of hassImportData.txt")
            return
    log.error(f"Device with mac address {mac} was not found in deviceData to update last ping time")


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
        for pt in self.ping_tasks2:
            if address == pt[0]:
                log.info(f"Address {address} already in ping que, skipping")
                return
        self.ping_tasks2.append([address, numberofpings, numberofpings, 1, 0, 0, 0, 0, ID])
        return ID

    def pingend(self, address):
        ct = time.monotonic()
        for pe in self.ping_tasks2:
            if address == pe[0]:
                pe[4] = ct

    def ping_runtime(self):  # ebben is lehetne sokkat egyszeriusiteni ha kivennenk a "in range" reszeket
        while len(self.ping_results2) > self.max_ping_storage:
            self.ping_results2.pop(0)
        if len(self.ping_tasks2) != 0:  # pingelés func
            for i in reversed(range(0, len(self.ping_tasks2))):  # törlés és kiiras
                if self.ping_tasks2[i][6] + self.ping_tasks2[i][7] == self.ping_tasks2[i][2]:  # kiiras
                    if self.ping_tasks2[i][6] == 0:  # nem volt válaszolt ping
                        log.warning(f"Ping failed: {self.ping_tasks2[i][6]} success, {self.ping_tasks2[i][7]} failed out of {self.ping_tasks2[i][2]}\n")
                        self.ping_results2.append(f"{self.ping_tasks2[i][8]}*Failed".split("*"))
                        setRuntimeDataPing(self.ping_tasks2[i][0], "Failed")
                    if self.ping_tasks2[i][6] != 0:  # volt valaszolt ping
                        log.console(f"Ping results: {self.ping_tasks2[i][6]} success, {self.ping_tasks2[i][7]} failed out of {self.ping_tasks2[i][2]}\nAvarage time was {self.ping_tasks2[i][5]/self.ping_tasks2[i][6]}")
                        self.ping_results2.append(f"{self.ping_tasks2[i][8]}*Successful".split("*"))
                        setRuntimeDataPing(self.ping_tasks2[i][0], str(int(self.ping_tasks2[i][5]/self.ping_tasks2[i][6]*1000)))
                    self.ping_tasks2.pop(i)  # torles
            for i in range(0, len(self.ping_tasks2)):  # pingtimecalc
                if self.ping_tasks2[i][3] < self.ping_tasks2[i][4]:  # ha pingstart hamarabb volt mint pingend
                    pingtime = self.ping_tasks2[i][4] - self.ping_tasks2[i][3]  # calc pingtime
                    if pingtime < ping_timeout:  # ha nem timoutolt
                        log.console(pingtime)
                        self.ping_tasks2[i][5] = self.ping_tasks2[i][5] + pingtime  # add to pingtimesum
                        self.ping_tasks2[i][6] += 1  # increase succescounter by 1
                    else:
                        log.warning(f"{self.ping_tasks2[i][0]} lassan valaszolt: {pingtime} seconds")
                        self.ping_tasks2[i][7] += 1  # add one to timeout

                if self.ping_tasks2[i][3] > self.ping_tasks2[i][4] and self.ping_tasks2[i][3] + ping_timeout < time.monotonic() and self.ping_tasks2[i][3] != 1:  # nem jött válasz timout (ha pingtart nagyobb mint pingend (elozobol) ÉS pingstart + timout kevesebb mint mostani ido ÉS nem kezdőállapot
                    self.ping_tasks2[i][7] += 1  # add one to timout
            for i in range(0, len(self.ping_tasks2)):  # send ping
                if (self.ping_tasks2[i][3] < self.ping_tasks2[i][4] and self.ping_tasks2[i][4] - self.ping_tasks2[i][3] < ping_timeout) or (self.ping_tasks2[i][3] > self.ping_tasks2[i][4] and self.ping_tasks2[i][3] + ping_timeout < time.monotonic()):  # ha lepingelt vagy timoutolt
                    topic = None
                    for j in range(0, len(configtable)):
                        if self.ping_tasks2[i][0] == configtable[j][0]:
                            topic = configtable[j][1]
                    if topic is not None:
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

    # IDEA BUT I DONT I WILL DO IT CAUSE ITS NOT NEEDED   #kesz egy passziv availability check, ha eszkoz probalja olvasni de nem sikerul az error mellet visszakuld egy uzit h not avaible, ezt kene kiboviteni egy actival h rakerdez a szerver es ugy megnezi mindegyik sensort esetleg
    def JSONdispatch(self, params):
        if params[0] == "SENSOR" and params[1] == "Ping":
            return self.returnPingSensorJson(params[1], params[2], params[3], params[4], params[5], params[6], params[7])
        elif params[0] == "SENSOR":
            return self.returnSensorJSON(params[1], params[2], params[3], params[4], params[5], params[6], params[7])
        elif params[0] == "BINARY_SENSOR":
            return self.returnBinarySensorJSON(params[1], params[2], params[3], params[4], params[5], params[6])
        elif params[0] == "SWITCH":
            return self.returnSwitchJson(params[1], params[2], params[3], params[4], params[5], params[6])
        elif params[0] == "LIGHT":
            return self.returnLightJSON(params[1], params[2], params[3], params[4], params[5], params[6])
        elif params[0] == "LIGHTRGB":
            return self.returnLightRGBJSON(params[1], params[2], params[3], params[4], params[5], params[6])

    def returnPingSensorJson(selfself, name, unique_id, state_topic, unit_of_measurement, entity_category, icon, availability_topic):
        if icon == "ICON":
            icon = "mdi:lan"
        return(f'"icon":"{icon}","name":"{name}","unique_id":"{unique_id}","state_topic":"{state_topic}","unit_of_measurement":"{unit_of_measurement}","entity_category":"diagnostic","availability":' + '{' + f'"topic":"{availability_topic}"' + '}')  # entity categroyt ki kellett venni mert nem ment tole a discovery ("entity_category":"{entity_category}",), added state class to hopefully solve long term statistics storage issue

    def returnSensorJSON(self, name, unique_id, state_topic, unit_of_measurement, entity_category, icon, availability_topic):
        if icon == "ICON":
            icon = "mdi:leak"
        return(f'"icon":"{icon}","name":"{name}","unique_id":"{unique_id}","state_topic":"{state_topic}","unit_of_measurement":"{unit_of_measurement}","state_class":"measurement","availability":' + '{' + f'"topic":"{availability_topic}"' + '}')  # entity categroyt ki kellett venni mert nem ment tole a discovery ("entity_category":"{entity_category}",), added state class to hopefully solve long term statistics storage issue

    def returnLongDeviceJSON(self, name, identifier, manufacturer, model, sw_version, hw_version, configurl):
        return(f'"device":' + '{' + f'"name":"{name}","identifiers":["{identifier}"],"manufacturer":"{manufacturer}","model":"{model}","hw_version":"{hw_version}","sw_version":"{sw_version}"' + '}')   # config urlt ki kellett venni mert nem mukodott tole a discovery (,"configuration_url":"{configurl}")

    def returnBinarySensorJSON(self, name, unique_id, state_topic, entity_category, icon, availability_topic):  # platform has to be binary sensor
        if icon == "ICON":
            icon = "mdi:leak"
        return(f'"platform":"binary_sensor","icon":"{icon}","name":"{name}","unique_id":"{unique_id}","payload_on":"1","payload_off":"0","state_topic":"{state_topic}","availability":' + '{' + f'"topic":"{availability_topic}"' + '}')  # entity categroyt ki kellett venni mert nem ment tole a discovery ("entity_category":"{entity_category}",)

    def returnLightJSON(self, name, unique_id, state_topic, entity_category, icon, availability_topic):  # rgb not supported és implementalni rendesen
        if icon == "ICON":
            icon = "mdi:lightbulb"
        return(f'"platform":"light","icon":"{icon}","name":"{name}","unique_id":"{unique_id}","state_topic":"{state_topic}/state","brightness_command_topic":"{state_topic}/brightness_command","brightness_state_topic":"{state_topic}/brightness_state","command_topic":"{state_topic}/command","availability":' + '{' + f'"topic":"{availability_topic}"' + '}')  # entity categroyt ki kellett venni mert nem ment tole a discovery ("entity_category":"{entity_category}",)

    def returnLightRGBJSON(self, name, unique_id, state_topic, entity_category, icon, availability_topic):
        if icon == "ICON":
            icon = "mdi:lightbulb"
        return(f'"platform":"light","icon":"{icon}","name":"{name}","unique_id":"{unique_id}","command_topic":"{state_topic}/command","state_topic":"{state_topic}/state","brightness_command_topic":"{state_topic}/brightness_command","brightness_state_topic":"{state_topic}/brightness_state","rgb_command_topic":"{state_topic}/rgb_command","rgb_state_topic":"{state_topic}/rgb_state","availability":' + '{' + f'"topic":"{availability_topic}"' + '}')  # entity categroyt ki kellett venni mert nem ment tole a discovery ("entity_category":"{entity_category}",)


    def returnSwitchJson(self, name, unique_id, state_topic, entity_category, icon, availability_topic):
        if icon == "ICON":
            icon = "mdi:toggle-switch-variant"
        return(f'"platform":"switch","icon":"{icon}","name":"{name}","unique_id":"{unique_id}","state_topic":"{state_topic}","command_topic":"{state_topic}/command","availability":' + '{' + f'"topic":"{availability_topic}"' + '}')  # entity categroyt ki kellett venni mert nem ment tole a discovery ("entity_category":"{entity_category}",)

    # hassImportData per line: "ENTITY",NAME,UNIQUE_ID,STATE_TOPIC,UNIT_OF_MEASUREMENT,ENTITY_CATEGORY,ICON,AVAILABILITY_TOPIC          #uniqeIDba benne van a MAC
    # hassImprotData per line: "DEVICE",NAME,IDENTIFIER,MANUFACTURER,MODEL,SWVERSION,HWVERSION,CONFIGURL                                #name-be benne van a MAC
    loadedData = []

    devices = []
    entities = []

    hassDomains = ["SENSOR", "BINARY_SENSOR", "SWITCH", "LIGHT", "LIGHTRGB"] #lightrgb nem hass domain, csak igy van itt definialva h rgb vagy bw
    nonDefinedVars = ["UNIT_OF_MEASUREMENT", "ENTITY_CATEGORY", "ICON", "MANUFACTURER", "MODEL", "SWVERSION", "HWVERSION", "CONFIGURL",  "UNIQUE_ID", "STATE_TOPIC"]  # , "ENTITY" ki lett véve

    defaultDataByDomainList = [["SENSOR", "Sensor", "mdi:leak"],
                               ["BINARY_SENSOR", "Sensor", "mdi:toggle-switch"],
                               ["SWITCH", "Control", "mdi:toggle-switch-variant"],
                               ["LIGHT", "Control", "mdi:lightbulb"],
                               ["LIGHTRGB", "Control", "mdi:lightbulb"],
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
        log.info("HASS init started")
        for entry in self.defautlUOMByType:
            if len(entry) > 3:
                self.dualSensor.append(entry)
                self.dualSensorSimple.append(entry[0])
        with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
            log.console("Reading hassImportData file")
            dfile.seek(0)
            linecount = 0  # sorok számozása
            while line := dfile.readline():
                linecount += 1  # sor szám +1
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
        log.info("HASS init finished")

    def __del__(self):
        log.warning("Instance of HASS class was destroyed")

    def reloadData(self):
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
                #SENSOR,LightSensor,mcass_3c-ab-72-96-52-f4_LightSensor,MCASS/hass/RP2040ETH_1/LightSensor,adc,Sensor,mdi:leak,mcass/hass/RP2040ETH_1/LightSensor/available
                dfile.write(f"SENSOR,Ping,mcass_{mac.lower()}_Ping,MCASS/hass/{mac.upper().replace('-', '_')}/Ping,ms,Diagnostic,mdi:lan,mcass/hass/{mac.upper().replace('-', '_')}/Ping/available\n")
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
                                    dataLine = f"{entity.split('@')[1].split('(')[1][:-1].upper()},{entity.split('@')[1].split('(')[0]}_{name},mcass_{mac.lower()}_{entity.split('@')[1].split('(')[0]}_{name},MCASS/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1].split('(')[0]}/{name},UNIT_OF_MEASUREMENT,ENTITY_CATEGORY,ICON,MCASS/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1].split('(')[0]}/available\n"
                                    with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
                                        dfile.write(dataLine)
                            else:  # ha simpla sensor
                                try:
                                    dataLine = f"{entity.split('@')[1].split('(')[1][:-1].upper()},{entity.split('@')[1].split('(')[0]},mcass_{mac.lower()}_{entity.split('@')[1].split('(')[0]},MCASS/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1].split('(')[0]},UNIT_OF_MEASUREMENT,ENTITY_CATEGORY,ICON,mcass/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1].split('(')[0]}/available\n"
                                except:
                                    dataLine = f"ENTITY,{entity.split('@')[1]},mcass_{mac.lower()}_{entity.split('@')[1]},MCASS/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1]},UNIT_OF_MEASUREMENT,ENTITY_CATEGORY,ICON,mcass/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1]}/available\n"
                                with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
                                    dfile.write(dataLine)
                        else:  # ha nem sensor a domain
                            try:
                                dataLine = f"{entity.split('@')[1].split('(')[1][:-1].upper()},{entity.split('@')[1].split('(')[0]},mcass_{mac.lower()}_{entity.split('@')[1].split('(')[0]},MCASS/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1].split('(')[0]},ENTITY_CATEGORY,ICON,mcass/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1].split('(')[0]}/available\n"
                            except:
                                dataLine = f"ENTITY,{entity.split('@')[1]},mcass_{mac.lower()}_{entity.split('@')[1]},MCASS/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1]},ENTITY_CATEGORY,ICON,mcass/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1]}/available\n"
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
                                dataLine = f"{entity.split('@')[1].split('(')[1][:-1].upper()},{entity.split('@')[1].split('(')[0]}_{name},mcass_{mac.lower()}_{entity.split('@')[1].split('(')[0]}_{name},MCASS/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1].split('(')[0]},UNIT_OF_MEASUREMENT,ENTITY_CATEGORY,ICON,mcass/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1].split('(')[0]}/available\n"
                                with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
                                    dfile.write(dataLine)
                        else:  # ha nincs domain megadva es nem is 2 erteku sensor
                            dataLine = f"ENTITY,{entity.split('@')[1]},mcass_{mac.lower()}_{entity.split('@')[1]},MCASS/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1]},ENTITY_CATEGORY,ICON,mcass/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1]}/available\n"
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
            if f"{dataLine.split(',')[2].replace('mcass', 'mcass_')}_Ping" in loadedDataUNIQUEs:
                print("")
            else:
                with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
                    dfile.write(f"SENSOR,Ping,mcass_{mac.lower()}_Ping,MCASS/hass/{mac.upper().replace('-', '_')}/Ping,ms,Diagnostic,mdi:lan,mcass/hass/{mac.upper().replace('-', '_')}/Ping/available\n")
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
                                    dataLine = f"{entity.split('@')[1].split('(')[1][:-1].upper()},{entity.split('@')[1].split('(')[0]}_{name},mcass_{mac.lower()}_{entity.split('@')[1].split('(')[0]}_{name},MCASS/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1].split('(')[0]}/{name},UNIT_OF_MEASUREMENT,ENTITY_CATEGORY,ICON,mcass/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1].split('(')[0]}/available\n"
                                    if dataLine.split(",")[2] in loadedDataUNIQUEs:
                                        continue
                                    else:
                                        with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
                                            dfile.write(dataLine)
                            else:  # ha simpla sensor
                                try:
                                    dataLine = f"{entity.split('@')[1].split('(')[1][:-1].upper()},{entity.split('@')[1].split('(')[0]},mcass_{mac.lower()}_{entity.split('@')[1].split('(')[0]},MCASS/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1].split('(')[0]},UNIT_OF_MEASUREMENT,ENTITY_CATEGORY,ICON,mcass/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1].split('(')[0]}/available\n"
                                except:
                                    dataLine = f"ENTITY,{entity.split('@')[1]},mcass_{mac.lower()}_{entity.split('@')[1]},MCASS/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1]},UNIT_OF_MEASUREMENT,ENTITY_CATEGORY,ICON,mcass/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1]}/available\n"
                                if dataLine.split(",")[2] in loadedDataUNIQUEs:
                                    continue
                                else:
                                    with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
                                        dfile.write(dataLine)
                        else:  # ha nem sensor a domain
                            try:
                                dataLine = f"{entity.split('@')[1].split('(')[1][:-1].upper()},{entity.split('@')[1].split('(')[0]},mcass_{mac.lower()}_{entity.split('@')[1].split('(')[0]},MCASS/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1].split('(')[0]},ENTITY_CATEGORY,ICON,mcass/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1].split('(')[0]}/available\n"
                            except:
                                dataLine = f"ENTITY,{entity.split('@')[1]},mcass_{mac.lower()}_{entity.split('@')[1]},MCASS/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1]},ENTITY_CATEGORY,ICON,mcass/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1]}/available\n"
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
                                dataLine = f"{entity.split('@')[1].split('(')[1][:-1].upper()},{entity.split('@')[1].split('(')[0]}_{name},mcass_{mac.lower()}_{entity.split('@')[1].split('(')[0]}_{name},MCASS/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1].split('(')[0]},UNIT_OF_MEASUREMENT,ENTITY_CATEGORY,ICON,mcass/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1].split('(')[0]}/available\n"
                                if dataLine.split(",")[2] in loadedDataUNIQUEs:
                                    continue
                                else:
                                    with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
                                        dfile.write(dataLine)
                        else:  # ha nincs domain megadva es nem is 2 erteku sensor
                            dataLine = f"ENTITY,{entity.split('@')[1]},mcass_{mac.lower()}_{entity.split('@')[1]},MCASS/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1]},ENTITY_CATEGORY,ICON,mcass/hass/{mac.upper().replace('-', '_')}/{entity.split('@')[1]}/available\n"
                            if dataLine.split(",")[2] in loadedDataUNIQUEs:
                                continue
                            else:
                                with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
                                    dfile.write(dataLine)
                else:
                    continue

    def removeRemoved(self):
        inHassImport = []
        with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
            log.console("Reading hassImportData file in removeRemoved")
            dfile.seek(0)
            linecount = 0  # sorok számozása
            while line := dfile.readline():
                linecount += 1  # sor szám +1
                inHassImport.append(line.rstrip().split(","))
# itt a lejjebbi for loopokat ha megcsinalod while-al, akkor minden kijön aminek ki kell első körben nem csak többen
# lényeg h meg kell csinlani h legalabb a "for element in inHassImport" resz while-al menjen
        for element in inHassImport: #for complete device removals
            inconfigtable = False
            for entry in configtable:
                if element[0] == "DEVICE":
                    if element[1].split("_")[1] == entry[0]:
                        inconfigtable = True
                else:
                    if element[3].split("/")[2].replace("_", "-") == entry[0]:
                        inconfigtable = True
            if inconfigtable is False: #remove everything with this mac from hassimportdata
                for item in inHassImport:
                    if element[0] == "DEVICE":
                        if element[1].split("_")[1] in item[1]:
                            inHassImport.remove(item)
                    else:
                        if element[3].split("/")[2] in item[3]:
                            inHassImport.remove(item)

        for element in inHassImport: #for individual entity removals
            inconfigtable = False
            for entry in configtable:
                if element[0] == "DEVICE":
                    inconfigtable = True
                elif element[0] == "SENSOR" and element[1] == "Ping":
                    if element[3].split("/")[2].replace("_", "-") == entry[0]:
                        inconfigtable = True
                else:
                    if element[3].split("/")[2].replace("_", "-") == entry[0]:
                        for entity in entry[2].split("/"):
                            if len(entity.split("@")[1].split("(")) > 1:
                                if element[3].split("/")[3] == entity.split("@")[1].split("(")[0]:
                                    inconfigtable = True
                            else:
                                if element[3].split("/")[3] == entity.split("@")[1]:
                                    inconfigtable = True
            if inconfigtable is False:
                #remove item form hassimportdata
                #print("remove", element)
                inHassImport.remove(element)

        #for entry in inHassImport:
            #print(entry)

        file = open("hassImportData.txt", "w", encoding='UTF-8')
        file.close()
        with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
            for line in inHassImport:
                if line[0] == "DEVICE" or line[0] == "SENSOR": #csak ez a 2 dolog 8 elemes a tobbi csak 7
                    linetowrite = f"{line[0]},{line[1]},{line[2]},{line[3]},{line[4]},{line[5]},{line[6]},{line[7]}"
                else:
                    linetowrite = f"{line[0]},{line[1]},{line[2]},{line[3]},{line[4]},{line[5]},{line[6]}"
                dfile.write(linetowrite)
                dfile.write("\n")

    def sendToHassIndex(self, index):
        entity = self.entities[index]
        entitydata = self.JSONdispatch(entity)
        mac = entity[2].split("_")[1]
        parentDevice = ""
        for device in self.devices:
            if device[1].split("_")[1] == mac.upper():
                parentDevice = device
        devicedata = self.returnLongDeviceJSON(parentDevice[1], parentDevice[2], parentDevice[3], parentDevice[4], parentDevice[5], parentDevice[6], parentDevice[7])
        pubPayload = "{" + f"{entitydata},{devicedata}" + "}"
        if entity[0].upper() == "LIGHTRGB":
            try:  # homeassistant/domain(switch,sensor,stb)/id(mac?)/config
                pubTopic = f"homeassistant/light/{entity[3].replace('/hass', '').replace('/', '_').lower()}/config"  # homeassistant/binary_sensor/MCASS_RP2040ETH_1_Switch/config
            except Exception as e:
                log.error(f"Exception occurred when creating MQTT Discovery topic for an RGB Light device: {e}")
        else:
            try:  # homeassistant/domain(switch,sensor,stb)/id(mac?)/config
                pubTopic = f"homeassistant/{entity[0].lower()}/{entity[3].replace('/hass', '').replace('/', '_').lower()}/config"  # homeassistant/binary_sensor/MCASS_RP2040ETH_1_Switch/config
            except:
                pubTopic = f"homeassistant/{entity[1].lower()}/{entity[3].replace('/hass', '').replace('/', '_').lower()}/config"
                log.warning(f"No domain defined for entity {entity[1]}")
                #ezt a fenti 3 sort nem vágom mi a gyász
        send = True
        for element in self.nonDefinedVars:
            if element in pubPayload:
                send = False
                log.warning(f"Config was not sent to MQTT Discovery, due to missing information: {pubPayload}")
        if send:
            client.publish(pubTopic, pubPayload)

    def removeFromHass(self, domain, name): #MCASS/hass/RP2040ETH_1/LightSensor
        #mcass_3c_ab_72_96_52_f4_lightsensor
        #MCASS/hass/3C_AB_72_96_52_F4/Ping
        client.publish(f"homeassistant/{domain}/{name}/config", "{}")



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
                    inhass.append(element)
            indexOfEntityToBeSentToHass = []  # currently there's no reliable way to check if a device exist in hass, since the API does not return unique id, only entity_id, which is created by "<device_name>_<entity_name>", because of this currently we are going by entity id
            for i in range(0, len(self.entities)):
                for j in range(0, len(inhass)):
                    if str(f'{"_".join(self.entities[i][2].split("_", 2)[:2])}_{self.entities[i][1].split("(")[0].lower()}'.replace("-", "_")) == str(inhass[j]).split('entity_id":"')[1].split(",")[0][:-1].split(".")[1]:
                        indexOfEntityToBeSentToHass.append(int(i))
            for i in range(0, len(self.entities)):
                if i in indexOfEntityToBeSentToHass:
                    continue
                else:
                    self.sendToHassIndex(i)
        except Exception as e:
            log.error(e)

    def removeSyncToHass(self):
        print("in removeSyncToHass")
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
            inhassShort = []
            for j in range(0, len(inhass)):
                inhassShort.append(str(inhass[j]).split('entity_id":"')[1].split(",")[0][:-1].split(".")[1])
            ToBeRemovedFromHass = inhassShort.copy()  # currently there's no reliable way to check if a device exist in hass, since the API does not return unique id, only entity_id, which is created by "<device_name>_<entity_name>", because of this currently we are going by entity id

            for i in range(0, len(self.entities)):
                if str(f'{"_".join(self.entities[i][2].split("_", 2)[:2])}_{self.entities[i][1].split("(")[0].lower()}'.replace("-", "_")) in inhassShort:
                    ToBeRemovedFromHass.remove(str(f'{"_".join(self.entities[i][2].split("_", 2)[:2])}_{self.entities[i][1].split("(")[0].lower()}'.replace("-", "_")))

            for item in ToBeRemovedFromHass:
                for element in inhass:
                    if item in element:
                        domain = str(element).split('entity_id":"')[1].split(",")[0].split(".")[0]
                        name = str(element).split('entity_id":"')[1].split(",")[0][:-1].split(".")[1]
                        self.removeFromHass(domain, name)

        except Exception as e:
            if "name 'client' is not defined" in str(e):
                log.warning("MQTT has not started yet, but removeSyncToHass tried to use it")
            else:
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
                    if self.entities[i][0] == "SENSOR":
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
        tempHold = []
        newlist = []
        with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
            dfile.seek(0)
            linecount = 0  # sorok számozása
            while line := dfile.readline():
                linecount += 1  # sor szám +1
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
        print("in updatedata")
        MANUFACTURER = "MANUFACTURER"
        MODEL = "MODEL"
        HW_VERSION = "HW_VERSION"
        SW_VERSION = "SW_VERSION"
        CONFIGURL = "CONFIGURL"
        ENTITY_CATEGORY = "ENTITY_CATEGORY"
        ICON = "ICON"
        UNIT_OF_MEASUREMENT = "UNIT_OF_MEASUREMENT"
        for data in values.split(","):
            param = data.split("=")[0]
            value = data.split("=")[1]
            if param == "MANUFACTURER":
                MANUFACTURER = value
            if param == "MODEL":
                MODEL = value
            if param == "HW_VERSION":
                HW_VERSION = value
            if param == "SW_VERSION":
                SW_VERSION = value
            if param == "CONFIGURL":
                CONFIGURL = value
            if param == "ENTITY_CATEGORY":
                ENTITY_CATEGORY = value
            if param == "ICON":
                ICON = value
            if param == "UNIT_OF_MEASUREMENT":
                UNIT_OF_MEASUREMENT = value
        tempHold = []
        newlist = []
        with open("hassImportData.txt", "a+", encoding='UTF-8') as dfile:
            dfile.seek(0)
            linecount = 0  # sorok számozása
            while line := dfile.readline():
                linecount += 1  # sor szám +1
                tempHold.append(line.rstrip())
        if len(device.split("@")) == 2:  # for sensors
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
        else:  # for the actual device
            for entry in tempHold:
                if entry.split(",")[0] == "DEVICE":
                    if entry.split(",")[1].split("_")[1].upper() == device.upper():
                        #newlist.append(entry.replace("MANUFACTURER", MANUFACTURER).replace("MODEL", MODEL).replace("HW_VERSION", HW_VERSION).replace("SW_VERSION", SW_VERSION).replace("CONFIGURL", CONFIGURL))
                        helpline = ""
                        helplist = entry.split(",")
                        if MANUFACTURER != "MANUFACTURER":
                            helplist[3] = MANUFACTURER
                        if MODEL != "MODEL":
                            helplist[4] = MODEL
                        if HW_VERSION != "HW_VERSION":
                            helplist[5] = HW_VERSION
                        if SW_VERSION != "SW_VERSION":
                            helplist[6] = SW_VERSION
                        if CONFIGURL != "CONFIGURL":
                            helplist[7] = CONFIGURL
                        helpline = helplist[0]
                        for i in range(1, len(helplist)):
                            helpline = f"{helpline},{helplist[i]}"
                        newlist.append(helpline)
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
            for i in range(self.asketfordev % len(self.devices), len(self.devices)):  # 0 hosszusagu devicedata listaval elhasal
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
                            peripheralType = peripheral.split("@")[0]
                            domain = peripheral.split("@")[1].split("(")[1][:-1]
                    except:
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
        if sensi != "":
            sensi = f"_{sensi}"
        ha.updateData(f"{mac}@{name}{sensi}", f"UNIT_OF_MEASUREMENT={UNIT_OF_MEASUREMENT},ENTITY_CATEGORY={ENTITY_CATEGORY},ICON={ICON}")

    startedPings = []  # ID, unique id

    def checkAvailablity(self):
        for device in self.devices:
            self.startedPings.append(f"{p.pingstart(device[1].split('_')[1], 4)}*{device[2]}".split("*"))

    def getAvail(self):
        global activeErrors
        global configtable
        wasunavailable = False
        for entry in self.startedPings:
            result = p.get_result(entry[0])
            if result is None:
                continue
            else:
                if result == "Failed":
                    self.setAllSensorsOfDeviceToOffline(entry[1])
                    deviceMacHelp = entry[1].split("mcass")[1].upper()
                    if activeErrorHandler(f"{deviceMacHelp} offline", "Device did not respond to ping request", "add"):
                        log.info(f'Device {deviceMacHelp} added to activeErrors list with reason:"Device offline", added by HASS:getAvail')
                    #activeErrors.append(f"{deviceMacHelp}*offline".split("*"))
                    log.error(f"Availability check failed for device {entry[1]}")  # get the avail topic for it and send unavaible message
                elif result == "Successful":
                    #inlastAmm = 10  # might have to set higher if using multiple devices
                    #if log.inLastX(inlastAmm, f"Availability check failed for device {entry[1]}") is True:
                        #log.info(f"Availability check succeeded for device {entry[1]} that was previously unavailable") # ez folyamat ezt irja ki, azóta kapott egy inlastx-et maga elé
                    ### de igazabol ez már ki is van utve mert amikor jön érték egy eszköztől, ha benne volt az utolso x logba h device is offline akkor megy forcevalues
                    #log.console(f"Availability check succeeded for device {entry[1]}")  # get the avail topic for it and send avaible message

                    deviceMacHelp = entry[1].split("mcass")[1].upper()
                    if activeErrorHandler(f"{deviceMacHelp} offline", "Device did not respond to ping request", "remove"):
                        log.info(f'Device {deviceMacHelp} removed from activeErrors list, device responded, removed by HASS:getAvail')
                        wasunavailable = True

                    #for i in range(0, len(activeErrors)):
                        #if activeErrors[i][0] == deviceMacHelp:
                            #log.info(f"Availability check succeeded for device {entry[1]} that was previously unavailable")
                            #activeErrors.pop(i)
                            #wasunavailable = True
                            #for element in configtable:
                                #if element[0] == deviceMacHelp:
                                    #client.publish(element[1], "PRTCL_FORCEVALUES")
                                    #log.info(f"Ping failed for device mcass{deviceMacHelp} previously, sending force values command")
                            #continue
                    if wasunavailable:
                        log.info(f"Availability check succeeded for device {entry[1]} that was previously unavailable")
                        for element in configtable:
                            if element[0] == deviceMacHelp:
                                client.publish(element[1], "PRTCL_FORCEVALUES")
                                log.info(f"Ping failed for device mcass{deviceMacHelp} previously, sending force values command")
                            continue
                    elif wasunavailable == False:
                        log.console(f"Availability check succeeded for device {entry[1]}")

                else:
                    log.error(f'Unknown result given to ping: "{result}"')
            self.startedPings.remove(entry)

    def setAllSensorsOfDeviceToOffline(self, device):
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
            if entry[0] == "SENSOR":
                if Domain != "":  # ha megvan a domain is
                    if entry[1] == SensorName and entry[0] == Domain.upper() and entry[2] == f"mcass_{Device.lower()}_{SensorName}":
                        return entry[7]
                else:  # ha nics domain
                    if entry[1] == SensorName and entry[2] == f"mcass_{Device.lower()}_{SensorName}":
                        return entry[7]
            else:
                if Domain != "":  # ha megvan a domain is
                    if entry[1] == SensorName and entry[0] == Domain.upper() and entry[2] == f"mcass_{Device.lower()}_{SensorName}":
                        return entry[6]
                else:  # ha nics domain
                    if entry[1] == SensorName and entry[2] == f"mcass_{Device.lower()}_{SensorName}":
                        return entry[6]

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

    def getDeviceDatas(self, mac):
        for device in self.devices:
            if mac == device[1].replace("MCASS_", ""):
                return(device[3], device[4], device[5], device[6], device[7])


ha = ""
if HaState == "ON":
    log.info("Starting HASS...")
    ha = HASS()
    ha.kiirOnlyNew()
    ha.reloadData()
    #ha.removeSyncToHass()
    #ha.removeRemoved()
else:
    log.info("Skipping the startup off HASS, as it is not configured")


class ProtocolBook:
    protocollist = []  # protocollist=[protpointer, protname, type(short,normal,long,everycycle) or off]
    protDict = {}
    executeProts = ["protShort", "protNorm", "protLong", "protocollist", "protDict", "executeProts", "everyLoop", "dailyCheck", "helper", "setOverRide", "changeFreq", "getID", "getDescription"]  # protocols to exclude from list, whih dont need automatic running

    helper = 0

    def __init__(self):
        var = 1
        for protocol in dir(ProtocolBook):
            if "__" not in protocol and protocol not in self.executeProts:
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
                elif protocol[-1] == "d":  # daily
                    self.protocollist.append(str(f"{var}*{protocol}*daily").split("*"))
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
            if protocol[0][0] == "W" and protocol[0][1] == "C":
                if webcontrol is False:
                    log.info(f"Switching off protocol {protocol[1]} with id of {protocol[0]} due to WEBCONTROL setting being turned off")
                    protocol[2] = "off"

    def protShort(self):
        for i in range(0, len(self.protocollist)):
            if self.protocollist[i][2] == "short":
                self.protDict[self.protocollist[i][0]](self, "none")

    def protNorm(self):
        for i in range(0, len(self.protocollist)):
            if self.protocollist[i][2] == "normal":
                self.protDict[self.protocollist[i][0]](self, "none")

    def protLong(self):
        for i in range(0, len(self.protocollist)):
            if self.protocollist[i][2] == "long":
                self.protDict[self.protocollist[i][0]](self, "none")

    def everyLoop(self):
        for i in range(0, len(self.protocollist)):
            if self.protocollist[i][2] == "every":
                self.protDict[self.protocollist[i][0]](self, "none")

    def dailyCheck(self):
        global isFinished
        for i in range(0, len(self.protocollist)):
            if self.protocollist[i][2] == "daily":
                self.protDict[self.protocollist[i][0]](self, "none")
        isFinished = True

    def changeFreq(self, name, freq):
        if "_OR" in freq:
            log.error("Can't change frequency into override state from any automatic setting as it could cause a soft-lock")
            return False
        for protocol in self.protocollist:  # nezd vegig a listat
            if protocol[1] == name and "_OR" not in protocol[2]:  # ha a nev egyezik a masikeval és nincs benne h OR (override)
                if protocol[2] != freq:
                    protocol[2] = freq  # rakd at normalra
                    log.info(f"Changed frequency of protocol {name} to {freq}")
                    return True
            elif protocol[1] == name and "_OR" in protocol[2]:
                log.warning(f"Frequency of protocol {name} is currently overridden, can't change")
                return False

    def setOverRide(self, name, freq):
        for protocol in self.protocollist:  # nezd vegig a listat
            if protocol[1] == name:  # ha a nev egyezik a masikeval és nincs benne h OR (override)
                if protocol[2] != freq:
                    protocol[2] = freq  # rakd at normalra
                    log.info(f"Changed frequency of protocol {name} to {freq}")
                    return True
        return False


    def getID(self, protocolName):
        for i in range(0, len(self.protocollist)):
            if self.protocollist[i][1] == protocolName:
                return(self.protDict[self.protocollist[i][0]](self, "getID"))
    def getDescription(self, protocolName):
        for i in range(0, len(self.protocollist)):
            if self.protocollist[i][1] == protocolName:
                return(self.protDict[self.protocollist[i][0]](self, "getDesc"))

    def frequencyCheckern(self, command):  # !!!!!! lentebb egy ifbe ez a név van ctrl+c ctrl+v-zve, ha itt atirod ird at ott is
        if command == "getID":
            return "HA1"
        elif command == "getDesc":
            return "Changes the frequency of dataGetter, and it's own, depending on the ammount of missing data in the data used to sync to HASS"
        FUNCTION_NAME = "frequencyCheckern"
        NAME_OF_SISTER_FUNC = "dataGettern"
        AmmOfMissingData = ha.getAmmountOfMissing()
        if AmmOfMissingData > 25:  # ha 25%nal tobb hianyzik
            if self.changeFreq(NAME_OF_SISTER_FUNC, "normal"):
                log.info("Ammount of missing data is high, switching dataGetter protocol to normal")
            if self.changeFreq(FUNCTION_NAME, "normal"):
                log.info("dataGetter protocol is going, swithing frequencyChecker to normal")
        elif AmmOfMissingData > 0:  # ha 25%nal kevesebb hianyzik
            if self.changeFreq(NAME_OF_SISTER_FUNC, "long"):
                log.info("Ammount of missing data is under 25%, switching dataGetter protocol to long")
            if self.changeFreq(FUNCTION_NAME, "normal"):
                log.info("dataGetter protocol is going, swithing frequencyChecker to normal")
        elif AmmOfMissingData == 0:  # semennyi enm hianyzik
            if self.changeFreq(NAME_OF_SISTER_FUNC, "off"):
                log.info("Ammount of missing data is none, switching dataGetter off")
            if self.changeFreq(FUNCTION_NAME, "long"):
                log.info("dataGetter protocol is stopped, swithing frequencyChecker to long")

        #for protocol in self.protocollist:  # nezd vegig a listat
        #    if protocol[1] == NAME_OF_SISTER_FUNC:  # ha a neve ugyanaz mint a masiknak
        #        if protocol[2] == "off":  # es ki van kapcsolva
        #            if self.changeFreq(FUNCTION_NAME, "long"):
        #                log.info("dataGetter protocol is stopped, swithing frequencyChecker to long")
        #        if protocol[2] != "off":  # ha megy
        #            if self.changeFreq(FUNCTION_NAME, "normal"):
        #                log.info("dataGetter protocol is going, swithing frequencyChecker to normal")

    def dataGettern(self, command):  # !!!!! a fenti protocolba stringkent ez a func name van megadva, ha itt atirod ird at ott is  # ha az adatok 50%a hianyzik normal, ha 25%a akkor long, ha semmi akkor off
        attempts = 0
        if command == "getID":
            return "HA2"
        elif command == "getDesc":
            return "Requests and updates default data of entities in list for syncing to HASS"
        data = ha.getDataForRequest()
        while data is None and attempts < 6:
            data = ha.getDataForRequest()
            attempts += 1
        if data is None:
            return
        try:
            if len(data.split("@")) == 2:
                ha.getDefaultData(data.split("@")[0], data.split("@")[1])  # ez megy internalba
            else:
                for device in configtable:
                    if device[0] == data.upper():
                        client.publish(device[1], "PRTCL_GETINFO:SELF")  # get the data of the device itself
        except Exception as e:
            if str(e) == "'NoneType' object has no attribute 'split'":
                log.error(f"Error occured in dataGettern protocol, no data was returned by getDataForRequest() from HASS")
            else:
                log.error(f"Unkown error occured in dataGettern protocol, error message was: {str(e)}")

    def avCheckerl(self, command):
        if command == "getID":
            return "HA3"
        elif command == "getDesc":
            return "Starts ping for defined devices"
        ha.checkAvailablity()

    def avReportn(self, command):
        if command == "getID":
            return "HA4"
        elif command == "getDesc":
            return "Checks the result of previously started pings, and handles them accordingly"
        ha.getAvail()

    def HassSyncl(self, command):
        if command == "getID":
            return "HA5"
        elif command == "getDesc":
            return "Checks what device or sensor is not found in HASS, and syncs it into HASS"
        if SyncOnlyWhenOnTestServer:
            if HassIP == "192.168.0.150":
                ha.syncToHass()
            else:
                log.error("SyncOnlyWhenOnTestServer is turned on, and IP is not the test server ip, hass sync functions will not work")
        else:
            ha.syncToHass()

    def RemoveHassSyncl(self, command):
        if command == "getID":
            return "HA8"
        elif command == "getDesc":
            return "Checks what device or sensor is found in HASS, but removed locally, and removes it from HASS"
        if SyncOnlyWhenOnTestServer:
            if HassIP == "192.168.0.150":
                ha.removeSyncToHass()
            else:
                log.error("SyncOnlyWhenOnTestServer is turned on, and IP is not the test server ip, hass sync functions will not work")
        else:
            ha.removeSyncToHass()

    def kiirOnylNewAutoRunl(self, command):
        if command == "getID":
            return "HA7"
        elif command == "getDesc":
            return "Adds new data from configtable to hassImportData"
        ha.kiirOnlyNew()

    def removeRemovedAutoRunl(self, command):
        if command == "getID":
            return "HA9"
        elif command == "getDesc":
            return "Removes data from hassImportData that has been removed from configtable"
        ha.removeRemoved()
    def HassSyncBackl(self, command):
        if command == "getID":
            return "HA6"
        elif command == "getDesc":
            return "Syncronises the icon change from HASS to local data"
        ha.syncIconFromHass()

    def checkDataValidityd(self, command):
        if command == "getID":
            return "DVC"
        elif command == "getDesc":
            return "Asks for the validity of stored data from given device"
        for entry in configtable:
            datas = ha.getDeviceDatas(entry[0])
            client.publish(entry[1], f"PRTCL_DVC_ASK:{datas[0]},{datas[1]},{datas[2]},{datas[3]},{datas[4]}")
            time.sleep(15)

    def getRuntimeDatForWebn(self, command):
        if command == "getID":
            return "WC1"
        elif command == "getDesc":
            return "Asks for runtime data from given device if there is unkown data"
        for i in range(self.helper % len(deviceData), len(deviceData)):  # 0 hosszusagu devicedata listaval elhasal
            self.helper += 1
            ammofna = 0
            for data in deviceData[i]:
                if data == "n/a":
                    ammofna += 1
            if ammofna > 1:
                data = get_device_config(deviceData[i][0])
                client.publish(data[1], "PRTCL_GETINFO:RUNTIME")
                break
            else:
                continue

    def getRuntimeDatForWebFrequencyManagerl(self, command):
        if command == "getID":
            return "WC2"
        elif command == "getDesc":
            return "Changes the frequency of getRuntimeDatForWebn depending of ammount of missing data in runtime data"
        empty = 0
        filled = 0
        for entry in deviceData:
            for element in entry:
                if element == "n/a":
                    empty += 1
                else:
                    filled += 1
        if empty != 0:
            missingrate = empty/(filled+empty)
        else:
            missingrate = 1

        if missingrate < 0.75:
            if self.changeFreq("getRuntimeDatForWebn", "normal"):
                log.info("Ammount of missing data is high in deviceData, switching getRuntimeDatForWebn protocol to normal")

        elif missingrate > 0.75 and missingrate != 1:
            if self.changeFreq("getRuntimeDatForWebn", "long"):
                log.info("Ammount of missing data is moderate in deviceData, switching getRuntimeDatForWebn protocol to long")

        else:  # ha 1 az osztas eredmenye szal minden megvan
            if self.changeFreq("getRuntimeDatForWebn", "off"):
                log.info("No data is missing in deviceData, switching getRuntimeDatForWebn protocol off")

    def MQTTwatchdogn(selfs, command):  # normalba van de lehet hogy le lesz veve shortba (5 sec vs 0.5 sec)
        global activeErrors
        global lastMessageTime
        global lastMessageAvgTime
        global selfTestHang
        if command == "getID":
            return "MW1"
        elif command == "getDesc":
            return "Watchdog function for MQTT, self test"
        #get last message time
        messageTimeDiffs = []
        avgtimehelper = 0
        for i in range(0, 13):
            if lastMessageTime[i] == 0 or lastMessageTime[i+1] == 0:
                continue
            else:
                messageTimeDiffs.append(lastMessageTime[i]-lastMessageTime[i+1])
        for element in messageTimeDiffs:
            avgtimehelper = avgtimehelper+element
        if len(messageTimeDiffs) != 0:
            if avgtimehelper / len(messageTimeDiffs) > 15:
                lastMessageAvgTime = 15
            else:
                lastMessageAvgTime = avgtimehelper / len(messageTimeDiffs)
        else:
            lastMessageAvgTime = 0

        #calc avg time from last 15 messages
            #if more then 15 sec, cap at 15sec  (lehet hogy 15 + "sajat valaszido" kene legyen a cap)


        if time.monotonic() - lastMessageTime[0] > lastMessageAvgTime*2 or lastMessageAvgTime == 0:
            if selfTestHang == True:
                log.error("Self test message was sent, but did not get received, or acknowledged")
                #activeErrors.append(f"{server_id} MQTT process*Self test message was not received".split("*"))
                if activeErrorHandler(f"{server_id} MQTT process", "Self test message was not received", "add"):
                    log.info(f'{server_id} MQTT process added to activeErrors list with reason: Self test message was not received, added by MQTTwatchdogn')
            client.publish(selftesttopic, f"Self test message sent, due to not receiving message within given timeframe ({lastMessageAvgTime*2})")
            selfTestHang = True
        #if no message within the last avg*2 sec
            #send selt test message


log.info("Starting ProtocolBook...")
prot = ProtocolBook()

log.info("Starting MQTT...")
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
client.username_pw_set(username=username, password=password)

def on_connect(client, userdata, flags, reasonCode, properties):
    if reasonCode == "Success":
        log.info("Connection successful")
        subscribe()
    else:
        if username == "" or password == "":
            log.error("Username or password for MQTT broker was not provided")
        elif reasonCode == "Not authorized":
            log.error("MQTT connection attempt failed, user not authorized")
        else:
            log.error(f"MQTT connection attempt returned code {reasonCode}")

client.on_connect = on_connect

log.info(f"Trying to connect to server: {broker}")
while True:
    try:
        client.connect(broker, port)
    except Exception as e:
        #log.error(f"Connection failed: {e}")
        continue
    #log.info("Connection succesful")
    break


def extract_address(message):
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


delayResponseWithSecond = 0.25


def on_message(client, userData, msg):
    global selfTestHang
    global lastMessageTime
    log.console(f"Message ({msg.payload}) arrived from ({msg.topic})")
    #lastMessageTime.pop(14)
    for i in reversed(range(0, 13)):
        lastMessageTime[i+1] = lastMessageTime[i]
    lastMessageTime[0] = time.monotonic()

    if msg.topic == selftesttopic and "Self test message sent, due to not receiving message within given timeframe" in str(msg.payload):
        selfTestHang = False
        #for i in range(0, len(activeErrors)):
            #if activeErrors[i][0] == f"{server_id} MQTT process":
                #log.info("Received self test message, removing activeError")
                #activeErrors.pop(i)
        if activeErrorHandler(f"{server_id} MQTT process", "Self test message was not received", "remove"):
            log.info("Received self test message, removed activeError status, removed by on_message")

    if msg.topic == negotopic and "PRTCL_ASK_CHNL" in str(msg.payload):
        client.publish(negotopic, f"PRTCL_NEGO_ANSW:CNFGREQ*{configreqtopic}:CNFGREPL*{configrepltopic}:DVC*{devicetopic}")

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
                log.info(f"Device {configtable[i][0]} succesfully connected to own channel")
                time.sleep(delayResponseWithSecond)
                client.publish(configtable[i][1], "channel change ack")

    if "b'ping ok'" == str(msg.payload):
        for i in range(0, len(configtable)):
            if configtable[i][1] == msg.topic:
                address = configtable[i][0]
                p.pingend(address)

    if str(msg.payload) == "b'PRTCL_PINCONFIG:REQUEST'":  # pinconfig request ---#PRTCL_PINCONFIG:config
        for i in range(0, len(configtable)):
            if msg.topic == configtable[i][1]:
                time.sleep(delayResponseWithSecond)  # remove when fixed on RP2040ETH side
                client.publish(configtable[i][1], f"PRTCL_PINCONFIG:{domainRemover(configtable[i][2])}")

    if "PRTCL_READBACK:" in str(msg.payload):  # readback ---#PRTCL_READBACK:OK if ok ---#PRTCL_READBACK:NOPE if not good readback
        if "OK" not in str(msg.payload) and "NOPE" not in str(msg.payload):
            for i in range(0, len(configtable)):
                if msg.topic == configtable[i][1]:
                    if str(msg.payload).split(":")[1][:-1] == domainRemover(configtable[i][2]):
                        time.sleep(delayResponseWithSecond)  # remove when fixed on RP2040ETH side
                        client.publish(configtable[i][1], "PRTCL_READBACK:OK")
                    else:
                        time.sleep(delayResponseWithSecond)  # remove when fixed on RP2040ETH side
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

    if "PRTCL_GIVEINFO_HW:" in str(msg.payload):
        device = ""
        giveninfo = str(msg.payload).split(":", 1)[1][:-1]
        for entry in configtable:
            if str(msg.topic) == entry[1]:
                device = entry[0]
        if device != "":
            ha.updateData(device, giveninfo)

    if "PRTCL_GIVEINFO_RT:" in str(msg.payload):
        device = ""
        giveninfo = str(msg.payload).split(":", 1)[1][:-1]
        for entry in configtable:
            if str(msg.topic) == entry[1]:
                device = entry[0]
        for entry in deviceData:
            if entry[0] == device:
                for data in giveninfo.split(","):# mac, device_model, gateway, ip_addr, mask, last_avg_ping_time
                    if "MODEL" in data:
                        entry[1] = data.split("=")[1]
                    elif "IP" in data:
                        entry[3] = data.split("=")[1]
                    elif "GATEWAY" in data:
                        entry[2] = data.split("=")[1]
                    elif "MASK" in data:
                        entry[4] = data.split("=")[1]
                    else:
                        log.error(f"Unkown data provided via protocol PRTCL_GIVEINFO_RT by device with mac address {device}, given info was {giveninfo}")

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
                            if "(" in entry:
                                compname = entry.split("@")[1].split("(")[0]
                            else:
                                compname = entry.split("@")[1]
                            if "_" in name:
                                name = name.split("_")[0]
                            if name in compname:
                                if len(entry.split("(")) == 2:  # ha tud (-ra splitelni akkor van domain definialva
                                    Domain = entry.split("@")[1].split("(")[1].split(")")[0]
                                else:
                                    continue

                ### check in logs if data was ever received from sensor (fix issue where if entity was put into offline in hass in a different session it was not brought back automatically, only after device went offline and came back)
                sendOnlineAvail = False
                result = log.inLastXConsole(10, f'PRTCL_VAL:{str(msg.payload).split(":")[1].split("@")[0]}', maxOccurance=2)  # azet 2 a maxOccurance mert amikor megjon az uzenet es azt triggereli, akk hozza is adodik a loghoz, szoval mar lesz benne 1
                if result is False:
                    result = log.inLastXConsole(150, f'PRTCL_VAL:{str(msg.payload).split(":")[1].split("@")[0]}', maxOccurance=2) # changed to 150 due to frequent not found messages
                if result is False:
                    log.info(f'No activity found from sensor {SensorName} in the previous 150 messages, setting it to availablity status "online"') # changed to 150
                    sendOnlineAvail = True
                # also maybe check if a set to unavailable happeneded beofre this és akkor is megcsinal ill forcevalue???

                ### end of extra part

                topic = ha.getStatusTopic(SensorName, Device, Domain)  # get status topic
                availtopic = ha.getAvailabilityTopic(SensorName, Device, Domain)
                if sendOnlineAvail and availtopic is not None:
                    client.publish(availtopic, "online")
                if topic is not None:
                    inlastAmm = 10  # might have to set higher if using multiple devices
                    client.publish(topic, value)
                    client.publish(availtopic, "online")
                    #if log.inLastX(inlastAmm, f"Availability check failed for device mcass{Device.lower()}") is True: #EZT KIVETTEM INNEN MERT VAN HOGY NEM REAGÁL AZ ELSŐRE: and log.inLastX(2, f": Ping failed for device {Device} previously, sending force values command") is False:
                    if log.inLastX(inlastAmm, f"Availability check succeeded for device {Device.lower()} that was previously unavailable") is True: #testelés után törölhető
                        log.info(f"Ping failed for device {Device} previously, sending force values command\n (sent from extra)")
                        client.publish(str(msg.topic), "PRTCL_FORCEVALUES")
                else:
                    log.error(f'Failed to find status topic for sensor with name "{SensorName}" under device "{Device}" (Domain:"{Domain}")')
            else:
                log.error("Báttya itt valami nem jó mert csak 1et kéne hogy kapjak egyszerre")

    if "PRTCL_AVAILABILITY_OFF:" in str(msg.payload):
        if HaState == "ON":
            ent_name = str(msg.payload).split(",")[0].split(":")[1]
            ent_type = str(msg.payload).split(",")[1]
            SensorName = ent_name
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

    if "b'PRTCL_DVC_OK'" == str(msg.payload):
        device = ""
        for entry in configtable:
            if entry[1] == msg.topic:
                device = entry[0]
        log.info(f"Data validity check for device with MAC address {device} succeeded")

    if "b'PRTCL_DVC_FAIL'" == str(msg.payload):
        device = ""
        for entry in configtable:
            if entry[1] == msg.topic:
                device = entry[0]
        log.warning(f"Data validity check for device with MAC address {device} failed, asking for device info")
        for entry in configtable:
            if entry[0] == device:
                client.publish(entry[1], "PRTCL_GETINFO:SELF")  # get the data of the device itself

    if "PRTCL_VALIDATE:" in str(msg.payload) and str(msg.payload) != "b'PRTCL_VALIDATE:RESPONSE_FAIL'" and str(msg.payload) != "b'PRTCL_VALIDATE:RESPONSE_OK'":
        help = str(msg.payload).split(":")[1][:-1]
        for entry in configtable:
            if msg.topic == entry[1]:
                if entry[0] != help.split(",")[0]:
                    time.sleep(delayResponseWithSecond)  # remove when fixed on RP2040ETH side
                    client.publish(msg.topic, "PRTCL_VALIDATE:RESPONSE_FAIL")
                else:
                    if domainRemover(entry[2]) != help.split(",")[1]:
                        time.sleep(delayResponseWithSecond)  # remove when fixed on RP2040ETH side
                        client.publish(entry[1], "PRTCL_VALIDATE:RESPONSE_FAIL")
                    else:
                        time.sleep(delayResponseWithSecond)  # remove when fixed on RP2040ETH side
                        client.publish(entry[1], "PRTCL_VALIDATE:RESPONSE_OK")

    if "PRTCL_GETCONTROLTOPIC" in str(msg.payload):
        for entities in ha.entities:
            if str(msg.payload).split(":")[1][:-1] == entities[1]:
                client.publish(msg.topic, f"PRTCL_GIVECONTROLTOPIC:{entities[1]}@{entities[3]}")


def subscribe():
    client.subscribe(configreqtopic)
    client.subscribe(devicetopic)
    client.subscribe(negotopic)
    client.subscribe(selftesttopic)

client.on_message = on_message
client.loop_start()

dailyRunAlready = False
isFinished = False


def runTimeLoop():
    log.info("Started runtime loop")
    global isFinished
    global dailyRunAlready
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
        if datetime.datetime.now().hour == 5 and datetime.datetime.now().minute == 30:
            dailyRunAlready = False
        if (datetime.datetime.now().hour >= 23 or datetime.datetime.now().hour <= 1) and dailyRunAlready is False:
            dailyRunAlready = True
            daily = threading.Thread(target=prot.dailyCheck)
            daily.start()
        if isFinished and dailyRunAlready:
            daily.join()
            isFinished = False
    # *****************************************************************************************************************************************************************************************************************

        if True:  # new ping
            p.ping_runtime()
            # nem mennek a protocollok amig ping van mert a ping runtime egybe van a protocolhivasokkal
            # ami igy gatya mert a protocllok time alapuak
            # start thread for it then join it back once finished
            #kell egy valtozo h is ping thread started, mert ha igen ne csinaljon uj threadet amig megy az elozo
            #ill a ping is gatyasodik hogyha sokaig tart egy protocol (volt pl egy valid 11 seces pingtime a 2.5ös timeout mellett)



loop = threading.Thread(target=runTimeLoop)
loop.start()
# *****************************************************************************************************************************************************************************************************************
# client.loop_stop()


# WEBPAGE PART ------------------------------
import json
from http.server import SimpleHTTPRequestHandler, HTTPServer

LOG_HISTORY = []


def add_log(message, tag):
    LOG_HISTORY.append(f'[{tag.upper()}] [{time.strftime("%H:%M:%S")}]: {message}')


CONFIG_FILES = {
    "configtable": "configtable.txt",
    "config": "CONFIGURATION.txt"
}


class MyHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        """Handles POST commands coming from the webpage"""
        if self.path == "/command":
            length = int(self.headers.get("Content-Length"))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))
            cmd = data.get("cmd", "")

            # --- COMMAND HANDLING HERE ---
            try:
                add_log(f"Received command: {cmd}", "info")
                log.info(f"Received command from web control: {cmd}")

                '''if cmd == "start":
                    add_log("System started!", "info")
                    response = {"status": "success", "detail": "System started"}

                elif cmd == "stop":
                    add_log("System stopped.", "info")
                    response = {"status": "success", "detail": "System stopped"}

                elif cmd == "reset":
                    add_log("System reset.", "info")
                    response = {"status": "success", "detail": "System reset"}

                elif cmd == "status":
                    add_log("Status checked.", "info")
                    response = {"status": "success", "detail": "System OK"}'''

                if cmd == "reloadconfigtable":
                    add_log("Reloading configtable data", "info")
                    result = reloadConfigTable()
                    if result == "OK":
                        response = {"status": "success", "detail": "Reloaded successfully"}
                    if result == "ERROR":
                        response = {"status": "error", "detail": "Error while reading configtable"}

                elif cmd == "reloadServerConfig":
                    add_log("Reloading Server Config data", "info")
                    loadConfig()
                    response = {"status": "success", "detail": "Reloaded successfully"} #no determination if reload was successful or not

                elif cmd == "restart_server":
                    log.error("IMPLEMENT SERVER RESTART COMMAND")
                    response = {"status": "error", "detail": "IMPLEMENT"}  # change to succesful when implemented

                elif cmd == "reloadHASS":
                    if HaState == "OFF":
                        log.info("Skipping Hass reload, Hass is currently turned off")
                        response = {"status": "error", "detail": "HASS is turned off"}
                    else:
                        # log.error("IMPLEMENT HASS CLASS RELOAD COMMAND")
                        global ha
                        del ha
                        ha = HASS()
                        log.info("Reloaded HASS class")
                        response = {"status": "success", "detail": "Reloaded successfully"}

                else:
                    # add_log("Unknown command.", "error")
                    log.error("Unknown command provided from web interface")
                    response = {"status": "error", "detail": "Unknown command"}

            except Exception as e:
                add_log(f"Error: {str(e)}", "error")
                response = {"status": "error", "detail": str(e)}

            # Send JSON back
            encoded = json.dumps(response).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        elif self.path == "/save_config":
            length = int(self.headers.get("Content-Length"))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))

            config_name = data.get("name")
            content = data.get("content")

            try:
                self.write_config(config_name, content)
                add_log(f"{config_name} saved successfully", "info")
                response = {"status": "success"}

            except Exception as e:
                add_log(str(e), "error")
                response = {"status": "error", "detail": str(e)}

            encoded = json.dumps(response).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        elif self.path == "/api/device_command":
            length = int(self.headers.get("Content-Length"))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))

            mac = data.get("mac")
            cmd = data.get("command")

            add_log(f"Device command '{cmd}' for {mac}", "info")

            result = self.handle_device_command(mac, cmd)

            if result == "OK":
                response = {"status": "success"}
            else:
                response = {"status": "error", "detail": result}

            encoded = json.dumps(response).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        elif self.path == "/api/save_protocols":
            length = int(self.headers.get("Content-Length"))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))
            try:
                for protocol in data:

                    name = protocol["name"]
                    frequency = protocol["frequency"]
                    override = protocol["override"]

                    if override:
                        # Override ON (including frequency changes while overridden)
                        success = prot.setOverRide(name, f"{frequency}_OR")

                    else:
                        # We need to know if this protocol was previously overridden
                        current_protocol = next(
                            p for p in prot.protocollist if p[1] == name
                        )

                        was_override = current_protocol[2].endswith("_OR")

                        if was_override:
                            # Turning override OFF
                            success = prot.setOverRide(name, frequency)
                        else:
                            # Normal frequency change
                            success = prot.changeFreq(name, frequency)

                    if not success:
                        response = {
                            "status": "error",
                            "detail": f"Failed to update protocol '{name}'."
                        }
                        break

                else:
                    response = {
                        "status": "success",
                        "detail": "Protocols updated successfully."
                    }


            except Exception as e:
                response = {
                    "status": "error",
                    "detail": str(e)
                }

            encoded = json.dumps(response).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)


        else:
            self.send_error(404)

    def do_GET(self):
        """Serve HTML/JS files AND the log polling endpoint"""
        if self.path == "/logs":
            # Return the last 50 log entries
            log_data = {"logs": LOG_HISTORY[-50:]}

            encoded = json.dumps(log_data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        elif self.path.startswith("/edit/"):
            config_name = self.path.split("/")[-1]

            try:
                content = self.read_config(config_name)
            except Exception as e:
                self.send_error(404, str(e))
                return

            html = f"""
            <html>
            <head>
                <title>Edit {config_name}</title>
                <style>
                    textarea {{ width: 100%; height: 80vh; }}
                    button {{ margin-right: 10px; }}
                </style>
            </head>
            <body>
                <h2>Editing {config_name}</h2>
    
                <textarea id="editor">{content}</textarea><br><br>
    
                <button onclick="save()">Save</button>
                <button onclick="discard()">Discard</button>
                <button onclick="window.location.href='/'">Back</button>
    
                <script>
                    const original = `{content}`;
    
                    function save() {{
                        fetch("/save_config", {{
                            method: "POST",
                            headers: {{ "Content-Type": "application/json" }},
                            body: JSON.stringify({{
                                name: "{config_name}",
                                content: document.getElementById("editor").value
                            }})
                        }})
                        .then(r => r.json())
                        .then(d => alert(d.status));
                    }}
    
                    function discard() {{
                        document.getElementById("editor").value = original;
                    }}
                </script>
            </body>
            </html>
            """

            encoded = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        elif self.path == "/devices":
            self.serve_devices_page()

        elif self.path.startswith("/device/"):
            mac = self.path.split("/device/")[1]
            self.serve_device_page(mac)

        elif self.path == "/api/devices":
            self.serve_devices_api()

        elif self.path.startswith("/api/device/"):
            mac = self.path.split("/api/device/")[1]

            cfg = self.find_device_in_config(mac)
            runtime = self.find_device_in_runtime(mac)
            hwsw = self.find_device_hwsw(mac)

            if not cfg:
                self.send_error(404, "Device not found")
                return

            data = {
                "mac": cfg[0],
                "topic": cfg[1],
                "pinconfig": cfg[2],
                "_":"",
                # runtime data (may be missing)  # mac, device_model, gateway, ip_addr, mask, last_avg_ping_time
                "device_model": runtime[1] if runtime else "unknown",
                "ip_addr": runtime[3] if runtime else None,
                "gateway": runtime[2] if runtime else None,
                "mask": runtime[4] if runtime else None,
                "last_avg_ping_time": runtime[5] if runtime else None,
                "-":"",
                #hardware, software info
                "Manufacturer": hwsw[3],
                "Model": hwsw[4],
                "Hardware version": hwsw[5],
                "Software version": hwsw[6],
            }

            encoded = json.dumps(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        elif self.path == "/api/errors":
            self.serve_errors_api()


        elif self.path == "/protocols":
            self.serve_protocol_page()

        elif self.path == "/api/protocols":
            self.serve_protocol_api()


        else:
            return super().do_GET()

    def log_message(self, format, *args):  # this is only here to disable the constant http request prints to console
        pass

    def read_config(self, name):
        path = CONFIG_FILES.get(name)
        if not path:
            raise ValueError("Unknown config")

        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def write_config(self, name, content):
        path = CONFIG_FILES.get(name)
        if not path:
            raise ValueError("Unknown config")

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def serve_devices_api(self):
        devices = [{"mac": e[0]} for e in configtable]

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(devices).encode())

    def serve_devices_page(self):
        html = """
        <html>
        <head>
            <title>Devices</title>
            <style>
                input { width: 100%; padding: 8px; margin-bottom: 10px; }
                button { width: 100%; padding: 10px; margin: 3px 0; }
            </style>
        </head>
        <body>
            <h2>Device List</h2>
    
            <input id="search" placeholder="Search MAC..." oninput="filter()">
    
            <div id="list"></div>
    
            <button onclick="location.href='/'">Back</button>
    
            <script>
                let devices = [];
    
                fetch("/api/devices")
                    .then(r => r.json())
                    .then(d => {
                        devices = d;
                        render(d);
                    });
    
                function render(list) {
                    const div = document.getElementById("list");
                    div.innerHTML = "";
                    list.forEach(dev => {
                        const b = document.createElement("button");
                        b.textContent = dev.mac;
                        b.onclick = () => location.href = "/device/" + dev.mac;
                        div.appendChild(b);
                    });
                }
    
                function filter() {
                    const q = document.getElementById("search").value.toLowerCase();
                    render(devices.filter(d => d.mac.toLowerCase().includes(q)));
                }
            </script>
        </body>
        </html>
        """

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def serve_device_page(self, mac):
        html = f"""
        <html>
        <head>
            <title>Device {mac}</title>
        </head>
        <body>
            <h2>Device: {mac}</h2>
    
            <pre id="info">Loading...</pre>
    
            <h3>Commands</h3>
            <button onclick="sendCommand('ping')">Ping</button>
            <button onclick="sendCommand('force_values')">Force Values</button>
            <button onclick="sendCommand('reload_pinconfig')">Reload pinconfig</button>
            <button onclick="sendCommand('restart')">Restart</button>

    
            <br><br>
            <button onclick="location.href='/devices'">Back</button>
    
        <script>
        fetch("/api/device/{mac}")
            .then(r => r.json())
            .then(d => {{
                document.getElementById("info").textContent =
                    JSON.stringify(d, null, 2);
            }})
            .catch(e => {{
                document.getElementById("info").textContent =
                    "Failed to load device data";
            }});
        
        function sendCommand(cmd) {{
            fetch("/api/device_command", {{
                method: "POST",
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify({{
                    command: cmd,
                    mac: "{mac}"
                }})
            }})
            .then(r => r.json())
            .then(d => {{
                if (d.status === "success")
                    alert("Command sent successfully");
                else
                    alert(d.detail);
            }});
        }}
        </script>

        </body>
        </html>
        """

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def serve_errors_api(self):
        global activeErrors
        errors = []

        for error in activeErrors:
            errors.append({
                "error": error[0],
                "reason": error[1]
            })

        encoded = json.dumps(errors).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def handle_device_command(self, mac, cmd):
        device_cfg = self.find_device_in_config(mac)
        device_runtime = self.find_device_in_runtime(mac)

        if not device_cfg:
            return "Device not found in configtable"

        if cmd == "ping":
            p.pingstart(mac.upper(), 4)
            return "OK"

        elif cmd == "restart":
            device_config = get_device_config(mac)
            client.publish(device_config[1], "PRTCL_REMOTE:restart")
            return "OK"

        elif cmd == "force_values":
            device_config = get_device_config(mac)
            client.publish(device_config[1], "PRTCL_FORCEVALUES") # a régi tartotta a prtcl_remote schemat, cserelve a szimpla prtcl_forcevaleuesra hogy ne kelljen a végeszköz configon modositani
            return "OK"

        elif cmd == "reload_pinconfig":
            device_config = get_device_config(mac)
            client.publish(device_config[1], "PRTCL_REMOTE:reload_pinconfig")
            return "OK"

        else:
            return "Unknown device command"

    def find_device_in_config(self, mac):
        return next((d for d in configtable if d[0] == mac), None)

    def find_device_in_runtime(self, mac):
        return next((d for d in deviceData if d[0] == mac), None)

    def find_device_hwsw(self, mac):
        return next((d for d in ha.devices if d[1].split("_")[1] == mac.upper()), None)
    def serve_protocol_api(self):

        protocols = []

        for protocol in prot.protocollist:

            freq = protocol[2]

            protocols.append({
                "name": protocol[1],
                "id": prot.getID(protocol[1]),
                "description": prot.getDescription(protocol[1]),
                "frequency": freq.replace("_OR", ""),
                "override": freq.endswith("_OR")
            })

        encoded = json.dumps(protocols).encode()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()

        self.wfile.write(encoded)

    def serve_protocol_page(self):
        html = """
    <!DOCTYPE html>
    <html>
    
    <head>
    
        <title>Protocol Handler</title>
    
        <style>
    
            body{
                font-family:Arial;
                margin:40px;
            }
    
            h2{
                margin-bottom:20px;
            }
    
            table{
                width:100%;
                border-collapse:collapse;
            }
    
            th, td{
                border:1px solid #aaa;
                padding:8px;
                text-align:left;
            }
    
            th{
                background:#ddd;
            }
    
            tr:nth-child(even){
                background:#f5f5f5;
            }
    
            select{
                width:120px;
            }
    
            .bottomBar{
                position:fixed;
                bottom:0;
                left:0;
                width:100%;
                background:white;
                border-top:1px solid #aaa;
            
                display:flex;
                justify-content:space-between;
            
                padding:10px 20px;
                box-sizing:border-box;
            }
            
            .bottomBar button{
                padding:10px 20px;
            }
    
        </style>
    
    </head>
    
    <body>
    
    <h2>Protocol Handler</h2>
    
    <table id="protocolTable">
    
    <colgroup>
        <col style="width:20%">
        <col style="width:8%">
        <col style="width:32%">
        <col style="width:15%">
        <col style="width:10%">
        <col style="width:15%">
    </colgroup>
    
    <thead>
    
    <tr>
    
    <th>Name</th>
    <th>ID</th>
    <th>Description</th>
    <th>Current Frequency</th>
    <th>Override</th>
    <th>New Frequency</th>
    
    </tr>
    
    </thead>
    
    <tbody>
    
    </tbody>
    
    </table>
    
    <br><br><br><br>
    
    <div class="bottomBar">
    <button onclick="location.href='/'">
        Back
    </button>
    <button onclick="saveProtocols()">
        Save Changes
    </button>
    
    </div>
    
    <script>

    
    let protocols=[];
    let originalProtocols = {};
    
    fetch("/api/protocols")
    .then(r=>r.json())
    .then(data=>{
    
        protocols = data;

        // Save the original state of every protocol
        originalProtocols = {};
        
        protocols.forEach(p => {
        
            originalProtocols[p.name] = {
        
                frequency: p.frequency,
        
                override: p.override
        
            };
        
        });
        
        renderProtocols();
    
    });
    
    function renderProtocols(){
    
        const tbody=document.querySelector("#protocolTable tbody");
    
        tbody.innerHTML="";
    
        protocols.forEach(protocol=>{
    
            const row=document.createElement("tr");
    
            row.innerHTML=`
    
            <td>${protocol.name}</td>
    
            <td>${protocol.id}</td>
    
            <td>${protocol.description}</td>
    
            <td>${protocol.frequency}</td>
    
            <td style="text-align:center;">
    
                <input
                    type="checkbox"
                    id="override_${protocol.name}"
                    ${protocol.override ? "checked" : ""}
                >
    
            </td>
    
            <td>
    
                <select id="freq_${protocol.name}">
    
                    <option value="off" ${protocol.frequency=="off"?"selected":""}>Off</option>
    
                    <option value="short" ${protocol.frequency=="short"?"selected":""}>Short</option>
    
                    <option value="normal" ${protocol.frequency=="normal"?"selected":""}>Normal</option>
    
                    <option value="long" ${protocol.frequency=="long"?"selected":""}>Long</option>
    
                    <option value="daily" ${protocol.frequency=="daily"?"selected":""}>Daily</option>
    
                </select>
    
            </td>
    
            `;
    
            tbody.appendChild(row);
    
        });
    
    }
    
    function saveProtocols(){

        let result = [];
    
        protocols.forEach(protocol => {
    
            const newFrequency =
                document.getElementById("freq_" + protocol.name).value;
    
            const newOverride =
                document.getElementById("override_" + protocol.name).checked;
    
            const original =
                originalProtocols[protocol.name];
    
            // Skip protocols that haven't changed
            if (
                newFrequency === original.frequency &&
                newOverride === original.override
            ){
                return;
            }
    
            result.push({
    
                name: protocol.name,
    
                frequency: newFrequency,
    
                override: newOverride
    
            });
    
        });
    
        if(result.length === 0){
    
            alert("No changes to save.");
    
            return;
    
        }
    
        fetch("/api/save_protocols",{
    
            method:"POST",
    
            headers:{
                "Content-Type":"application/json"
            },
    
            body:JSON.stringify(result)
    
        })
        .then(r=>r.json())
        .then(data=>{
    
            alert(data.detail);
    
            return fetch("/api/protocols");
    
        })
        .then(r=>r.json())
        .then(data=>{
    
            protocols = data;
    
            // Update the stored originals
            originalProtocols = {};
    
            protocols.forEach(p => {
    
                originalProtocols[p.name] = {
    
                    frequency: p.frequency,
    
                    override: p.override
    
                };
    
            });
    
            renderProtocols();
    
        });
    
    }
    
    </script>
    
    </body>
    
    </html>
    """

        encoded = html.encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()

        self.wfile.write(encoded)


def run_server():
    log.info("Starting webserver")
    port = 8000
    print(f"Serving at http://localhost:{port}")
    httpd = HTTPServer(("0.0.0.0", port), MyHandler)
    httpd.serve_forever()


if webcontrol:
    webserver = threading.Thread(target=run_server)
    webserver.start()
else:
    log.info("Web control disabled, skipping web start")

finishedStartup = True
log.info("Finished startup")


#hass integracio diagnostica subcategoryba (hasson belul diagnostic csoport) mehet ping meg stb (sw hw version, hardware leiras (marka tipus))
#---ONLY PING DONE----

#server sajat entity hassban????

'''
kulon topic for self check and interserver comm
MCASS/server/self   ---   ide mehetnek a self test uzenetek
MCASS/server/control   ---    ide mehetnek a takeover uzenetek, (amig backup server vagy addig passzivban maradsz, nem küldesz self check uzenetet mert a main server ugyis kuld te meg csak fogadod, és ha te lennel a main server akkor kezdesz kuldeni ilyeneket (protokol kapcsoloval megoldhato mint a hass enabled/disabled eseteben)
az ide erkezett uezenetek lehetnenenk q2-esek (amelyik megmarad a brokeren, és csatlakozaskor kiküldi a csatlakozott clientnek), hogy ha a masodlagos atveszi az iranyitast, es az elso ujraindulna, felcsatlakozas soran megkapja az uzenetet hogy atvettek az irnayitast
'''

# weblapra hass verzérlőgombok
#remove from hass (on entity level), re-add to hass, stb....

#ellenorzest adni neki h minden parameter megvan e az adressable rgb ledeknek
#ha kezdo ledszam nincs megadva csak egy szám a végé (ketto helyett), akkor 0tol indul es megadott szam a hossz


            # nem mennek a protocollok amig ping van mert a ping runtime egybe van a protocolhivasokkal
            # ami igy gatya mert a protocllok time alapuak
            # start thread for it then join it back once finished
            #kell egy valtozo h is ping thread started, mert ha igen ne csinaljon uj threadet amig megy az elozo
            # 1820-as sor kornykee

#még meg kell csinálni a synctohasst rendesen hogy az updatelt datat frissitse hassba is be
#---Azt ugy kene lehet megcsinálni hogy törli egyik saját diagnostikai entityjet (ami még nem létezik), a snyctohass protocol meg bekuldi ujra, (lehet esetleg direktbe hivni egy dataupdate utan), és felülirj a magavla vitt device dataval

#ill azt is meg kene csinalni h hogy ha egy entityt kiveszunk hardwerbol akkor az hassbol is jojjon ki jelenleg ez sincs megcsinalva
#!!!!! a pinget ugy kene kotni hozza h a dataline.ssplit(",")[2] szal a unique id eleje ("_Ping") nelkuli resz ha benne van (es csak az semmi mas egyeb kiegeszites utana(_Lamp pl) akk hagyja bent, de ha nincs vegye ki
#ugyanigy kene lehet megcsinalni a tobbi entity kivetelet is
#---ELV DONE ELL-----

#logs in the web on device basis, where the logs from the given devices are visible (switching a protocol to off/short stb)
# Individual protocol control like for server but n device basis????

#configtable es config fileokra lehetne szűrést csinálni tiltott karakterekre amik benne vannak a programba @, &, * ilyenek
#---ELVETVE---#

# ---- ---- ill lehet log3ba mehetne egy olyan update h az utolso 50 logot bent tartja memoriaban (50 az nem sok nem is kevés) és akkor nem a hattertarat kene gyepalni a folyamatos olvasasokkal (maybe 150 mert az ize i s150-el megy mostmar???)

#maybe add a "last run" time data point for the protocol page on the web interface
