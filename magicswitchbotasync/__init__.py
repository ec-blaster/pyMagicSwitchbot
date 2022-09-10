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

'''TODO: Move all these constants and merge with those at consts.py'''
'''How many times we will retry in case of error'''
DEFAULT_RETRY_COUNT = 3

'''How many seconds to wait between retries'''
DEFAULT_RETRY_TIMEOUT = 1

'''Max seconds to wait before the connection is established''' 
DEFAULT_CONNECT_TIMEOUT = 3

'''Max seconds to wait before the device sends back the response to a command'''
NOTIFY_TIMEOUT = 5

NO_TIMEOUT = -1

_LOGGER = logging.getLogger(__name__)


class MagicSwitchbot(MagicSwitchbotDevice):
    """Representation of a MagicSwitchbot."""
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """MagicSwitchbot constructor."""
        super().__init__(*args, **kwargs)

    async def update(self, interface: int | None = None) -> None:
        """Update mode, battery percent and state of device."""
        await self.get_device_data(retry=self._retry_count, interface=interface)

    async def turn_on(self) -> bool:
        """Turns the device on."""
        result = await self._sendCommand(CMD_SWITCH, PAR_SWITCHON, self._retry_count)
        ret = self._check_command_result(result, 0, {1, 5})
        self._override_adv_data = {"isOn": True}
        _LOGGER.debug(
            "%s: Turn on result: %s -> %s", self.name, result, self._override_adv_data
        )
        self._fire_callbacks()
        return True
    '''
    def turn_off(self) -> bool:
        """Turns the device off."""
        return self._sendCommand(self.CMD_SWITCH, self.PAR_SWITCHOFF, self._retry_count)
      
    def push(self) -> bool:
        """Just pushes a button"""
        return self._sendCommand(self.CMD_SWITCH, self.PAR_SWITCHPUSH, self._retry_count)
      
    '''  
      
      
    '''
    async def turn_off(self) -> bool:
        """Turns the device off."""
        result = await self._send_command(OFF_KEY)
        ret = self._check_command_result(result, 0, {1, 5})
        self._override_adv_data = {"isOn": False}
        _LOGGER.debug(
            "%s: Turn off result: %s -> %s", self.name, result, self._override_adv_data
        )
        self._fire_callbacks()
        return ret

    async def hand_up(self) -> bool:
        """Raise device arm."""
        result = await self._send_command(UP_KEY)
        return self._check_command_result(result, 0, {1, 5})

    async def hand_down(self) -> bool:
        """Lower device arm."""
        result = await self._send_command(DOWN_KEY)
        return self._check_command_result(result, 0, {1, 5})

    async def press(self) -> bool:
        """Press command to device."""
        result = await self._send_command(PRESS_KEY)
        return self._check_command_result(result, 0, {1, 5})

    async def set_switch_mode(
        self, switch_mode: bool = False, strength: int = 100, inverse: bool = False
    ) -> bool:
        """Change bot mode."""
        mode_key = format(switch_mode, "b") + format(inverse, "b")
        strength_key = f"{strength:0{2}x}"  # to hex with padding to double digit
        result = await self._send_command(DEVICE_SET_MODE_KEY + strength_key + mode_key)
        return self._check_command_result(result, 0, {1})

    async def set_long_press(self, duration: int = 0) -> bool:
        """Set bot long press duration."""
        duration_key = f"{duration:0{2}x}"  # to hex with padding to double digit
        result = await self._send_command(DEVICE_SET_EXTENDED_KEY + "08" + duration_key)
        return self._check_command_result(result, 0, {1})

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info()):
            return None
        return {
            "battery": _data[1],
            "firmware": _data[2] / 10.0,
            "strength": _data[3],
            "timers": _data[8],
            "switchMode": bool(_data[9] & 16),
            "inverseDirection": bool(_data[9] & 1),
            "holdSeconds": _data[10],
        }

    def is_on(self) -> bool | None:
        """Return switch state from cache."""
        # To get actual position call update() first.
        value = self._get_adv_value("isOn")
        if value is None:
            return None

        if self._inverse:
            return not value
        return value
    '''
    
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