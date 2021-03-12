'''
Testing new branch which manages MagicSwitchBot devices

IMPORTANT: hcitool and python is not allowed to access bluetooth stack unless the user is root
          To solve it (unsecure):
          
            sudo apt-get install libcap2-bin
            sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
            sudo setcap 'cap_net_raw+ep' $(readlink -f $(which hcitool))
'''

import magicswitchbot
import time

MAC1 = "34:14:b5:4a:28:0e"
MAC2 = "34:14:B5:4A:2A:24"

# ha-nodo1:
# device = magicswitchbot.MagicSwitchbot(mac=MAC1, interface=1)

# alef-mint:
device1 = magicswitchbot.MagicSwitchbot(mac=MAC1)
device2 = magicswitchbot.MagicSwitchbot(mac=MAC2)

for a in range(2):
    device1.turn_on()
    device2.turn_off()
    time.sleep(1)
    device1.turn_off()
    device2.turn_on()
    time.sleep(1)

'''device.turn_on()
time.sleep(5)
device.turn_off()
time.sleep(5)
device.toggle()
time.sleep(5)
device.toggle()

'''
