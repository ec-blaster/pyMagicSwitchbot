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

MAC1 = "34:14:b5:4a:28:0e"
MAC2 = "34:14:B5:4A:2A:24"

device = MagicSwitchbot(mac=MAC1)

device.connect(30)

res = device.get_battery()
print(f"Connected to device {MAC1} with {res}% of battery remaining")

for t in range(60):
    time.sleep(60)
    print(f"{t+1} minutes elapsed...")
    if not device.is_connected():
        print("Connection with the device is lost")
        break
