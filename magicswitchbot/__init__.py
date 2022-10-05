"""
Library to control MagicSwitchbot devices using BLEAK

@author: ec-blaster
@since: September 2022
@license: MIT 
"""

import asyncio, logging
import bleak
from bleak_retry_connector import BleakClient, establish_connection
from typing import Any

from .consts import *
from .device import MagicSwitchbotDevice
from .discovery import parse_advertisement_data
from .models import MagicSwitchbotAdvertisement

_LOGGER = logging.getLogger(__name__)

class MagicSwitchbot(MagicSwitchbotDevice):
    """Representation of a MagicSwitchbot."""
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """MagicSwitchbot constructor."""
        super().__init__(*args, **kwargs)

    async def update(self, interface: int | None=None) -> None:
        """Update mode, battery percent and state of device."""
        await self.get_device_data(retry=self._retry_count, interface=interface)

    async def turn_on(self) -> bool:
        """Turns the device on."""
        result = await self._sendCommand(CMD_SWITCH, PAR_SWITCHON, self._retry_count)
        
        if result:
          self._override_adv_data = {"isOn": True}
          
        _LOGGER.debug(
            "MagicSwitchbot[%s]: Turn on result: %s -> %s", self._device.address, result, self._override_adv_data
        )
        self._fire_callbacks()
        return result

    async def turn_off(self) -> bool:
        """Turns the device off."""
        result = await self._sendCommand(CMD_SWITCH, PAR_SWITCHOFF, self._retry_count)
        
        if result:
          self._override_adv_data = {"isOn": False}
          
        _LOGGER.debug(
            "MagicSwitchbot[%s]: Turn off result: %s -> %s", self._device.address, result, self._override_adv_data
        )
        self._fire_callbacks()
        return result
      
    async def push(self) -> bool:
        """Just pushes a button"""
        result = await self._sendCommand(CMD_SWITCH, PAR_SWITCHPUSH, self._retry_count)
        
        _LOGGER.debug(
            "MagicSwitchbot[%s]: Push result: %s", self._device.address, result
        )
        self._fire_callbacks()
        return result
      
    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        ok = await self._sendCommand(CMD_GETBAT, "01", self._retry_count)
        
        if not ok:
            return None
        return {
            "battery": self._battery,
            "firmware": f"{self._ver_major}.{self._ver_minor}",
            "chip_type": self._chip_type,
            "device_type": self._dev_type,
            "password_enabled": self._en_pwd
        }
        
    async def get_battery(self) -> int | None:
        """Gets the device's battery level
        Return
            int
                Level of the device's battery, from 0 to 100
        """
        ok = await self._sendCommand(CMD_GETBAT, "01", self._retry_count)
        if ok:
            return self._battery
        else:
            return None

    def is_on(self) -> bool | None:
        """Return switch's latest state"""
        value = self._get_adv_value("isOn")
        if value is None:
            return None
        return value
    
    '''
    def connect(self, connect_timeout=DEFAULT_CONNECT_TIMEOUT, disconnect_timeout=NO_TIMEOUT) -> bool:
        """Connects to the device
        
        This method allows us to connect to the Magic Switchbot device
        
        Params
        ------
            connect_timeout : int (Optional)
                Specifies the amount of time (seconds) we'll be waiting for the bluetooth device
                to connect. If it doesn't connect on time, it returns False
            disconnect_timeout : int (Optional)
                Specifies the amount of time (seconds) that will be scheduled to automatically
                disconnect from the device. If it's not specified, the client does not disconnect
                until the object is disposed from memory
        Returns
        -------
            bool
                Returns True on successful connection
        """
        return self._connect(connect_timeout, disconnect_timeout)
    
    def auth(self) -> bool:
        """Validates the password set on the device
        
        Validate the password set on the device and gets the communication token.
        The password we use is set on construct

        Returns
        -------
            bool
                Returns true if password is correct
        """
        return self._auth()
    
    def disconnect(self) -> None:
        """Disconnects from the device"""
        return self._disconnect()
    
    def is_connected(self) -> bool:
        """Checks if the device is connected
        
        Return
        ------
            bool
                Returns True if the device is still connected
        """
        return self._is_connected()
        
    def turn_on(self) -> bool:
        """Turns the device on."""
        return self._sendCommand(self.CMD_SWITCH, self.PAR_SWITCHON, self._retry_count)

    def turn_off(self) -> bool:
        """Turns the device off."""
        return self._sendCommand(self.CMD_SWITCH, self.PAR_SWITCHOFF, self._retry_count)
      
    def push(self) -> bool:
        """Just pushes a button"""
        return self._sendCommand(self.CMD_SWITCH, self.PAR_SWITCHPUSH, self._retry_count)

    def get_battery(self) -> int:
        """Gets the device's battery level
        Return
            int
                Level of the device's battery, from 0 to 100
        """
        ok = self._sendCommand(self.CMD_GETBAT, "01", self._retry_count)
        if ok:
            return self._battery
        else:
            return None
    '''
