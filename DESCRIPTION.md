# This file was created in order to make both the server and end device side of the workflow be more easily understood, while also clarifying and listing all configuration options 

## CONFIGURATION.txt format, possible entries and their default values:

### Formatting
  - Each entry has to be written into a new line
  - Each line consists of 3 parts:
    - The name of the paramter you want to give:
      - Start of the line, written in caps lock
    - "=" separator
    - And the value you want to set it to

### Possible entries

 - PROTOCOL_TIMEOUT_SHORT = 0.5  
   - Time after which frequent protocols are executed  
 - PROTOCOL_TIMEOUT = 5  
   - Time after which normal protocols are executed  
 - PROTOCOL_TIMEOUT_LONG = 60  
   - Time after which periodical protocols are executed  
 - BROKER = "127.0.0.1"  
   - Broker for the MQTT messaging to be used (Reccomended is to use the one in HASS)  
 - PORT = 1883  
   - Port for the MQTT broker  
 - CONFIGREQUEST = "home/config/request"  
   - Topic for the devices to request their config from  
 - CONFIGREPLY = "home/config/reply"  
   - Topic where the requested config should be sent  
 - DEVICETOPIC = "home/devices/#"  
   - Topic of each device connected  
 - USERNAME = ""  
   - Username for the MQTT broker  
 - PASSWORD = ""  
   - Password for the MQTT broker  
 - CLIENT_ID = "MQTTControlServer1"  
   - Client ID which the server should use to connect to the broker  
 - TBCCONFLICTHANDLE ="error"  
   - Servers lists out unconfigured devices which requested config. T(o)B(e)C(onfigured) conflict handle option decides what to do if a device is in TBC but got configured since  
    - error : Does not modify the file, puts out and error log for it  
    - delete : Deletes entry from TBC
 - HAK = ""
   - Key to the Home Assistant API
 - HASS = broker
   - IP Address of Home Assistant
   - Setting it to "broker" will result in using the IP of the broker. If a different IP is to be used, format it according to BROKER
  
## Configtable.txt format:
Each row has the configuration for a device:
  - Every row has to contain 3 main components: the mac address of the device, the topic of the device to use, and the pin configuration
  - Each of the main component is separated by "," characters
  
In the pin configuration section each entry is divided by the "/" character
  - Each entry has to contain type to be configured, the name of the pin, and the number of pin to use
  - Each of these are separated by "@" characters
    - The type has to be the main thing that you would program into a normal program
      - Can be "AnalogRead", "DigitalRead", "DigitalOut", "PWMOut" or <SPECHARDWARE>
      - SPECHARDWARE: Any hardware that needs separate support, and does not fall in the category of the previous four options (eg: BMP180)
      - <TBD list of supported hardware>
    - Optional domain defining:
      - **Highly recommended in case of using HASS**:
      - You can define the domain to be used in HASS.
      - This will determine that the given entry how will be integrated into HASS
      - It can be added after the name without any spaces, within "(" ")" characters
  - Special entries:
    - SCL and SDA pins
      - These do not require a name, just "SDA" or "SCL" and a pin
    - If multiple pins are required, separate them with a "&" characcter (eg: in case of a rotary encoder)
  - Modifiers:
    - EC (Every Cycle)
      - Adding "@EC" at the end of an entry will make so that the end device reads the state every cycle, not just at protocol times
      - This will only affect inputs ("AnalogRead", "DigitalRead", and <SPECHARDWARE>

***Example entry:***
*AA-BB-CC-DD-EE-FF,MCASS/devices/doesntexist,Rotary@Rotary@2&3@EC/DHT11@DHT(Sensor)@7*
The 3 main sections:
  - AA-BB-CC-DD-EE-FF
  - MCASS/devices/doesntexist
  - Rotary@Rotary@2&3@EC/DHT11@DHT(Sensor)@7

Pinconfig broken up more:
  - Rotary@Rotary@2&3@EC:
    - Rotary *Type*
    - Rotary *Name*
    - 2&3 *Pins*
    - EC *Every Cycle modifier*
  - DHT11@DHT(Sensor)@7
    - DHT11 *Type*
    - DHT *Name*
    - (Sensor) *Domain*
    - 7 *Pin*
