from machine import UART, Pin
from machine import I2C
import machine
import time
import ubinascii


#pinconfighoz kikötesek
#scl es sda nem lehet ugyanaz a pin
#ha van i2c cim akkor legyen scl sda config is, ha nincs send error vagy valamifele ellenorzes
#hogyha van már valami azon a pinen ne inditsa rá (és az elozot ami mar fogja azt a pint üsse ki mert görcs tudj amelyik van elirva)

TIMEOUT = 5 #protocolcheck timout in seconds
PROTOCOL_TIME = time.time() + TIMEOUT 

# MQTT
CLIENT_ID = "Waveshare_RP2040_ETH"
CONFIG_RPLY_TOPIC = "test/config/reply"
CONFIG_REQ_TOPIC = "test/config/request"
DEVICE_TOPIC = ""
USERNAME = "mqttuser"
PASSWORD = "mqtt"

DEVICE_MAC = ""#"3C-AB-72-96-52-F4"
CONFIG_STATUS = [0, 0, 0, 0] #requested config, got config, sent ok on device topic, got acknoledged
PINCONFIG_STATUS=[0, 0, 0, 0, 0] #requested pinconfig, got config, readback, readback ok received , started pinconfig ez mar az IOArraybol kell jojjon
PINCONFIG = ""
# CH9120
MODE = 1  #0:TCP Server 1:TCP Client 2:UDP Server 3:UDP Client
GATEWAY = (192, 168, 0, 1)     # GATEWAY
TARGET_IP = (192, 168, 0, 106)  # TARGET_IP
LOCAL_IP = (192, 168, 0, 139)  # LOCAL_IP
SUBNET_MASK = (255,255,255,0)  # SUBNET_MASK
LOCAL_PORT1 = 1000             # LOCAL_PORT1
TARGET_PORT = 1883             # TARGET_PORT
BAUD_RATE = 115200             # BAUD_RATE

uart1 = UART(1, baudrate=9600, tx=Pin(20), rx=Pin(21))


class IOArray:
    #need a func to add them to the list
    #need a func to periodically get data and send them to server
    #dont send value if value is "value", inicializalashoz kell valami a listaba de lehetseges erteket nem irhatok bele mer szetbaszna a statot
    #maybe do a check hogy ne akarjak ADC-t egy olyan pinen amin nincs adc
    
    #ha pinconfig = None akkor ne csinaljon semmit, nincs config megadva
    
    #update idea, theres options for pullup/pulldown, maybe add the possibility to define pullup/down in config
    
    #még az i2c nincs meg!!!!!!!
    
    analogInList=[] 	#mindegyiknel
    digitalInList=[]	#elso a név
    digitalOutList=[]	#masodik a pin number
    i2cAddressList=[]	#harmadik a pindefinicio
    pwmOutList=[]		#negyedik a sensor value
    SCL=0
    SDA=0
    
    newValList=[]
    
    def __init__(self):
        print("IOArray init")
        
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
            elif "DigitalRead" in configList[i]:
                self.addDI(configList[i].split("@")[1], configList[i].split("@")[2])
            elif "DigitalOut" in configList[i]:
                self.addDO(configList[i].split("@")[1], configList[i].split("@")[2])
            elif "PWMOut" in configList[i]:
                self.addPWMO(configList[i].split("@")[1], configList[i].split("@")[2])
            elif "SDA" in configList[i]:
                self.SetSDA(configList[i].split("@")[1])
            elif "SCL" in configList[i]:
                self.SetSCL(configList[i].split("@")[1])
            elif "0x" in configList[i]:
                self.addi2cAddress(configList[i].split("@")[0], configList[i].split("@")[1])
            else:
                print(f"Unkown IO parameter was given in section: {configList[i]}")
        print(f"\n{self.analogInList}\n{self.digitalInList}\n{self.digitalOutList}\n{self.i2cAddressList}\n{self.pwmOutList}\n")
        self.initAnalogIn()
        self.initDigitalIn()
        self.initDigitalOut()
        self.initPWMOut()
        
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
        self.i2cAddressList.append(f"{deviceName}@{address}@pindef@value@lastval".split("@"))
        print(f"Successfully added {deviceName} device with address {address} to i2c address list")
    
    #initialize and read/write fucntions---------------------------------------------------------------       
        
    def initAnalogIn(self):
        for i in range(0, len(self.analogInList)):
            self.analogInList[i][2] = machine.ADC(int(self.analogInList[i][1]))
    
    def readAnalog(self):
        for i in range(0, len(self.analogInList)):
            self.analogInList[i][4] = self.analogInList[i][3]
            self.analogInList[i][3] = self.analogInList[i][2].read_u16()
            print(f"{self.analogInList[i][0]} with value of {self.analogInList[i][3]}")
    #*******************************        
    def initDigitalIn(self):
        for i in range(0, len(self.digitalInList)):
            self.digitalInList[i][2] = machine.Pin(int(self.digitalInList[i][1]), machine.Pin.IN)
            
    def readDigital(self):
        for i in range(0, len(self.digitalInList)):
            self.digitalInList[i][4] = self.digitalInList[i][3]
            self.digitalInList[i][3] = self.digitalInList[i][2].value()
            print(f"{self.digitalInList[i][0]} with value of {self.digitalInList[i][3]}")
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
                
    def getVals(self):
        self.readAnalog()
        self.readDigital()
        #read I2C
        for i in range(0, len(self.analogInList)):
            if self.analogInList[i][3] != self.analogInList[i][4]:
                self.newValList.append(f"{self.analogInList[i][0]}@{self.analogInList[i][3]}")
            else:
                print(f"No new value for {self.analogInList[i][0]}, skipping send data")
        for i in range(0, len(self.digitalInList)):
            if self.digitalInList[i][3] != self.digitalInList[i][4]:
                self.newValList.append(f"{self.digitalInList[i][0]}@{self.digitalInList[i][3]}")
            else:
                print(f"No new value for {self.digitalInList[i][0]}, skipping send data")
        #send data
        for i in range(0, len(self.newValList)):
            mqtt_client.publish(DEVICE_TOPIC, f"{self.newValList[i]}")
        self.newValList.clear()
        

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
        print(self.connect_message)
        self.uart.write(bytes(self.connect_message))

    def publish(self, topic, message):
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
            print("ittstart")
            pubmes = bytearray([0x30])
            pubmes.extend(bytes([0x11]))
            pubmes[1] = len(publish_message) - 2
            pubmes.extend(bytes([0x01]))
            pubmes.extend(publish_message[2:])
            publish_message = pubmes
        print("message:")
        print(publish_message)
        self.uart.write(bytes(publish_message))

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
        if len(rxArray) < 128:
            topic = rxArray[4:4 + rxArray[3]].decode('utf-8')
            message = rxArray[4 + rxArray[3]:rxArray[1] + 2].decode('utf-8')
        else:
            topic = rxArray[5:5 + rxArray[4]].decode('utf-8')
            message = rxArray[5 + rxArray[4]:rxArray[1] + 3].decode('utf-8')
        return topic, message

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
    ch9120.exit_config()  # exit configuration mode'''
    
    
    # Clear cache and reconfigure uart1
    uart1.read(uart1.any())
    time.sleep(0.5)
    uart1 = UART(1, baudrate=115200, tx=Pin(20), rx=Pin(21))
    
    
