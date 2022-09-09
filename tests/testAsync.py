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
from bleak import BleakScanner

logging.basicConfig(level=logging.DEBUG)

MAC = "00:11:22:33:44:55"
MAC = "fc:45:c3:75:c9:ae"
PASSWORD = None
MODEL_NBR_UUID = "00002a24-0000-1000-8000-00805f9b34fb"


async def main():
  try:
    print(f"Connecting to MagicSwitchbot device at {MAC}...")
    
    ble_device = await BleakScanner.find_device_by_address(MAC, timeout=20)
    
    if ble_device is not None:
      device = MagicSwitchbot(ble_device)
      
      print("Turning on...")
      await device.turn_on()
    else:
      print(f"No se ha podido encontrar un dispositivo con la mac {MAC}")
    
  except Exception as e:
    print(e)
    
  finally:
    print("Testing finished")

    
asyncio.run(main())
  
'''client = BleakClient(MAC, timeout=3)
  try:
    print(f"Connecting to MagicSwitchbot device at {MAC}...")
    #await client.connect()
    
    #print("Connection succesfull")
    di = client._device_info
    ble_device = BLEDevice(address=MAC,
                           name=di["Name"],
                           rssi=di["RSSI"],
                           details={
                             "path": di["Adapter"]
                           }
    )
    await client.disconnect()
    
    device = MagicSwitchbot(ble_device)
    
    
    

  




res = device.get_battery()
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
