# pyMagicSwitchbot


This is a Python library that allows the integration of *Magic Switchbot* devices in open source projects like home automation.

## Product description

The [Magic Switchbot device](https://www.interear.com/smart-products/magic-bluetooth-switchbot.html) is apparently a clone of the *Switchbot* manufactured by the Chinese company *Shenzhen Interear Intelligent Technology Co., Ltd*.

<img src="img/render.jpg" alt="Rendered product image" style="zoom:50%;" />

<img src="img/box.jpg" alt="Outer box" style="zoom:50%;" />

If we open the device (which is easy just lifting a lid), we can see it is based upon a low power and high performance [**CC2541**](https://www.ti.com/product/CC2541) SOC chip, manufactured by Texas Instruments. It is compatible with BLE (Bluetooth Low Energy) 4.0.

This is the board overview we see when opening the lid:

![Board Overview](img/board.jpg)

The device has an internal 360mAh LiPo battery that can be recharged via its MicroUSB connector and according to the manufacturer its charge can last up to 2 or 3 months.

The device has 2 different working modes:

* **Switch**.
  In this mode, you can *turn on* or *turn off* a device. For this mode to work, the manufacturer provides an extension "hook" that can be attached to the physical switch you want to activate, so that when you *turn off* it effectively *pulls* the hook. You can watch a video tutorial [in this link](https://cloud.video.alibaba.com/play/u/2153292369/p/1/e/6/t/1/d/hd/278038162598.mp4).

* **Push button**.

  In this mode, the device simply *pushes* the object to which it is attached for a second and then retracts to its original position every time you activate it.



## Device API and protocol

The device uses a *propietary* BLE protocol that I documented based on information provided by the manufacturer and some reverse engineering of the bluetooth logs and the original [Android App](https://play.google.com/store/apps/details?id=com.runChina.moLiKaiGuan&hl=es&gl=US).

The documentation is published [here](doc/MagicSwitchBot_API.md).

## References

The library is based on `bluepy`, so it does not work on Windows.

The code is strongly influenced by [pySwitchbot](https://github.com/Danielhiversen/pySwitchbot) library by [Daniel Hjelseth Høyer (Danielhiversen)](https://github.com/Danielhiversen). My original idea was to modify this library and make it work for both devices families, but the internal working mode is quite different and most of the code was going to be different, so I decided to start a new project but using some of his good techniques and code.

## Important Note

IMPORTANT: hcitool and python are not allowed to access bluetooth stack in LInux unless the user is root.
To solve it (insecure), you must run these commands if you don' t have the privileges:          

```bash
sudo apt-get install libcap2-bin
sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
sudo setcap 'cap_net_raw+ep' $(readlink -f $(which hcitool))
```
## Using the library

You need Python 3.5 or newer to use the library, and it is published to PyPi. So to use it just fetch it:

```bash
pip install magicswithbot
```

From your program just import the library or only the main class:

```python
import magicswithbot

--OR--

from magicswitchbot import MagicSwitchbot
```

### Constructor

The library uses a main class called `MagicSwitchbot`. The constructor gets the device's MAC address as a parameter:

`MagicSwitchbot(mac, retry_count=0, password=None, interface=None)`

##### Parameters:
* mac : str
  MAC address of the device
* retry_count : int
  Number of retries if the connection does not succed
* password : string
  Password or PIN set on the device
* interface : int
  Number of the bluetooth client interface to use. It will be prefixed by 'hci'. Default: hci0

### Methods

In addition to the constructor, the main class has the following public methods:

* `connect(timeout=-1) ‑> NoneType`
Connects to the device
  
  This method allows us to connect to the Magic Switchbot device.
  
  #### Parameters:
  
  * timeout : int
    Specifies the amount of time (seconds) that will be scheduled to automatically disconnect from the device. If it's not specified, the client does not disconnect until the object is disposed from memory.
* `disconnect()`

  Manual disconnect.
* `auth(password) ‑> bool`
Validation of the password.
  
  This method allows us to validate the password and gets the current token..
  
  #### Parameters:
  
  * password : str
    Current device password or empty (or None) if no password is set.
  
  Returns bool: Returns True if password is correct.
  
* `is_connected() ‑> bool`

  Checks if the device is connected.

  Returns bool: Returns True if the device is still connected
* `turn_on() ‑> bool`
  Use the device just to switch something on.
* `turn_off() ‑> bool`
  Use the device just to switch something off.

* `push() ‑> bool`
  Use the device just to push a button.

* `get_battery() ‑> int`

  Gets the device's battery level

  Returns int: Level of the device's battery, from 0 to 100

## Example code

The following example shows how to use the library in your Python program:

```python
from magicswitchbot import MagicSwitchbot
import time, logging

logging.basicConfig(level=logging.INFO)

MAC = "00:11:22:33:44:55"

device = MagicSwitchbot(mac=MAC)

device.connect(30)

res = device.get_battery()
print(f"Connected to device {MAC} with {res}% of battery remaining")

time.sleep(1)

device.turn_on()

time.sleep(1)

device.turn_off()

time.sleep(1)

device.push()

```

