# pyMagicSwitchbot


This is a Python library that allows the integration of MagicSwitchbot devices in open source projects like home automation.

## Product description

The [MagicSwitchbot device](https://www.interear.com/smart-products/magic-bluetooth-switchbot.html) is a clone of the Switchbot manufactured by the chinese company *Shenzhen Interear Intelligent Technology Co., Ltd*.

<img src="img/render.jpg" alt="Rendered product image" style="zoom:50%;" />

<img src="img/box.jpg" alt="Outer box" style="zoom:50%;" />

If we open the device (which is easy just lifting a lid), we can see the device uses a [**CC2541**](https://www.ti.com/product/CC2541) chip, manufactured by Texas Instruments.

This is the board overview we see when opening the lid:

![Board Overview](img/board.jpg)

## Device API and protocol

The device uses a propietary BLE (Bluetooth Low Energy) protocol that I documented based on information provided by the company and reverse engineering of the logs and the App.

The documentation is published [here](doc/MagicSwitchBot_API.md).

## References

The library is based on bluepy, so it does not work on Windows.

The code is strongly influenced by [pySwitchbot](https://github.com/Danielhiversen/pySwitchbot) library by [Daniel Hjelseth Høyer (Danielhiversen)](https://github.com/Danielhiversen). My original idea was to modify this library and make it work for both devices families, but the internal working mode is quite different and most of the code was going to be different, so I decided to start a new project but using some of his good techniques and code.

## Library definition



