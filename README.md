# Modular Control And Sensor System

## 🦺README.md under construction...🦺



### CONFIGURATION.txt entries and their default values:

 - PROTOCOL_TIMEOUT_SHORT = 0.5  
   - Time after which frequent protocols are executed  
 - PROTOCOL_TIMEOUT = 5  
  Time after which normal protocols are executed  
PROTOCOL_TIMEOUT_LONG = 60  
  Time after which periodical protocols are executed  
BROKER = "127.0.0.1"  
  Broker for the MQTT messaging to be used (Reccomended is to use the one in HASS)  
PORT = 1883  
  Port for the MQTT broker  
CONFIGREQUEST = "test/config/request"  
  Topic for the devices to request their config from  
CONFIGREPLY = "test/config/reply"  
  Topic where the requested config should be sent  
DEVICETOPIC = "test/devices/#"  
  Topic of each device connected  
USERNAME = ""  
  Username for the MQTT broker  
PASSWORD = ""  
  Password for the MQTT broker  
CLIENT_ID = "MQTTControlServer1"  
  Client ID which the server should use to connect to the broker  
TBCCONFLICTHANDLE ="error"  
  Servers lists out unconfigured devices which requested config. T(o)B(e)C(onfigured) conflict handle option decides what to do if a device is in TBC but got configured since  
    - error : Does not modify the file, puts out and error log for it  
    - delete : Deletes entry from TBC
HAK = ""
  Key to the Home Assistant API
HASS = broker
  IP Address of Home Assistant
    Setting it to "broker" will result in using the IP of the broker. If a different IP is to be used, format it according to BROKER
