import time
import datetime
import requests


################
### Settings ###

# Home Assistant
token = ""
ha_url = "http://homeassistant.local:8123/api/"

# First the procution sensor, then the consumption sensor in this format: "sensor.xxx_production,sensor.xxx_consumption"
sensors = "sensor.sonnenbatterie_state_production_w,sensor.sonnenbatterie_state_consumption_w"
url_battery = "http://homeassistant.local:8123/api/states/sensor.sonnenbatterie_state_charge_real"

# The number is the estimated or average wattage of the device.
# Do not set it too low that the device does not turn on to early and uses the grid,
# but also don't set it too high because you will need a lot of overproduction that the device turns on.
#
# The priority isn't implemented yet. But it will be used for devices which are only turned on if the energy
# gets exported and lets the battery charge with the max available watts.
devices = {
            "switch.heizteppich_kuche": [300, 1],
            "switch.heizteppich_esszimmer": [660, 1],
            "switch.heizung_bad_unten": [900, 1],
            "switch.heizung_werkstatt": [1500, 1], # Priority = 9
          }
       
# Do you have a battery? If not, set to False and ignore the charge power options
has_battery = True
# You can configure the times below, directly in the script.
# This adds some logic to the battery charging. You can read more info about this below in the script.
timebased_battery = True

# Battery charge power
battery_charge_max = 3400 # The maximum wattage that you battery is able to be charged with
charge_battery_medium = 800 # Custom: As long as the battery is not full (95% and below), the consumption will virtually be enlarged by that value so the battery will charge during the day
charge_battery_min = 300 # Same as medium, but only if the battery has 95%+. Can safely set to 0 if you don't need that extra 5%.

### END settings ###
####################



def calculate(powered_on_devices, production, consumption, export, battery, firstRun):
    excess = production - consumption

    # Removes the consumption of the device from the consumption value.
    # This prevents that the devices are turned on and off in a loop because
    # if the device turns on, more power is consumed. In the next loop it would
    # turn off that device because of the higher power consumption.
    for device in powered_on_devices:
        excess += devices[device][0]
    
    power_off_devices = [] # A list with devices that will be turned off (all devices that aren't turned on)
    power_on_devices = []
    
    estimated_consumption = 0 # Estimated consumption of all devices in the list
    
    if has_battery:
        battery_time_force = False
        if timebased_battery:
            # Do not turn on any devices if battery is lower than 85% after 15:00 or battery is lower than 75% after 12:00
            # 15:00: The battery should have at least 85% at this time because it might not manage to charge the battery until night
            # 12:00: Turn on devices early in the morning but if the battery is low after 12:00, store the energy because it might not manage to charge the battery until night
            now = datetime.datetime.now().time()
            if (battery < 95 and now.hour >= 15) or (battery < 75 and now.hour >= 12): 
                excess -= battery_charge_max
                battery_time_force = True
                print("Battery percentage lower than 85% ({}%) at hour {}. Do not turn on any devices.".format(battery, now.hour))
        
        
        if not battery_time_force:
            if battery < 30: # 0 - 30%
                excess -= battery_charge_max # Charge the battery with max possible power (do not turn on any devices)
        
            elif battery < 95: # 30-95%
                excess -= charge_battery_medium # Charge battery with medium power (only turn on devices if the battery charges with at least medium watts)
            
            elif battery < 95: # 95-100%
                excess -= charge_battery_min # Charge battery with low power (Prever to turn on devices, but leave the battery some power to charge)
    
    for device_name in devices:
        device_consumption = devices[device_name][0] # Consumption in Watts
        device_priority = devices[device_name][1]
        estimated_consumption += device_consumption # Add device consumption to the total estimated consumption
        
        print('Device {}: Consumption {}; Priority: {}'.format(device_name, device_consumption, device_priority))
        
        # Power on device as soon as there is enough power (ignore battery percentage)
        if device_priority == 0:
            print("Nothing here yet")
        # Priority 1 == Power on device based on solar production and battery percentage.
        # If the battery is low, prefer to charge it with full speed until a specific percentage, then power on devices,
        # but leave some power to charge the battery during the day. When the battery is (almost) fully charged, use all watts for the devices.
        if device_priority == 1:
            if estimated_consumption > excess:
                if firstRun:
                    power_off_devices.append(device_name)
                if device_name in powered_on_devices:
                    power_off_devices.append(device_name)
                    powered_on_devices.remove(device_name)
            else:
                if not device_name in powered_on_devices:
                    power_on_devices.append(device_name)
                    powered_on_devices.append(device_name)
        
        # Only power on devices if the energy would get exported otherwise. (Battery fully charged and overproduction)
        if device_priority == 9:
            if export > device_consumption:
                print("Nothing here yet")
        
    for device in power_on_devices:
        url = "{}services/switch/turn_on".format(ha_url)
        data = '{"entity_id": "'+device+'"}'

        output = requests.post(url, data=data, headers=headers)
        print('Powered on device {}'.format(device))
        
       
    for device in power_off_devices:
        url = "{}services/switch/turn_off".format(ha_url)
        data = '{"entity_id": "'+device+'"}'

        output = requests.post(url, data=data, headers=headers)
        print('Powered off device {}'.format(device))
        
    print('All powered on devices: {}'.format(powered_on_devices))
    print('Excess without powered on devices: {}'.format(excess))
    
    
def loop():
    haHistory = datetime.datetime.now() - datetime.timedelta(seconds=10)
    sensor_url = "{}history/period/{}?minimal_response&filter_entity_id={}".format(ha_url, haHistory, sensors)
    
    # Gets sensor data history
    request = requests.get(sensor_url, headers=headers).json()
    battery = int(requests.get(url_battery, headers=headers).json()['state'])
            
    production_request = request[0]
    production_length = len(production_request)
    production_total = 0
    for output in production_request:
        production_total += int(output['state'])
    production_average = int(production_total / production_length)
    
    consumption_request = request[1]
    consumption_length = len(consumption_request)
    consumption_total = 0
    for output in consumption_request:
        consumption_total += int(output['state'])
    consumption_average = int(consumption_total / consumption_length)
    
    #export_request = request[2]
    #export_length = len(export_request)
    #export_total = 0
    #for output in export_request:
    #    export_total += int(output['state'])
    #export_average = int(export_total / export_length)
    
    export_average = 0
        
    print('Average (1min) - Production: {}; Consumption: {}; Export: {}'.format(production_average, consumption_average, export_average))


    calculate(powered_on_devices, production_average, consumption_average, export_average, battery, firstRun)
    print('\n')
    
if __name__ == "__main__":
    run = True
    
    firstRun = True
    
    headers =  {"Authorization": "Bearer {}".format(token), "Content-Type":"application/json"}
    
    powered_on_devices = []
    
    while(run):
        try:
            loop()
        except requests.exceptions.RequestException as e:
            print("Could not connect to HomeAssistant!")
            #print("Exception: {}".format(e))
        except:
            print("Something went wrong. Trying again in 15 seconds. Is HA reachable? Do you have the correct AUTH token?")

        time.sleep(15)
        
        firstRun = False
        
        #run = False
        