'''
IOarray = IOArray()
IOarray.addAI("LightSensor", 28)
IOarray.initAnalogIn()
IOarray.readAnalog()
IOarray.addDI("Switch", 4)
IOarray.initDigitalIn()
IOarray.readDigital()
'''

IOArray = IOArray()

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
            print(rxData)
            topic, message = mqtt_client.extract_data(rxData) # Parse the received data
            #print("Printing topic:")
            print(topic)
            #print("Printing message:")
            print(message)
            if topic == CONFIG_RPLY_TOPIC:
                if DEVICE_MAC in message:
                    DEVICE_TOPIC = message.split(",")[1]
                    CONFIG_STATUS[1] = 1 # set got config to true
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
                if "PRTCL_PINCONFIG" in message and message != "PRTCL_PINCONFIG:REQUEST":
                    print(message.split(":")[1])
                    PINCONFIG = message.split(":")[1]
                    PINCONFIG_STATUS[1] = 1
                if message == "PRTCL_READBACK:OK":
                    PINCONFIG_STATUS[3] = 1
                if message == "PRTCL_READBACK:NOPE":
                    PINCONFIG_STATUS[1] = 0
                    PINCONFIG_STATUS[2] = 0
                
        
############################################################################################################
        if PROTOCOL_TIME <= time.time():
            print("Protocolcheck")
            
        #config protocols
            if CONFIG_STATUS[1] == 0: #no config reply yet
                print("No config reply, asking again")
                mqtt_client.publish(CONFIG_REQ_TOPIC, DEVICE_MAC)
                CONFIG_STATUS[0] = 1 #set config requested to true
            if CONFIG_STATUS[3] == 0 and CONFIG_STATUS[2] == 1: #no topic change ack yet and sent here message
                print("No topic ack, asking again")
                mqtt_client.publish(DEVICE_TOPIC, "HERE")
                
        #pinconfig protocols
            if CONFIG_STATUS[3] == 1:#csak akkor kerje a pinconfigot ha mar teljesult az mqtt config
                
                if PINCONFIG_STATUS[3] == 1 and PINCONFIG_STATUS[4] == 0:
                    print("pinconfig ok, start pinconfig on hardware")
                    print(PINCONFIG)
                    IOArray.autoSetup(PINCONFIG)
                
                if PINCONFIG_STATUS[2] == 1 and PINCONFIG_STATUS[3] == 0: #no ack of readback yet
                    mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_READBACK:{PINCONFIG}")
                
                if PINCONFIG_STATUS[1] == 1 and PINCONFIG_STATUS[2] == 0: #got config, no readback
                    mqtt_client.publish(DEVICE_TOPIC, f"PRTCL_READBACK:{PINCONFIG}")
                    PINCONFIG_STATUS[2] = 1

                if PINCONFIG_STATUS[0] == 1 and PINCONFIG_STATUS[1] == 0: #requested config yet no reply
                    mqtt_client.publish(DEVICE_TOPIC, "PRTCL_PINCONFIG:REQUEST")
                
                if PINCONFIG_STATUS[0] == 0: #not yet requested config 
                    mqtt_client.publish(DEVICE_TOPIC, "PRTCL_PINCONFIG:REQUEST")
                    PINCONFIG_STATUS[0] = 1
            
            if PINCONFIG_STATUS[4] == 1:
                IOArray.getVals()
                    
            PROTOCOL_TIME = time.time() + TIMEOUT
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
                    mqtt_client.subscribe(CONFIG_RPLY_TOPIC) # Subscribe to topic：test_topic1
                    mqtt_client.subscribe(DEVICE_TOPIC)
                    time.sleep_ms(200) # Waiting for the server to respond
                    uart1.read() # Clear unnecessary data
                    mqtt_client.send_heartbeat() # Sending the first heartbeat
                    last_heartbeat_time = current_time # Clear unnecessary data
                    time.sleep_ms(60) # Waiting for the server to respond
                    if mqtt_client.check_heartbeat_response():
                        print("Reconnection successful!")
                        break
            
        time.sleep_ms(0) # elozoleg 20 volt de most epp stabilabb az uart olvasas

