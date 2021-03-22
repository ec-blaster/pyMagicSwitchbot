'''
Testing new branch which manages MagicSwitchBot devices

IMPORTANT: hcitool and python is not allowed to access bluetooth stack unless the user is root
          To solve it (unsecure):
          
            sudo apt-get install libcap2-bin
            sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
            sudo setcap 'cap_net_raw+ep' $(readlink -f $(which hcitool))
'''

from magicswitchbot import MagicSwitchbot
import time, logging

logging.basicConfig(level=logging.INFO)

MAC = "00:11:22:33:44:55"

device = MagicSwitchbot(mac=MAC)

device.connect(5,30)

res = device.get_battery()
print(f"Connected to device {MAC} with {res}% of battery remaining")

time.sleep(1)

device.turn_on()

time.sleep(1)

device.turn_off()

time.sleep(1)

device.push()
