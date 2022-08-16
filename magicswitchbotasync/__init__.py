import asyncio, logging
import bleak
from bleak_retry_connector import BleakClient, establish_connection


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


class MagicSwitchbotDevice: 
    """Base Representation of a MagicSwitchbot Device."""

    """Constants definition for BLE communication"""    
    UUID_SERVICE = "0000fee7-0000-1000-8000-00805f9b34fb"
    UUID_USERWRITE_CHAR = "000036f5-0000-1000-8000-00805f9b34fb"
    UUID_USERREAD_CHAR = "000036f6-0000-1000-8000-00805f9b34fb"
    UUID_NOTIFY_SET = "00002902-0000-1000-8000-00805f9b34fb"
    
    """Symmetric encryption key used for AES"""
    CRYPT_KEY = [42, 97, 57, 92, 64, 85, 73, 81, 58, 90, 75, 98, 27, 109, 55, 53]
    
    """Protocol commands definition"""
    CMD_ENNOTIF = "0100"
    CMD_GETBAT = "0201"
    CMD_OTA = "0301"
    CMD_SWITCH = "0501"
    CMD_MODIFYPWD = "0504"
    CMD_TIMEDSWITCH = "0508"
    CMD_GETTOKEN = "0601"
    
    COMMANDS = {
        CMD_ENNOTIF: "CMD_ENNOTIF",
        CMD_GETBAT: "CMD_GETBAT",
        CMD_OTA: "CMD_OTA",
        CMD_SWITCH: "CMD_SWITCH",
        CMD_MODIFYPWD: "CMD_MODIFYPWD",
        CMD_TIMEDSWITCH: "CMD_TIMEDSWITCH",
        CMD_GETTOKEN: "CMD_GETTOKEN"
    }
    
    """Protocol parameters definition"""
    PAR_SWITCHON = "01"
    PAR_SWITCHOFF = "00"
    PAR_SWITCHPUSH = "02"
    PAR_OTA = "01"
    
    """Protocol response return code definition"""
    RC_GETBAT = "02"
    RC_SWITCH = "02"
    RC_MODIFYPWD = "05"
    RC_TIMEDSWITCH = "09"
    RC_TOKENOK = "02"
    RC_TOKENERR = "03"
    
    """Protocol response status definition"""
    STA_OK = "00"
    STA_ERR = "01"
    
    def __init__(self, mac, retry_count=DEFAULT_RETRY_COUNT, password=None, interface='hci0', connect_timeout=DEFAULT_CONNECT_TIMEOUT, disconnect_timeout=NO_TIMEOUT) -> None:
        """Creates a new instance to control the device
        
        Parameters
        ----------
            mac : str
                MAC address of the device
            retry_count : int
                Number of retries if the connection does not succed
            password : string
                Password or PIN set on the device
            interface : int
                Number of the bluetooth client interface to use. It will be prefixed by 'hci'. Default: hci0
            connect_timeout : int
                Timeout in seconds for every connection. Default: 3 seconds
        
        """
        self._interface = interface
        self._mac = mac
        self._btclient = None
        self._service = None
        self._userReadChar = None
        self._userWriteChar = None
        self._cccdDescriptor = None
        self._retry_count = retry_count
        self._password = password
        self._token = None
        self._battery = None
        self._delegate = None
        self._connectTimeout = connect_timeout
        self._disconnectTimeout = disconnect_timeout
        self._timer = None
        
    async def _connect(self, connect_timeout=DEFAULT_CONNECT_TIMEOUT, disconnect_timeout=NO_TIMEOUT, retries=1) -> bool:
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
        
        """Don't try to reconnect if we are connected already"""
        if self._is_connected():
            return True
        
        connected = False
        if disconnect_timeout != NO_TIMEOUT:
            self._disconnectTimeout = disconnect_timeout
        partial_connect = False
        
        for i in range(retries): 
            _LOGGER.debug("MagicSwitchbot[%s] Connecting using hci%d with %d seconds timeout (%d of %d retries)...", self._mac, self._interface, connect_timeout, (i + 1), retries)
            
            self._btclient = BleakClient(self._mac, device=self._interface)
            try:
                await self._btclient.connect(connect_timeout)
                partial_connect = True
                _LOGGER.info("MagicSwitchbot[%s] Connected with %s.", self._mac, self._interface)
                
                '''Initialize service and characteristics handles to the device'''
                self._userReadChar = await self._btclient.read_gatt_char(self.UUID_USERREAD_CHAR)
                self._cccdDescriptor = await self._btclient.read_gatt_descriptor(self.UUID_NOTIFY_SET)
                self._userWriteChar = await self._btclient.read_gatt_char(self.UUID_USERWRITE_CHAR)
    
                '''Once we connected, let's enable the response notifications'''
                await self._enableNotifications()
                
                connected = True
                
                self._scheduleDisconnection()
            except Exception as e:
                if partial_connect:
                    _LOGGER.error("MagicSwitchbot[%s] Incomplete connection to device (%s)", self._mac, str(e))
                else:
                    _LOGGER.error("MagicSwitchbot[%s] Couldn't connect to device (%s)", self._mac, str(e))
                self._btclient = None
                
            if connected:
                return True
            elif i < retries - 1:
                _LOGGER.debug("MagicSwitchbot[%s] Retrying in %d seconds...", self._mac, DEFAULT_RETRY_TIMEOUT)
                await asyncio.sleep(DEFAULT_RETRY_TIMEOUT)
        
        return connected
    
    async def _getNotification(self, sender, data):
        print("{0}: {1}".format(sender, data))
    
    async def _enableNotifications(self) -> None:
        """Enable read notifications
        
        We establish how we receive the notifications from the device
        """
        await self._btclient.start_notify(self.UUID_NOTIFY_SET, self._getNotification)
        
    async def _disconnect(self, scheduled=False) -> None:
        """Discconnects from the device"""
        
        self._timer = None
        _LOGGER.debug("MagicSwitchbot[%s] Disconnecting%s", self._mac, " on scheduled time" if scheduled else "")
        if not self._is_connected():
            self._btclient = None
            _LOGGER.debug("MagicSwitchbot[%s] The device was not connected", self._mac)
            return
        
        try:
            await self._btclient.disconnect()
            _LOGGER.info("MagicSwitchbot[%s] Client disconnected", self._mac)
            self._token = None
        except Exception as e:
            _LOGGER.warning("MagicSwitchbot[%s] Error disconnecting: %s", self._mac, str(e))
        finally:
            self._btclient = None

    def _is_connected(self) -> bool:
        """Checks if the device is connected
        
        Return
        ------
            bool
                Returns True if the device is still connected
        """
        
        if self._btclient is not None:
            connected = self._btclient.is_connected
        else:
            connected = False
            
        _LOGGER.debug("MagicSwitchbot[%s] Connected state: %s", self._mac, "True" if connected else "False")
        
        return connected