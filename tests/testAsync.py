'''
Testing MagicSwitchBot devices library

IMPORTANT: hcitool and python is not allowed to access bluetooth stack unless the user is root
          To solve it (unsecure):
          
            sudo apt-get install libcap2-bin
            sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
            sudo setcap 'cap_net_raw+ep' $(readlink -f $(which hcitool))
'''

from magicswitchbotasync import MagicSwitchbot
import time, logging, asyncio
from bleak.backends.device import BLEDevice

logging.basicConfig(level=logging.DEBUG)

MAC = "00:11:22:33:44:55"
MAC = "fc:45:c3:75:c9:ae"
PASSWORD = None

async def main():
  ble_device = BLEDevice(MAC, "any")
  
  device = MagicSwitchbot(ble_device)
  #device = MagicSwitchbot(mac=MAC, connect_timeout=15, disconnect_timeout=10, password=PASSWORD)
  
  print(f"Connecting to MagicSwitchbot device at {MAC}...")
  
  await device.turn_on()
  
  print("Testing finished")

asyncio.run(main())

'''res = device.get_battery()
if res:
    print(f"Connected to MagicSwitchbot device at {MAC} with {res}% of battery remaining")
    time.sleep(1)
   
    print("Turning on...")
    ok = device.turn_on() 
    if ok:
        print("Command executed successfully")
        time.sleep(1)
        
        print("Turning off...")
        ok = device.turn_off()
        if ok:
            print("Command executed successfully")
            time.sleep(1)
        
            print("Pushing...")
            if device.push():
                print("Command executed successfully")
            else:
                print("Error sending command")
            
        else:
            print("Error sending command")
        
    else:
        print("Error sending command")
    
else:
    print("Could't get battery status")
'''