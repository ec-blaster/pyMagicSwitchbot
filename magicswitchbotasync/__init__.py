import asyncio, logging
import bleak
from bleak_retry_connector import BleakClient, establish_connection
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
