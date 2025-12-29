from machine import UART, Pin
from machine import I2C
import machine
import time
import ubinascii

import dht
import bmp085
import bh1750
#import rotary #not used, creating my own implement


MANUFACTURER = "Waveshare"
MODEL = "RP2040ETH"
HW_VERSION = "n/a"
SW_VERSION = "0.3"
CONFIGURL = "https://github.com/G1b0r/MCASS"


i2c = ""
i2c = I2C(id=0, scl=1, sda=0, freq=400000)

#add long protocol for it to check i2c devices, mert ha indukalkor nem ment akkor kiveszi configbol, errol is kene feedback serverbe, de azert kell a protocol hogy ha menet kozben feleled vagy ki lesz cserelve egy mukodore akkor ujrakerje a pinconfigot es a kulonbsegeket ujracsinalja
#igy futas kozben ha kicserelunk egy alkatreszt akkor nem kell ujrainditani es megjavul "magatol"

#illetve azt is meg kell oldani hogyha boototolaskor nincs net akkor kesobb is tudjon csatlakozni
#most bebootolt allt vagy 5 percet es utana dugtam be netre de nem csatlakozott fel

#pinconfighoz kikötesek
#ha van i2c cim akkor legyen scl sda config is, ha nincs send error vagy valamifele ellenorzes
#hogyha van már valami azon a pinen ne inditsa rá (és az elozot ami mar fogja azt a pint üsse ki mert görcs tudj amelyik van elirva)
################################################################################### protocol stuff
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
################################################################################### protocol stuff
# MQTT
CLIENT_ID = "Waveshare_RP2040_ETH" #optionally write out the new client id to eeprom, and use that from boot, this way no need to force reconnect, after a restart it will use it by default from eeprom
#current solution is to force reconnect which is not solved currently NEED TO DOOOOOOOOO
CONFIG_RPLY_TOPIC = "test/config/reply"
CONFIG_REQ_TOPIC = "test/config/request"
DEVICE_TOPIC = ""
USERNAME = "mqttuser"
PASSWORD = "mqtt"

LASTMESSAGE = time.time_ns()


DEVICE_MAC = ""#"3C-AB-72-96-52-F4"
CONFIG_STATUS = [0, 0, 0, 0] #requested config, got config, sent ok on device topic, got acknoledged
PINCONFIG_STATUS=[0, 0, 0, 0, 0] #requested pinconfig, got config, readback, readback ok received , started pinconfig ez mar az IOArraybol kell jojjon
PINCONFIG = ""
# CH9120
MODE = 1  #0:TCP Server 1:TCP Client 2:UDP Server 3:UDP Client
GATEWAY = (192, 168, 0, 1)     # GATEWAY
TARGET_IP = (192, 168, 0, 150)  # TARGET_IP #106 a normál, #150 a test
LOCAL_IP = (192, 168, 0, 139)  # LOCAL_IP
SUBNET_MASK = (255,255,255,0)  # SUBNET_MASK
LOCAL_PORT1 = 1000             # LOCAL_PORT1
TARGET_PORT = 1883             # TARGET_PORT
BAUD_RATE = 115200             # BAUD_RATE

uart1 = UART(1, baudrate=9600, tx=Pin(20), rx=Pin(21))

DHCP_IP = ""
DHCP_GW = ""
DHCP_MASK = ""

class rotaryEncoder:
    counter = 0
    aState = 0
    aLastState = 0
    pinA = ""
    pinB = ""
    rotation = None

    def __init__(self, pinA, pinB):
        self.pinA = machine.Pin(int(pinA), machine.Pin.IN)
        self.pinB = machine.Pin(int(pinB), machine.Pin.IN)
        self.aLastState = self.pinA.value()

    def read(self):
        self.rotation = None
        self.aState = self.pinA.value()
        if self.aState != self.aLastState:
            if self.pinB.value() != self.aState:
                #print("clockwise")
                self.rotation = "Clockwise"
            else:
                #print("counterclokwise")
                self.rotation = "Counterclockwise"

        self.aLastState = self.aState
        return(self.rotation)


