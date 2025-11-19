# Modular Control And Sensor System

## 🦺README.md under construction...🦺

### The inspiration and goal of the project:

I've gotten into home automatisation and with that into IOT in 2023 and since then i tried to integrate as much of the stufff in our home into Home Assistant as I could. Well it didn't go as easily as I though. A lot of stuff was buggy, got deprecated and lost support or just was bad in the first place, or the devices weren't suitable for the task given to them. So in September of 2025 i got fed up started working on my own system which led to the MCASS Project.
This project's goal is create an easy to set up, fully modular and heavily customisable system, that is able to monitor and control it's environment.

### Main features (or them to be):
*(!!!Some of the lower mentioned features are not implemented yet, but are planned to be in the final version!!!)*

On the long run I want to create two main versions of this, with maybe a third option as a hybrid of the first two.
 - Home Edition
   - Option to take the server seperately or in a HASS integration
   - End devices would use MDNS to find the server and connect to it
   - Also would use Mosquito built into HASS with no option for seperate broker
 - Enterprise edition
   - Two separate brokers
    - The first one would be responsible for the base configuration the device, and this server would have a fix IP address on every network calculated by a simple algorith (eg: take the 15th avaible IP of the network, or the middle IP of the newtork.)
    - The second one would be where the actual traffic and communication between the server and end devices would take place. This broker can take any IP
   - It could be configurable in the server which IP the second broker would be in, and the configuration would be sent via the first broker in the initial configuration of the end device.
   - Option for backup server that monitors traffic and when detects an outage in the main server it takes over.

### Current standing:

In a few words: Very alpha testing
On the end device part it is a midway and base code currently for the two versions. It is only missing the MDNS and the IP based connection. (It is using a fix programmed IP for testing and development)
On the server side it's very close to a beta version. The server configuration is avaible, I'm currently working on the HASS side so that all devices are automatically created in HASS via MQTT Discovery.

### Next steps in development (what to be expected):

Finish the HASS configuration part 
  - Implement the forwarder, which is responsible for forwarding the state and control data from end device to HASS and vice versa
  - Implement the ping function to check the availability of devices and report it to HASS
  - HASS syncronisation so something got changed in HASS (eg: Icon of entity) it is updated in the server
Implement some protocols for checking the validity of information on devices (eg: if the software got updated on it)
Implement a protocol where it checks if the end device supports a certain sensor, and deal with it appropriately (Currently the end device ignores a not supported hardware if it was given in the config, so there has to be a protocol to ask the end device for what is has a support for (It is stored in the program))

### Long term goals: 

Of course making it of the most useful projects for the community
But seriously (not in order):
  - Separating the Home and Enterprise versions
  - Adding support for more off board hardware (NFC readers, Oxigen sensors and anything that is requested and can be fulfilled)
  - Adding support for more boards (Expand and adapt for ESP, Arduino boards and any development board that is widespread among the IOT community)
  - Adding option for backup server
  - Multithreading (mainly on server side, but possibly on any end device that supports it)
  - Adding support for EEPROM caching so initial setup of end devices are faster and create less stress on the server (although a chechkup of the saved config is necessary to find out if it is still valid on need to be re-cached)
  - Adding support remote nodes. These would leverage the connection of a 'main' end device while using it sort of like a proxy for communicating with the server, this way the network would be loaded with devices. This would probably use I2C as the form of communicating between the remote node (or subdevice) and the end device with the actual network connection
  - Remote control (maybe web?) of the main server, so it could be configured from a remote computer from the web and not in a txt file directly on the server.
  - Remote control of end devices, so if it has a config changed it could be updated without the need to restart the device and go there physically (besides changing the hardware)
  - Runtime reconfiguration and restarts both on server and end device side. This way if a configuration got changed (eg: en device got a new sensor) we do not need to restart the entire server or device
  - And other ideas that may come with feature requests....

### Closing notes:
This project might get the attention of some people and I belive it could be useful for the most of us, so I'm trying my best to allocate as much time to this as I can, but I'm a university student, who is also working a job, so I don't exactly have 12 hours a day that I am able to dedicate to this poject.
What I want to say that development might be slow but steady, and all I ask for is your patience.
Thank you in advance for using my sofware and for all of your helpful feedbacks!

