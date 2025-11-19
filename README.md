# Modular Control And Sensor System

## 🦺README.md under construction...🦺

### The inspiration and goal of the project:

I've gotten into home automatisation and with that into IOT in 2023 and since then i tried to integrate as much of the stufff in our home into Home Assistant as I could. Well it didn't go as easily as I though. A lot of stuff was buggy, got deprecated and lost support or just was bad in the first place, or the devices weren't suitable for the task given to them. So in September of 2025 i got fed up started working on my own system which led to the MCASS Project.
This project's goal is create an easy to set up, fully modular and heavily customisable system, that is able to monitor and control it's environment.

### Main features (or them to be):
(!!!Some of the lower mentioned features are not implemented yet, but are planned to be in the final version!!!)

On the long run I want to create two main versions of this, with maybe a third option as a hybrid of the first two.
 - Home Edition
   - Maybe lose the control server entirely, with integrating into HASS
   - End devices would use MDNS to find the server and connect to it
   - Also would use Mosquito built into HASS
 - Enterprise edition
   - Two separate brokers
    - The first one would be responsible for the base configuration the device, and this server would have a fix IP address on every network calculated by a simple algorith (eg: take the 15th avaible IP of the network, or the middle IP of the newtork.)
    - The second one would be where the actual traffic and communication between the server and end devices would take place. This broker can take any IP
   - It could be configurable in the server which IP the second broker would be in, and the configuration would be sent via the first broker in the initial configuration of the end device.
   - Option for backup server that monitors traffic and when detects an outage in the main server it takes over.

### Current standing:

### Next steps in development (what to be expected):

### CONFIGURATION.txt entries and their default values:

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