class IOArray:
    #maybe do a check hogy ne akarjak ADC-t egy olyan pinen amin nincs adc

    #update idea, theres options for pullup/pulldown, maybe add the possibility to define pullup/down in config

    #még az i2c nincs meg!!!!!!!

    supportedHardWare = ["DHT11", "DHT22", "BMP180", "BMP085", "BH1750", "Rotary"]

    #write in the multiSensors the correct way to correlate with how the values are stored separated via the "/"
    #so if the value before "/" is a temp here it should be temperature the first one after the type designation
    multiSensors = [["DHT11", "Temperature", "Humidity"],
                    ["DHT22", "Temperature", "Humidity"],
                    ["BMP180", "Temperature", "Pressure"],
                    ["BMP085", "Temperature", "Pressure"]]

    checkEveryCycle = [[], [], [], [], [], []]#ide a nagy listák azon indexe jon amelyiket minden ciklusban akarjuk ellenzorni
    #[EveryanalogInList, EverydigitalInList, EverydigitalOutList, Everyi2cAddressList, EverypwmOutList, EveryspeHardWareList]

    analogInList=[] 	#mindegyiknel
    digitalInList=[]	#elso a név
    digitalOutList=[]	#masodik a pin number
    i2cAddressList=[]	#harmadik a pindefinicio
    pwmOutList=[]		#negyedik a sensor value
    speHardWareList=[]
    SCL=0
    SDA=0
    i2cByteArray = bytearray(8)
    i2cRead = ""

    newValList=[]

    def __init__(self):
        print("IOArray init")
        self.checkEveryCycle = [[], [], [], [], [], []]
        self.analogInList=[]
        self.digitalInList=[]
        self.digitalOutList=[]
        self.i2cAddressList=[]
        self.pwmOutList=[]
        self.speHardWareList=[]
        self.SCL=0
        self.SDA=0
        self.i2cByteArray = bytearray(8)
        self.i2cRead = ""
        self.newValList=[]

    def autoSetup(self, config):
        global PINCONFIG_STATUS
        PINCONFIG_STATUS[4] = 1
        if config == "None":
            print("No config applied yet, skipping")
            return
        configList = config.split("/")
        for i in range(0, len(configList)):
            if "AnalogRead" in configList[i]:
                self.addAI(configList[i].split("@")[1], configList[i].split("@")[2])
                if configList[i].split("@")[-1] == "EC":
                    self.checkEveryCycle[0].append(int(len(self.analogInList)-1))
            elif "DigitalRead" in configList[i]:
                self.addDI(configList[i].split("@")[1], configList[i].split("@")[2])
                if configList[i].split("@")[-1] == "EC":
                    self.checkEveryCycle[1].append(int(len(self.digitalInList)-1))
            elif "DigitalOut" in configList[i]:
                self.addDO(configList[i].split("@")[1], configList[i].split("@")[2])
                if configList[i].split("@")[-1] == "EC":
                    mqtt_client.publish(DEVICE_TOPIC, 'PRTCL_LOG_WARNING:No "EC" modifier avaible for Digital Outputs')
            elif "PWMOut" in configList[i]:
                self.addPWMO(configList[i].split("@")[1], configList[i].split("@")[2])
                if configList[i].split("@")[-1] == "EC":
                    mqtt_client.publish(DEVICE_TOPIC, 'PRTCL_LOG_WARNING:No "EC" modifier avaible for PWM Outputs')
            elif "SDA" in configList[i]:
                self.SetSDA(configList[i].split("@")[1])
                if configList[i].split("@")[-1] == "EC":
                    mqtt_client.publish(DEVICE_TOPIC, 'PRTCL_LOG_WARNING:No "EC" modifier avaible for I2C')
            elif "SCL" in configList[i]:
                self.SetSCL(configList[i].split("@")[1])
                if configList[i].split("@")[-1] == "EC":
                    mqtt_client.publish(DEVICE_TOPIC, 'PRTCL_LOG_WARNING:No "EC" modifier avaible for I2C')
            elif "0x" in configList[i]:
                self.addi2cAddress(configList[i].split("@")[0], configList[i].split("@")[1])
            elif configList[i].split("@")[0] in self.supportedHardWare:
                self.addSpecHardware(configList[i].split("@")[1], configList[i].split("@")[0], configList[i].split("@")[2])
                if configList[i].split("@")[-1] == "EC":
                    self.checkEveryCycle[5].append(int(len(self.speHardWareList)-1))
            else:
                mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_LOG_ERROR:The hardware in section {configList[i]} is not yet supported by this board ({MANUFACTURER} {MODEL})")
                #mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_LOG_ERROR:Unkown IO parameter was given in section: {configList[i]}") #old error message
        print(f"\n{self.analogInList}\n{self.digitalInList}\n{self.digitalOutList}\n{self.i2cAddressList}\n{self.pwmOutList}\n{self.speHardWareList}\n")
        self.initAnalogIn()
        self.initDigitalIn()
        self.initDigitalOut()
        self.initPWMOut()
        self.initSpecHardWare()
        '''if not self.i2cAddressList: #ha ures'''
        if self.SCL != self.SDA:
            self.initI2C()
            self.scanI2C()
        else:
            mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_LOG_ERROR: Can't initialize I2C, SCL and SDA are defined on the same pin")
        print(self.checkEveryCycle)


    #add devices to lists------------------------------------------------------------------------
    def addAI(self, name, pin):
        self.analogInList.append(f"{name}@{pin}@pindef@value@lastval".split("@"))
        print(f"Successfully added {name} input on pin {pin} to AnalogIn")
    def addDI(self, name, pin):
        self.digitalInList.append(f"{name}@{pin}@pindef@value@lastval".split("@"))
        print(f"Successfully added {name} input on pin {pin} to DigitalIn")
    def addDO(self, name, pin):
        self.digitalOutList.append(f"{name}@{pin}@pindef@value@lastval".split("@"))
        print(f"Successfully added {name} output on pin {pin} to DigitalOut")
    def addPWMO(self, name, pin):
        self.pwmOutList.append(f"{name}@{pin}@pindef@value".split("@"))
        print(f"Successfully added {name} output on pin {pin} to pwmOut")
    def SetSDA(self, pin):
        self.SDA = pin
        print(f"Successfully set SDA to pin {pin}")
    def SetSCL(self, pin):
        self.SCL = pin
        print(f"Successfully set SCL to pin {pin}")
    def addi2cAddress(self, deviceName, address):
        address = address.split("x")[1]
        self.i2cAddressList.append(f"{deviceName}@{address}@value@lastval".split("@"))
        print(f"Successfully added {deviceName} device with address {address} to i2c address list")
    def addSpecHardware(self, deviceName, deviceType, devicePin):
        if deviceType == "Rotary":
            self.speHardWareList.append(f"{deviceName}@{deviceType}@{devicePin}@pindef@value".split("@"))
            print(f"Successfully added {deviceName} input on pin {devicePin} to SpecHardware")
        else:
            self.speHardWareList.append(f"{deviceName}@{deviceType}@{devicePin}@pindef@value@lastval".split("@"))
            print(f"Successfully added {deviceName} input on pin {devicePin} to SpecHardware")

    #initialize and read/write fucntions---------------------------------------------------------------

    def initAnalogIn(self):
        for i in range(0, len(self.analogInList)):
            self.analogInList[i][2] = machine.ADC(int(self.analogInList[i][1]))

    def readAnalog(self, whichone):
        if whichone == "all":
            for i in range(0, len(self.analogInList)):
                self.analogInList[i][4] = self.analogInList[i][3]
                self.analogInList[i][3] = self.analogInList[i][2].read_u16()
                #print(f"{self.analogInList[i][0]} with value of {self.analogInList[i][3]}")
        else:
            self.analogInList[whichone][4] = self.analogInList[whichone][3]
            self.analogInList[whichone][3] = self.analogInList[whichone][2].read_u16()
            #print(f"{self.analogInList[whichone][0]} with value of {self.analogInList[whichone][3]}")
    #*******************************
    def initDigitalIn(self):
        for i in range(0, len(self.digitalInList)):
            self.digitalInList[i][2] = machine.Pin(int(self.digitalInList[i][1]), machine.Pin.IN)

    def readDigital(self, whichone):
        if whichone == "all":
            for i in range(0, len(self.digitalInList)):
                self.digitalInList[i][4] = self.digitalInList[i][3]
                self.digitalInList[i][3] = self.digitalInList[i][2].value()
                #print(f"{self.digitalInList[i][0]} with value of {self.digitalInList[i][3]}")
        else:
            self.digitalInList[whichone][4] = self.digitalInList[whichone][3]
            self.digitalInList[whichone][3] = self.digitalInList[whichone][2].value()
            #print(f"{self.digitalInList[whichone][0]} with value of {self.digitalInList[whichone][3]}")
    #*******************************
    def initDigitalOut(self):
        for i in range(0, len(self.digitalOutList)):
            self.digitalOutList[i][2] = machine.Pin(int(self.digitalOutList[i][1]), machine.Pin.OUT)

    def setDigitalOut(self, name, state):#name and on/off-1/0
        for i in range(0, len(self.digitalOutList)):
            if name == self.digitalOutList[i][0]:
                if state == "on" or 1:
                    self.digitalOutList[i][2].on()
                    return
                elif state == "off" or 0:
                    self.digitalOutList[i][2].off()
                    return
                else:
                    print(f'Invalid digital pin state of "{state}" was given')
        print(f'Invalid output name of "{name}" was given')
    #********************************
    def initPWMOut(self):
        for i in range(0, len(self.pwmOutList)):
            self.pwmOutList[i][2] = machine.PWM(machine.Pin(int(self.pwmOutList[i][1])))

    def setPWMparams(self, name, frequency, dutyCycle):
        for i in range(0, len(self.pwmOutList)):
            if name == self.pwmOutList[i][0]:
                self.pwmOutList[i][2].freq(frequency)
                self.pwmOutList[i][2].duty(dutyCycle)
    #********************************
    def initI2C(self):
        if self.SCL != self.SDA and self.SCL != 0 and self.SDA != 0:
            #machine.I2C(0, int(self.SCL), int(self.SDA), freq=400000)
            #I2C.init(0, int(self.SCL), int(self.SDA), freq=400000)
            i2c = I2C(id=0, scl=int(self.SCL), sda=int(self.SDA), freq=400000)
        else:
            if self.SCL == 0 and self.SDA == 0:
                mqtt_client.publish(DEVICE_TOPIC, "PRTCL_LOG_WARNING:SCL and SDA was left unconfigured")
            elif self.SCL == 0:
                mqtt_client.publish(DEVICE_TOPIC, "PRTCL_LOG_WARNING:SCL was left unconfigured")
            elif self.SDA == 0:
                mqtt_client.publish(DEVICE_TOPIC, "PRTCL_LOG_WARNING:SDA was left unconfigured")
            elif self.SDA == self.SCL:
                mqtt_client.publish(DEVICE_TOPIC, "PRTCL_LOG_ERROR:invalid I2C config SCL and SDA were provided the same pin")
            else:
                mqtt_client.publish(DEVICE_TOPIC, "PRTCL_LOG_ERROR:Unkown error while setting up I2C")
            del self.i2cAddressList

    def scanI2C(self):
        peripherals = i2c.scan()
        print(peripherals)
        mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_LOG_INFO:The following devices were found on I2C: {peripherals}")
        for element in self.i2cAddressList:
            if element[1] in peripherals:
                mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_LOG_INFO:Device at {element[1]} was found connected, leaving in config")
            else:
                mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_LOG_WARNING:Device with address {element[1]} was not found, removing from config")
                self.i2cAddressList.remove(element)

    def readI2C(self):
        #print("reading i2c")
        for i in range(0, len(self.i2cAddressList)):
            try:
                self.i2cAddressList[i][3] = self.i2cAddressList[i][2]
                #self.i2cByteArray = I2C.readfrom_into(int(self.i2cAddressList[i][1]), self.i2cByteArray, stop=True)
                #i2c.readfrom_into(int(self.i2cAddressList[i][1]), self.i2cByteArray, stop=True)
                self.i2cRead = i2c.readfrom(int(self.i2cAddressList[i][1]), 8)
                self.i2cAddressList[i][2] = self.i2cByteArray
                #print(f"{self.i2cAddressList[i][0]} with value of {self.i2cAddressList[i][2]}")
            except Exception as e:
                print(e)
                if str(e) == "[Errno 5] EIO":
                    mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_LOG_ERROR:Lost communication with device {self.i2cAddressList[i][0]} on address {self.i2cAddressList[i][1]}")
                else:
                    mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_LOG_ERROR:Unkown error occured while reading from I2C: {str(e)}")

    def initSpecHardWare(self): #{deviceName}@{deviceType}@{devicePin}@pindef@value@lastval
        for i in range(0, len(self.speHardWareList)):
            try:
                if self.speHardWareList[i][1] == "DHT11":
                    self.speHardWareList[i][3] = dht.DHT11(machine.Pin(int(self.speHardWareList[i][2])))
                if self.speHardWareList[i][1] == "DHT22":
                    self.speHardWareList[i][3] = dht.DHT22(machine.Pin(int(self.speHardWareList[i][2])))
                if self.speHardWareList[i][1] == "BMP180":
                    self.speHardWareList[i][3] = bmp085.BMP180(i2c)
                if self.speHardWareList[i][1] == "BMP085":
                    self.speHardWareList[i][3] = bmp085.BMP085(i2c)
                if self.speHardWareList[i][1] == "BH1750":
                    self.speHardWareList[i][3] = bh1750.BH1750(0x23, i2c)
                if self.speHardWareList[i][1] == "Rotary":
                    self.speHardWareList[i][3] = rotaryEncoder(self.speHardWareList[i][2].split("&")[0], self.speHardWareList[i][2].split("&")[1])
                    #print(self.speHardWareList[i][3])
            except Exception as e:
                print(e)
                if str(e) == "[Errno 5] EIO":
                    mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_LOG_ERROR:Can not communicate with device {self.i2cAddressList[i][0]} on address {self.i2cAddressList[i][1]}")
                    del (self.speHardWareList[i])
                else:
                    mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_LOG_ERROR:Unkown error occured while reading from I2C: {str(e)}")

    def readSpecHardWare(self, whichone):
        if whichone == "all":
            for i in range(0, len(self.speHardWareList)):
                self.subreadSpecHardWare(i)
        else:
            self.subreadSpecHardWare(whichone)

    def subreadSpecHardWare(self, index):
        if self.speHardWareList[index][1] == "DHT11" or self.speHardWareList[index][1] == "DHT22":
            self.speHardWareList[index][5] = self.speHardWareList[index][4]
            try:
                self.speHardWareList[index][3].measure()
                help1=self.speHardWareList[index][3].temperature()
                help2=self.speHardWareList[index][3].humidity()
                self.speHardWareList[index][4] = f"{help1}/{help2}"
            except Exception as e:
                #print(e)
                if str(e) == "[Errno 110] ETIMEDOUT":
                    mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_LOG_ERROR:Can not communicate with device {self.speHardWareList[index][0]} on pin {self.speHardWareList[index][2]}")
                else:
                    mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_LOG_ERROR:Unkown error occured while reading from device {self.speHardWareList[index][0]} with type {self.speHardWareList[index][1]} : {str(e)}")
                mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_AVAILABILITY_OFF:{self.speHardWareList[index][0]},{self.speHardWareList[index][1]}")

        elif self.speHardWareList[index][1] == "BMP180" or self.speHardWareList[index][1] == "BMP085":
            self.speHardWareList[index][5] = self.speHardWareList[index][4]
            try:
                help1=self.speHardWareList[index][3].temperature
                help2=int(self.speHardWareList[index][3].pressure*100) #*100 to give back pascal not hectopascal (the pressure() fucntion gives back hectopascals), and then convert to int to remove floating point
                self.speHardWareList[index][4] = f"{help1}/{help2}"
            except Exception as e:
                print(e)
                if str(e) == "[Errno 110] ETIMEDOUT": #ide nem ilyen error for jonni
                    mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_LOG_ERROR:Can not communicate with device {self.speHardWareList[index][0]} on pin {self.speHardWareList[index][2]}")
                else:
                    mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_LOG_ERROR:Unkown error occured while reading from device {self.speHardWareList[index][0]} with type {self.speHardWareList[index][1]} : {str(e)}")
                mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_AVAILABILITY_OFF:{self.speHardWareList[index][0]},{self.speHardWareList[index][1]}")

        elif self.speHardWareList[index][1] == "BH1750":
            self.speHardWareList[index][5] = self.speHardWareList[index][4]
            try:
                self.speHardWareList[index][4] = self.speHardWareList[index][3].measurement
            except Exception as e:
                #print(e)
                if str(e) == "[Errno 5] EIO":
                    mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_LOG_ERROR:Lost communication with device {self.speHardWareList[index][0]} on address 0x23")
                else:
                    mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_LOG_ERROR:Unkown error occured while reading from device {self.speHardWareList[index][0]} with type {self.speHardWareList[index][1]} : {str(e)}")
                mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_AVAILABILITY_OFF:{self.speHardWareList[index][0]},{self.speHardWareList[index][1]}")
        elif self.speHardWareList[index][1] == "Rotary":
            self.speHardWareList[index][4] = None
            self.speHardWareList[index][4] = self.speHardWareList[index][3].read()

    #********************************
    def getVals(self):
        self.readAnalog("all")
        self.readDigital("all")
        self.readI2C()
        #read I2C
        self.readSpecHardWare("all")
        self.checkForNewData()

    def seperateValuesToSend(self, dName, dType, value):  # used to separate 2 or more values stored together so the server doesnt have to, reduceing load on
        sensors = []
        values = value.split("/")
        for entry in self.multiSensors:
            if entry[0] == dType:
                for i in range(1, len(entry)):
                    sensors.append(entry[i])

        tbr = f"{dName}_{sensors[0]}@{values[0]}"
        for i in range(1, len(sensors)):
            tbr = tbr + f"*{dName}_{sensors[i]}@{values[i]}"
        return(tbr)

    def checkForNewData(self):
        for i in range(0, len(self.analogInList)):
            if self.analogInList[i][3] != self.analogInList[i][4]:
                self.newValList.append(f"{self.analogInList[i][0]}@{self.analogInList[i][3]}")
            else:
                #print(f"No new value for {self.analogInList[i][0]}, skipping send data")
                continue
            self.analogInList[i][4] = self.analogInList[i][3] #ez azert kell mert ha nem mér nem upadteolja a prev erteket igy tobbszor elkuldi
        for i in range(0, len(self.digitalInList)):
            if self.digitalInList[i][3] != self.digitalInList[i][4]:
                self.newValList.append(f"{self.digitalInList[i][0]}@{self.digitalInList[i][3]}")
            else:
                #print(f"No new value for {self.digitalInList[i][0]}, skipping send data")
                continue
            self.digitalInList[i][4] = self.digitalInList[i][3] #ez azert kell mert ha nem mér nem upadteolja a prev erteket igy tobbszor elkuldi
        #send data
        for i in range(0, len(self.i2cAddressList)):
            if self.i2cAddressList[i][2] != self.i2cAddressList[i][3]:
                self.newValList.append(f"{self.i2cAddressList[i][0]}@{self.i2cAddressList[i][2]}")
            else:
                #print(f"No new value for {self.i2cAddressList[i][0]}, skipping send data")
                continue
        for i in range(0, len(self.speHardWareList)):
            if self.speHardWareList[i][1] != "Rotary":
                if self.speHardWareList[i][4] != self.speHardWareList[i][5]:
                    #self.newValList.append(f"{self.speHardWareList[i][0]}@{self.speHardWareList[i][4]}")
                    sep = self.seperateValuesToSend(self.speHardWareList[i][0], self.speHardWareList[i][1], self.speHardWareList[i][4])
                    for entry in sep.split("*"): #this way it is handling multiple sensors not just 2, eg: 3 in the form of an accelerometer
                        self.newValList.append(entry)
                else:
                    #print(f"No new value for {self.speHardWareList[i][0]}, skipping send data")
                    continue
                self.speHardWareList[i][5] = self.speHardWareList[i][4] #ez azert kell mert ha nem mér nem upadteolja a prev erteket igy tobbszor elkuldi
            else:
                if self.speHardWareList[i][4] != None:
                    self.newValList.append(f"{self.speHardWareList[i][0]}@{self.speHardWareList[i][4]}")
                else:
                    continue

        for i in range(0, len(self.newValList)):
            mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_VAL:{self.newValList[i]}")
            time.sleep(0.001)
        self.newValList.clear()

    def readEveryCycle(self):
        for i in range(0, len(self.checkEveryCycle)):
            for j in range(0, len(self.checkEveryCycle[i])):
                if i == 0:
                    self.readAnalog(self.checkEveryCycle[i][j])
                elif i == 1:
                    self.readDigital(self.checkEveryCycle[i][j])
                elif i == 5:
                    self.readSpecHardWare(self.checkEveryCycle[i][j])
        self.checkForNewData()

    def forceValues(self):
        self.readAnalog("all")
        self.readDigital("all")
        self.readI2C()
        #read I2C
        self.readSpecHardWare("all")

        for i in range(0, len(self.analogInList)):
            if self.analogInList[i][4] != "lastval":
                self.newValList.append(f"{self.analogInList[i][0]}@{self.analogInList[i][3]}")
            else:
                #print(f"No new value for {self.analogInList[i][0]}, skipping send data")
                continue
            self.analogInList[i][4] = self.analogInList[i][3] #ez azert kell mert ha nem mér nem upadteolja a prev erteket igy tobbszor elkuldi
        for i in range(0, len(self.digitalInList)):
            if self.digitalInList[i][4] != "lastval":
                self.newValList.append(f"{self.digitalInList[i][0]}@{self.digitalInList[i][3]}")
            else:
                #print(f"No new value for {self.digitalInList[i][0]}, skipping send data")
                continue
            self.digitalInList[i][4] = self.digitalInList[i][3] #ez azert kell mert ha nem mér nem upadteolja a prev erteket igy tobbszor elkuldi
        #send data
        for i in range(0, len(self.speHardWareList)):
            if self.speHardWareList[i][1] != "Rotary":
                continue
            else:
                self.newValList.append(f"{self.speHardWareList[i][0]}@{self.speHardWareList[i][4]}")

        for i in range(0, len(self.newValList)):
            mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_VAL:{self.newValList[i]}")
            time.sleep(0.001)
        self.newValList.clear()


