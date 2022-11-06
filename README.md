# solar-controller
A python script that controls devices according to the current solar productions with HomeAssistant

## Important: You need some basic python knowledge to configure and modify the script. This project isn't really user-oriented as I mainly programmed this for myself but wanted to share it.

# Installation
- Download the solar_control.py file to some kind of server (for example a Raspberry Pi).
- Open the file, create a HA-Auth-Token and paste it in the variable.
- Configure your sensors and HA-URL
- Configure the devices. You need to know how much current they draw in watts.
  If the watts are changing a lot, use the power peaks to be safe, or some other high base current.
  This is needed because the scripts needs to calculate the estimated current so it can turn on/off devices correctly.
- Start the python script on a server and let it run. You can let it run in a screen if you want to close the terminal.

### screen
```
sudo apt install screen -y
screen -dm python3 /path/to/solar_control.py
```
