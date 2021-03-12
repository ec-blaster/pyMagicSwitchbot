'''
Testing new branch which manages MagicSwitchBot devices

IMPORTANT: hcitool and python is not allowed to access bluetooth stack unless the user is root
          To solve it (unsecure):
          
            sudo apt-get install libcap2-bin
            sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
            sudo setcap 'cap_net_raw+ep' $(readlink -f $(which hcitool))
'''

import magicswitchbot

MAC1 = "34:14:b5:4a:28:0e"
MAC2 = "34:14:B5:4A:2A:24"
device = magicswitchbot.MagicSwitchbot(mac=MAC1, interface=1)
# device = magicswitchbot.MagicSwitchbot(mac=MAC2)

# device.turn_on()

'''Let's send the "get token" command to test the API:'''
device._sendCommand("0601", "", 3)

'''time.sleep(5)
device.turn_off()
'''