class ProtocolBook:
    protocollist = []  # protocollist=[protpointer, protname, type(short,normal,long)]
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
                    print(f"Unkown protocoltype defined in {protocol}")
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
        #print("test normal")

    def tests(self, command):
        if command == "getID":
            return "T1"
        #print("test short")

    def testl(self, command):
        if command == "getID":
            return "T3"
        #print("test long")

    def teste(self, command):
        if command == "getID":
            return "T0"
        #print("test everyloop")

    def protShort(self):
        for i in range(0, len(self.protocollist)):
            if self.protocollist[i][2] == "short":
                #log.console("Executes short protocols")
                self.protDict[self.protocollist[i][0]](self, "none")

    def protNorm(self):
        for i in range(0, len(self.protocollist)):
            if self.protocollist[i][2] == "normal":
                #log.console("Executes normal protocols")
                self.protDict[self.protocollist[i][0]](self, "none")

    def protLong(self):
        for i in range(0, len(self.protocollist)):
            if self.protocollist[i][2] == "long":
                #log.console("Executes long protocols")
                self.protDict[self.protocollist[i][0]](self, "none")

    def everyLoop(self):
        for i in range(0, len(self.protocollist)):
            if self.protocollist[i][2] == "every":
                #log.console("Executes protocols every loop")
                self.protDict[self.protocollist[i][0]](self, "none")

    def configProtn(self, command):
        if command == "getID":
            return "C0"
        #config protocols
        if CONFIG_STATUS[1] == 0: #no config reply yet
            print("No config reply, asking again")
            mqtt_client.publish(CONFIG_REQ_TOPIC, DEVICE_MAC)
            CONFIG_STATUS[0] = 1 #set config requested to true
        elif CONFIG_STATUS[3] == 0 and CONFIG_STATUS[2] == 1: #no topic change ack yet and sent here message
            print("No topic ack, asking again")
            mqtt_client.publish(DEVICE_TOPIC, "HERE")

        #pinconfig protocols
        elif CONFIG_STATUS[3] == 1:#csak akkor kerje a pinconfigot ha mar teljesult az mqtt config

            if PINCONFIG_STATUS[3] == 1 and PINCONFIG_STATUS[4] == 0:
                print("pinconfig status ok, start pinconfig on hardware")
                print(PINCONFIG)
                IOarray.autoSetup(PINCONFIG)
            elif PINCONFIG_STATUS[2] == 1 and PINCONFIG_STATUS[3] == 0: #no ack of readback yet
                mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_READBACK:{PINCONFIG}")

            elif PINCONFIG_STATUS[1] == 1 and PINCONFIG_STATUS[2] == 0: #got config, no readback
                mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_READBACK:{PINCONFIG}")
                PINCONFIG_STATUS[2] = 1

            elif PINCONFIG_STATUS[0] == 1 and PINCONFIG_STATUS[1] == 0: #requested config yet no reply
                mqtt_client.publish(DEVICE_TOPIC, "PRTCL_PINCONFIG:REQUEST")

            elif PINCONFIG_STATUS[0] == 0: #not yet requested config
                mqtt_client.publish(DEVICE_TOPIC, "PRTCL_PINCONFIG:REQUEST")
                PINCONFIG_STATUS[0] = 1

    def readValuesn(self, command):
        if command == "getID":
            return "RT1"
        if PINCONFIG_STATUS[4] == 1:
            IOarray.getVals()

    def readValuesEveryCycle(self, command):
        if command == "getID":
            return "RT0"
        if PINCONFIG_STATUS[4] == 1:
            IOarray.readEveryCycle()


