'''
Testing MagicSwitchBot devices library

IMPORTANT: hcitool and python is not allowed to access bluetooth stack unless the user is root
          To solve it (unsecure):
          
            sudo apt-get install libcap2-bin
            sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
            sudo setcap 'cap_net_raw+ep' $(readlink -f $(which hcitool))
'''

from magicswitchbot import MagicSwitchbot
import time, logging

logging.basicConfig(level=logging.DEBUG)

MAC = "00:11:22:33:44:55"

device = MagicSwitchbot(mac=MAC, connect_timeout=10)

res = device.get_battery()
if res:
    print(f"Connected to device {MAC} with {res}% of battery remaining")
    time.sleep(1)
    
    print("Turning on...")
    if device.turn_on():
        print("Command executed successfully")
    else:
        print("Error sending command")
    time.sleep(1)
    
    print("Turning off...")
    if device.turn_off():
        print("Command executed successfully")
    else:
        print("Error sending command")
    time.sleep(1)
    
    print("Pushing...")
    if device.push():
        print("Command executed successfully")
    else:
        print("Error sending command")
else:
    print("Could't get battery status")
