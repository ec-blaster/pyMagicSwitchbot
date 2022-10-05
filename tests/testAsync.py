'''
Testing MagicSwitchBot devices library

IMPORTANT: hcitool and python is not allowed to access bluetooth stack unless the user is root
          To solve it (unsecure):
          
            sudo apt-get install libcap2-bin
            sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
            sudo setcap 'cap_net_raw+ep' $(readlink -f $(which hcitool))
'''

import sys
sys.path.append("..")
from magicswitchbot import MagicSwitchbot
import logging, asyncio
from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice

logging.basicConfig(level=logging.DEBUG)

MAC = "00:11:22:33:44:55"
MAC = "fc:45:c3:75:c9:ae"
PASSWORD = None


async def explore_device(device: BLEDevice) -> None:
  client = BleakClient(device)
  try:
    await client.connect()
    for service in client.services:
      print(f"[Service] {service}")
      for char in service.characteristics:
        if "read" in char.properties:
          try:
            value = bytes(await client.read_gatt_char(char.uuid))
            print(
                f"\t[Characteristic] {char} ({','.join(char.properties)}), Value: {value}"
            )
          except Exception as e:
            print(
                f"\t[Characteristic] {char} ({','.join(char.properties)}), Value: {e}"
            )
  
        else:
          value = None
          print(
              f"\t[Characteristic] {char} ({','.join(char.properties)}), Value: {value}"
          )
  
        for descriptor in char.descriptors:
          try:
            value = bytes(
                await client.read_gatt_descriptor(descriptor.handle)
            )
            print(f"\t\t[Descriptor] {descriptor}) | Value: {value}")
          except Exception as e:
            print(f"\t\t[Descriptor] {descriptor}) | Value: {e}")
  except:
    await client.disconnect()


async def main():
  try:
    print(f"Connecting to MagicSwitchbot device at {MAC}...")
    
    ble_device = await BleakScanner.find_device_by_address(MAC, timeout=20)
    
    # await explore_device(ble_device)
    
    if not ble_device:
      print(f"Couldn't find a BLE device with address {MAC}")
    else:
      device = MagicSwitchbot(ble_device)
      
      print ("Device information:")
      print (await device.get_basic_info())

      res = await device.get_battery()
      if res:
          print(f"Connected to MagicSwitchbot device at {MAC} with {res}% of battery remaining")      

          print("Turning on...")
          ok = await device.turn_on()
          
          if ok:
              print("Command executed successfully")
                      
              print("Turning off...")
              ok = await device.turn_off()
              if ok:
                  print("Command executed successfully")
              
                  print("Pushing...")
                  if await device.push():
                      print("Command executed successfully")
                  else:
                      print("Error sending command")
              else:
                  print("Error sending command")
          else:
              print("Error sending command")
      
  except Exception as e:
    print(e)
    
  finally:
    print("Testing finished")

    
asyncio.run(main())