class ASCII:
    HexCharList = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f"]

    AsciiHexTable = [["21", "!"],["22", '"'],["23", "#"],["24", "$"],
                     ["25", "%"],["26", "&"],["27", "'"],["28", "("],
                     ["29", ")"],["2A", "*"],["2B", "+"],["2C", ","],
                     ["2D", "-"],["2E", "."],["2F", "/"],["30", "0"],
                     ["31", "1"],["32", '2'],["33", "3"],["34", "4"],
                     ["35", "5"],["36", "6"],["37", "7"],["38", "8"],
                     ["39", "9"],["3A", ":"],["3B", ";"],["3C", "<"],
                     ["3D", "="],["3E", ">"],["3F", "?"],["40", "@"],
                     ["41", "A"],["42", 'B'],["43", "C"],["44", "D"],
                     ["45", "E"],["46", "F"],["47", "G"],["48", "H"],
                     ["49", "I"],["4A", "J"],["4B", "K"],["4C", "L"],
                     ["4D", "M"],["4E", "N"],["4F", "O"],["50", "P"],
                     ["51", "Q"],["52", 'R'],["53", "S"],["54", "T"],
                     ["55", "U"],["56", "V"],["57", "W"],["58", "X"],
                     ["59", "Y"],["5A", "Z"],["5B", "["],["5C", "\\"],
                     ["5D", "]"],["5E", "^"],["5F", "_"],["60", "`"],
                     ["61", "a"],["62", 'b'],["63", "c"],["64", "d"],
                     ["65", "e"],["66", "f"],["67", "g"],["68", "h"],
                     ["69", "i"],["6A", "j"],["6B", "k"],["6C", "l"],
                     ["6D", "m"],["6E", "n"],["6F", "o"],["70", "p"],
                     ["71", "q"],["72", 'r'],["73", "s"],["74", "t"],
                     ["75", "u"],["76", "v"],["77", "w"],["78", "x"],
                     ["79", "y"],["7A", "z"],["7B", "{"],["7C", "|"],
                     ["7D", "}"],["7E", "~"]]
    def __init__(self):
        print("ASCII init")

    def convert(self, message):
        #print("In ASCII Convert")
        #print(message)
        message = self.removeExtras(message)
        message = self.AsciiToHex(message)
        return message

    def removeExtras(self, message):
        #print("In ASCII removeExtras")
        #print(message)
        message = str(message)
        message = message.replace("b'", "")
        message = message.replace("'", "")
        message = message.replace("\\x", "")
        return message

    def AsciiToHex(self, message):
        #print("In ASCII AsciiToHex")
        #print(message)
        fixedmessage = ""
        #find non-hex characters and convert them to hex
        for i in range(0, len(message)):
            if f"{message[i]}" in self.HexCharList:
                fixedmessage = fixedmessage + f"{message[i]}"
            else:
                for j in range(0, len(self.AsciiHexTable)-1):
                    if f"{message[i]}" == self.AsciiHexTable[j][1]:
                        fixedmessage = fixedmessage + f"{self.AsciiHexTable[j][0]}"

        return fixedmessage


class MQTTClient:
    def __init__(self, uart):
        self.uart = uart
        self.ClientID = "Waveshare_RP2040_ETH"
        self.connect_message = bytearray([
            0x10,  # MQTT control packet type (CONNECT)
            0x11,  # Remaining Length in the fixed header
            0x00, 0x04,  # Length of the UTF-8 encoded protocol name
            0x4D, 0x51, 0x54, 0x54,  # MQTT string "MQTT"
            0x04,  # Protocol Level (MQTT 3.1.1)
            0xc2,  # Connect Flags: Clean Session, No Will, No Will Retain, QoS = 0, No Will Flag, Keep Alive = 60 seconds
            0x00, 0x3C  # Keep Alive Time in seconds

            #0x14, #length of client id
            #0x57, 0x61, 0x76, 0x65, 0x73, 0x68, 0x61, 0x72, 0x65, 0x5F, 0x52, 0x50, 0x32, 0x30, 0x34, 0x30, 0x5F, 0x45, 0x54, 0x48, 0x0A

        ])

    def connect(self):
        byte_array = bytes(self.ClientID, "utf-8")
        length = len(byte_array)
        self.connect_message.extend(length.to_bytes(2, 'big')) # Length of the Client ID
        self.connect_message.extend(byte_array) # Client ID

        self.connect_message.extend(len(USERNAME).to_bytes(2, 'big'))
        self.connect_message.extend(bytes(USERNAME, "utf-8"))

        self.connect_message.extend(len(PASSWORD).to_bytes(2, 'big'))
        self.connect_message.extend(bytes(PASSWORD, "utf-8"))


        self.connect_message[1] = len(self.connect_message) - 2 # Change Length
        #print(self.connect_message)
        self.uart.write(bytes(self.connect_message))

    def publish(self, topic, message):
        global LASTMESSAGE
        if LASTMESSAGE + 500000 > time.time_ns():
            print("Too fast message burst, waiting .125 seconds")
            time.sleep(0.25)
        publish_message = bytearray([
            0x30, 0x11,   # MQTT control packet type (PUBLISH)
            0x00, 0x0A    # Length of the topic name
        ])
        publish_message.extend(bytes(topic, "utf-8"))   # Topic
        publish_message.extend(bytes(message, "utf-8")) # Message content
        publish_message[1] = len(publish_message) - 2   # Change Length
        publish_message[3] = len(bytes(topic, "utf-8")) # Change Length
        if len(publish_message)<128:
            publish_message[1] = len(publish_message) - 2 # Change Length
        else:
            publish_message[1] = len(publish_message) - 2 #this will break if length is more than ami ebbe a bitbe belefér
            #publish_message.insert(2, bytes([0x01]))
            #print("ittstart")
            pubmes = bytearray([0x30])
            pubmes.extend(bytes([0x11]))
            pubmes[1] = len(publish_message) - 2
            pubmes.extend(bytes([0x01]))
            pubmes.extend(publish_message[2:])
            publish_message = pubmes
        #print("message:", publish_message)
        self.uart.write(bytes(publish_message))
        LASTMESSAGE = time.time_ns()

    def subscribe(self, topic):
        subscribe_message = bytearray([
            0x82, 0x0A,   # MQTT control packet type (SUBSCRIBE)
            0x00, 0x01    # Remaining length
        ])
        byte_array = bytes(topic, "utf-8")
        length = len(byte_array)
        subscribe_message.extend(length.to_bytes(2, 'big')) # Length of the topic name
        subscribe_message.extend(byte_array) # Topic
        subscribe_message.extend(bytes([0x00])) # qos
        subscribe_message[1] = len(subscribe_message) - 2 # Change Length
        self.uart.write(bytes(subscribe_message))

    def send_heartbeat(self):
        heartbeat_message = bytearray([0xC0, 0x00])# Heartbeat message to keep the connection alive
        self.uart.write(heartbeat_message)

    def check_heartbeat_response(self):
        response = self.uart.read()# Check for PINGRESP message
        if response == bytes([0xD0, 0x00]):
            return True
        else:
            return False

    def extract_data(self, rxData):
        rxArray = bytearray()
        rxArray.extend(rxData)
        try:
            if len(rxArray) < 128:
                topic = rxArray[4:4 + rxArray[3]].decode('utf-8')
                message = rxArray[4 + rxArray[3]:rxArray[1] + 2].decode('utf-8')
            else:
                topic = rxArray[5:5 + rxArray[4]].decode('utf-8')
                message = rxArray[5 + rxArray[4]:rxArray[1] + 3].decode('utf-8')
            return topic, message
        except Exception as e:
            print("An error occured while decoding a message:", rxArray)
            print(e)
            if str(e) == "UnicodeError: ":
                print("UnicodeError occured during the processing of an MQTT message")
                mqtt_client.publish(DEVICE_TOPIC, "PRTCL_LOG_ERROR:UnicodeError occured during the processing of an MQTT message")
            return None, None

class CH9120:
    def __init__(self, uart):
        self.uart = uart
        self.MODE = 1  #0:TCP Server 1:TCP Client 2:UDP Server 3:UDP Client
        self.GATEWAY = (192, 168, 0, 1)   # GATEWAY
        self.TARGET_IP = (192, 168, 0, 106)  # TARGET_IP
        self.LOCAL_IP = (192, 168, 0, 235)  # LOCAL_IP
        self.SUBNET_MASK = (255,255,252,0)  # SUBNET_MASK
        self.LOCAL_PORT = 1000              # LOCAL_PORT1
        self.TARGET_PORT = 1883             # TARGET_PORT
        self.BAUD_RATE = 115200             # BAUD_RATE
        self.CFG = Pin(18, Pin.OUT,Pin.PULL_UP)
        self.RST = Pin(19, Pin.OUT,Pin.PULL_UP)

    def enter_config(self):
        print("begin")
        self.RST.value(1)
        self.CFG.value(0)
        time.sleep(0.5)

    def exit_config(self):
        self.uart.write(b'\x57\xab\x0D')
        time.sleep(0.1)
        self.uart.write(b'\x57\xab\x0E')
        time.sleep(0.1)
        self.uart.write(b'\x57\xab\x5E')
        time.sleep(0.1)
        self.CFG.value(1)
        time.sleep(0.1)
        print("end")

    def set_mode(self,MODE):
        self.MODE = MODE
        self.uart.write(b'\x57\xab\x10' + self.MODE.to_bytes(1, 'little'))#Convert int to bytes
        time.sleep(0.1)

    def set_localIP(self,LOCAL_IP):
        self.LOCAL_IP = LOCAL_IP
        self.uart.write(b'\x57\xab\x11' + bytes(self.LOCAL_IP))#Converts the int tuple to bytes
        time.sleep(0.1)

    def set_subnetMask(self,SUBNET_MASK):
        self.SUBNET_MASK = SUBNET_MASK
        self.uart.write(b'\x57\xab\x12' + bytes(self.SUBNET_MASK))
        time.sleep(0.1)

    def set_gateway(self,GATEWAY):
        self.GATEWAY = GATEWAY
        self.uart.write(b'\x57\xab\x13' + bytes(self.GATEWAY))
        time.sleep(0.1)

    def set_localPort(self,LOCAL_PORT):
        self.LOCAL_PORT = LOCAL_PORT
        self.uart.write(b'\x57\xab\x14' + self.LOCAL_PORT.to_bytes(2, 'little'))
        time.sleep(0.1)

    def set_targetIP(self,TARGET_IP):
        self.TARGET_IP = TARGET_IP
        self.uart.write(b'\x57\xab\x15' + bytes(self.TARGET_IP))
        time.sleep(0.1)

    def set_targetPort(self,TARGET_PORT):
        self.TARGET_PORT = TARGET_PORT
        self.uart.write(b'\x57\xab\x16' + self.TARGET_PORT.to_bytes(2, 'little'))
        time.sleep(0.1)

    def set_baudRate(self,BAUD_RATE):
        self.BAUD_RATE = BAUD_RATE
        self.uart.write(b'\x57\xab\x21' + self.BAUD_RATE.to_bytes(4, 'little'))
        time.sleep(0.1)

    def enable_DHCP(self):
        self.BAUD_RATE = BAUD_RATE
        self.uart.write(b'\x57\xab\x33\x01')
        time.sleep(0.1)

    def disable_DHCP(self):
        self.BAUD_RATE = BAUD_RATE
        self.uart.write(b'\x57\xab\x33\x00')
        time.sleep(0.1)

    def getMac(self):
        global DEVICE_MAC
        DEVICE_MAC = ""
        #print("getmacbasic")
        uart1.write(b'\x57\xab\x81')
        time.sleep_ms(20)
        mac = uart1.read()
        #print(uart1.read())
        print(mac)
        #print("getmac end")

        #print("getmachexconvert")
        uart1.write(b'\x57\xab\x81')
        time.sleep_ms(20)
        mac2 = uart1.read()
        asci = ASCII()
        mac2 = asci.convert(mac2)
        #print(mac2)
        for i in range(0, (len(mac2)-1)/2):
            DEVICE_MAC = DEVICE_MAC + f"{mac2[i*2]}"
            DEVICE_MAC = DEVICE_MAC + f"{mac2[(i*2)+1]}"
            DEVICE_MAC = DEVICE_MAC + str("-")
        DEVICE_MAC = DEVICE_MAC.upper()[:-1]
        #print(DEVICE_MAC)
        #print("getmachexconvert end")

    def getIP(self):
        uart1.read()
        global DHCP_IP
        uart1.write(b'\x57\xab\x61')
        time.sleep_ms(20)
        DHCP_IP = uart1.read()
        DHCP_IP = f'{int(str(DHCP_IP).split("\\x")[1], 16)}.{int(str(DHCP_IP).split("\\x")[2], 16)}.{int(str(DHCP_IP).split("\\x")[3], 16)}.{int(str(DHCP_IP).split("\\x")[4][:-1], 16)}'
        print(DHCP_IP)


    def getGateway(self):
        global DHCP_GW
        uart1.write(b'\x57\xab\x63')
        time.sleep_ms(20)
        DHCP_GW = uart1.read()
        DHCP_GW = f'{int(str(DHCP_GW).split("\\x")[1], 16)}.{int(str(DHCP_GW).split("\\x")[2], 16)}.{int(str(DHCP_GW).split("\\x")[3], 16)}.{int(str(DHCP_GW).split("\\x")[4][:-1], 16)}'
        print(DHCP_GW)

    def getMask(self):
        global DHCP_MASK
        uart1.write(b'\x57\xab\x62')
        time.sleep_ms(20)
        DHCP_MASK = uart1.read()
        DHCP_MASK = f'{int(str(DHCP_MASK).split("\\x")[1], 16)}.{int(str(DHCP_MASK).split("\\x")[2], 16)}.{int(str(DHCP_MASK).split("\\x")[3], 16)}.{int(str(DHCP_MASK).split("\\x")[4][:-1], 16)}'
        print(DHCP_MASK)



def ch9120_configure():
    global uart1
    ch9120 = CH9120(uart1)
    ch9120.enter_config() # enter configuration mode
    #######################################################
    while len(DEVICE_MAC) != 17:
        ch9120.getMac()
        print(f"Device's MAC Adress: {DEVICE_MAC}")
    #######################################################
    ch9120.set_mode(MODE)
    #ch9120.set_localIP(LOCAL_IP)
    #ch9120.set_subnetMask(SUBNET_MASK)
    #ch9120.set_gateway(GATEWAY)
    ch9120.set_localPort(LOCAL_PORT1)
    ch9120.set_targetIP(TARGET_IP)
    ch9120.set_targetPort(TARGET_PORT)
    ch9120.set_baudRate(BAUD_RATE)
    ch9120.enable_DHCP()
    #ch9120.disable_DHCP()
    time.sleep(2)
    ch9120.getIP()
    ch9120.getGateway()
    ch9120.getMask()
    ch9120.exit_config()  # exit configuration mode'''


    # Clear cache and reconfigure uart1
    uart1.read(uart1.any())
    time.sleep(0.5)
    uart1 = UART(1, baudrate=115200, tx=Pin(20), rx=Pin(21))

def checkData(inp):
    if inp.split(",")[0] == MANUFACTURER and inp.split(",")[1] == MODEL and inp.split(",")[2] == HW_VERSION and inp.split(",")[3] == SW_VERSION and inp.split(",")[4] == CONFIGURL:
        return True
    else:
        return False

'''
IOarray = IOArray()
IOarray.addAI("LightSensor", 28)
IOarray.initAnalogIn()
IOarray.readAnalog()
IOarray.addDI("Switch", 4)
IOarray.initDigitalIn()
IOarray.readDigital()
'''

IOarray = IOArray()
prot = ProtocolBook()

if __name__ == "__main__":
    ch9120_configure()
    mqtt_client = MQTTClient(uart1)
    mqtt_client.ClientID = CLIENT_ID # Set ClientID
    mqtt_client.connect() # Connect to MQTT server
    mqtt_client.subscribe(CONFIG_RPLY_TOPIC) # Subscribe to topic：test_topic1

    mqtt_client.send_heartbeat()
    last_heartbeat_time = time.time()
    time.sleep_ms(60) # Sending the first heartbeat
    uart1.read() # Clear unnecessary data

    mqtt_client.publish(CONFIG_REQ_TOPIC, DEVICE_MAC)
    CONFIG_STATUS[0] = 1 #set config requested to true

    while True:
        rxData = uart1.read()
        if rxData is not None and len(rxData) > 6: #got message
            #print("Printing rxData.....")
            #print(rxData)
            topic, message = mqtt_client.extract_data(rxData) # Parse the received data
            #print("Printing topic:")
            #print(topic)
            #print("Printing message:")
            #print(message)
            if topic is None and message is None:
                continue
            if topic == CONFIG_RPLY_TOPIC:
                if DEVICE_MAC in message:
                    DEVICE_TOPIC = message.split(",")[1]
                    CONFIG_STATUS[1] = 1 # set got config to true
                    CLIENT_ID = DEVICE_TOPIC.split("/")[-1]
                    #reconnect
                    time.sleep(1)
                    print("Reconnecting...")
                    mqtt_client = MQTTClient(uart1)
                    mqtt_client.ClientID = CLIENT_ID # Set ClientID
                    mqtt_client.connect() # Connect to MQTT server
                    mqtt_client.subscribe(CONFIG_RPLY_TOPIC) # Subscribe to topic
                    mqtt_client.subscribe(DEVICE_TOPIC)
                    #reconnect
                    print(DEVICE_TOPIC)
                    time.sleep(1)
                    mqtt_client.publish(DEVICE_TOPIC, "HERE")
                    CONFIG_STATUS[2] = 1 # set sent ok on device channel to true
                    mqtt_client.subscribe(DEVICE_TOPIC)
                    print("Sent here message")

            elif topic == DEVICE_TOPIC:
                if message == "ping":
                    mqtt_client.publish(DEVICE_TOPIC, "ping ok")
                if message == "channel change ack":
                    CONFIG_STATUS[3] = 1 #set server acknowledge by server to true

                if message == "PRTCL_REMOTE:reload_pinconfig":
                    mqtt_client.publish(DEVICE_TOPIC, "PRTCL_LOG_INFO:Start setting up to reload pinconfig")
                    del IOarray #del ioarray
                    PINCONFIG = "" #config to default
                    PINCONFIG_STATUS = [0, 0, 0, 0, 0] #configstatus list to default
                    IOarray = IOArray() #create ioarray
                    mqtt_client.publish(DEVICE_TOPIC, "PRTCL_LOG_INFO:Finished setting up to reload pinconfig")

                if message == "PRTCL_REMOTE:restart":
                    mqtt_client.publish(DEVICE_TOPIC, "PRTCL_LOG_ERROR:IMPLEMENT RESTART COMMAND")

                if "PRTCL_PINCONFIG" in message and message != "PRTCL_PINCONFIG:REQUEST":
                    print(message.split(":")[1])
                    PINCONFIG = message.split(":")[1]
                    PINCONFIG_STATUS[1] = 1
                    PROTOCOL_TIME = time.time()
                if message == "PRTCL_READBACK:OK":
                    PINCONFIG_STATUS[3] = 1
                    PROTOCOL_TIME = time.time()
                if message == "PRTCL_READBACK:NOPE":
                    PINCONFIG_STATUS[1] = 0
                    PINCONFIG_STATUS[2] = 0
                    PROTOCOL_TIME = time.time()

                if message == "PRTCL_GETINFO:SELF":
                    mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_GIVEINFO_HW:MANUFACTURER={MANUFACTURER},MODEL={MODEL},HW_VERSION={HW_VERSION},SW_VERSION={SW_VERSION},CONFIGURL={CONFIGURL}")
                if message == "PRTCL_GETINFO:RUNTIME":
                    if DHCP_IP is None or DHCP_GW is None or DHCP_MASK is None:
                        ch9120_configure()
                        print("Some network related data is not avaible, reconfiguring CH9120")
                    """if DHCP_IP is None: DHCP_IP = 'n/a'
                    else: continue
                    if DHCP_GW is None: DHCP_GW ='n/a'
                    else: continue
                    if DHCP_MASK is None: DHCP_MASK = 'n/a'
                    else: continue"""

                    mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_GIVEINFO_RT:MODEL={MODEL},IP={DHCP_IP},GATEWAY={DHCP_GW},MASK={DHCP_MASK}")
                if "PRTCL_DVC_ASK:" in message:
                    if checkData(message.split(":")[1]) is True:
                        mqtt_client.publish(DEVICE_TOPIC, "PRTCL_DVC_OK")
                    else:
                        mqtt_client.publish(DEVICE_TOPIC, "PRTCL_DVC_FAIL")
                if message == "PRTCL_FORCEVALUES":
                        IOarray.forceValues()

############################################################################################################ new protocol controller
        prot.everyLoop()
        if PROTOCOL_TIME_SHORT < time.time():  # protocol long
            setpts()
            prot.protShort()
        if PROTOCOL_TIME < time.time():  # protocol
            setpt()
            prot.protNorm()
        if PROTOCOL_TIME_LONG < time.time():  # protocol long
            setptl()
            prot.protLong()
###########################################################################################################
        current_time = time.time()

        if current_time - last_heartbeat_time >= 30:
            mqtt_client.send_heartbeat() # Send a heartbeat every 30 seconds
            last_heartbeat_time = current_time
            time.sleep_ms(60) # Waiting for the server to respond
            if not mqtt_client.check_heartbeat_response():
                while True:
                    time.sleep(1)
                    print("Reconnecting...")
                    mqtt_client = MQTTClient(uart1)
                    mqtt_client.ClientID = CLIENT_ID # Set ClientID
                    mqtt_client.connect() # Connect to MQTT server
                    mqtt_client.subscribe(CONFIG_RPLY_TOPIC) # Subscribe to topic
                    mqtt_client.subscribe(DEVICE_TOPIC)
                    time.sleep_ms(200) # Waiting for the server to respond
                    uart1.read() # Clear unnecessary data
                    mqtt_client.send_heartbeat() # Sending the first heartbeat
                    last_heartbeat_time = current_time # Clear unnecessary data
                    time.sleep_ms(60) # Waiting for the server to respond
                    if mqtt_client.check_heartbeat_response():
                        print("Reconnection successful!")
                        mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_LOG_WARNING: Disconnected from broker, reconnected successfully")
                        break

        time.sleep_ms(0) # elozoleg 20 volt de most epp stabilabb az uart olvasas

### HA TOBB UZENET EGYSZERRE VAN BEOLVASVA ELHASSAL A TÉMA TELJESEN, NEM TUDJA DECODOLNI (uart readnel), valahgyo gyorstani kell a ciklusokat hiogy ne egybe találja meg az uzeneteket

### jelenelg nem megy a ping amig nem kap topic ack-ot a servertől, ezt ki kene javitani

### illetve server oldarol kell egy olyan fix hogy jelenleg nem megy amig pingel mintha blockolná az mqtt részt (addig nem kapja meg ennek az uzenetet amig irja ki a pingeket)

