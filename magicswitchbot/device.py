import asyncio
import logging
import random
import binascii
from typing import Any, Callable
from binascii import hexlify
from Crypto.Cipher import AES

import async_timeout
from bleak import BleakError
from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTCharacteristic, BleakGATTServiceCollection
from bleak.exc import BleakDBusError
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    BleakNotFoundError,
    ble_device_has_changed,
    establish_connection,
)

from .models import MagicSwitchbotAdvertisement
# from .consts import *
from .consts import (DEFAULT_SCAN_TIMEOUT,
    DEFAULT_RETRY_COUNT,
    DISCONNECT_DELAY,
    NOTIFY_TIMEOUT,
    CRYPT_KEY,
    COMMANDS,
    CMD_GETTOKEN,
    CMD_GETBAT,
    CMD_SWITCH,
    RC_TOKENOK,
    RC_GETBAT,
    RC_SWITCH,
    STA_OK,
    UUID_USERREAD_CHAR,
    UUID_USERWRITE_CHAR)
from .discovery import GetMagicSwitchbotDevices

_LOGGER = logging.getLogger(__name__)

BLEAK_EXCEPTIONS = (AttributeError, BleakError, asyncio.exceptions.TimeoutError)

    
class CharacteristicMissingError(Exception):
    """Custom exception raised when a characteristic is missing."""

    
class MagicSwitchbotOperationError(Exception):
    """Custom exception raised when an operation fails."""


class MagicSwitchbotDevice:
    """Base representation of a MagicSwitchbot device."""

    def __init__(
        self,
        device: BLEDevice,
        password: str | None=None,
        interface: int=0,
        **kwargs: Any,
    ) -> None:
        """MagicSwitchbot base class constructor."""
        self._interface = f"hci{interface}"
        self._device = device
        self._sb_adv_data: MagicSwitchbotAdvertisement | None = None
        self._override_adv_data: dict[str, Any] | None = None
        self._scan_timeout: int = kwargs.pop("scan_timeout", DEFAULT_SCAN_TIMEOUT)
        self._retry_count: int = kwargs.pop("retry_count", DEFAULT_RETRY_COUNT)
        self._connect_lock = asyncio.Lock()
        self._operation_lock = asyncio.Lock()
        if password is None or password == "":
            self._password_encoded = ""
        else:
            self._password_encoded = self._passwordToHex(password)
        self._client: BleakClientWithServiceCache | None = None
        self._read_char: BleakGATTCharacteristic | None = None
        self._write_char: BleakGATTCharacteristic | None = None
        self._disconnect_timer: asyncio.TimerHandle | None = None
        self._expected_disconnect = False
        self.loop = asyncio.get_event_loop()
        self._callbacks: list[Callable[[], None]] = []
        self._token = None
        self._chip_type = None
        self._ver_major = None
        self._ver_minor = None
        self._dev_type = None
        self._en_pwd = False if password is None else True
        self._notify_future: asyncio.Future[bytearray] | None = None
      
    async def _sendCommand(self, command: str, parameter: str, retries: int | None=None) -> bool | None:
        """Sends a command to the device and waits for its response
        
        This method sends a command to the device via BLE, waiting and processing an execution response
        
        Parameters
        ----------
            command: str
                Hexadecimal string with 2 bytes for the command (and subcommand) to execute
            parameter: str
                Hexadecimal string with 1 or more bytes as a parameter to the command
            retries : int
                Number of times that the connection will be retried in case of error

        Returns
        -------
            bool
                Returns True if the command executed succesfully
        """
        if retries is None:
            retries = self._retry_count
        
        _LOGGER.debug("MagicSwitchbot[%s]: Sending command %s with parameter %s and %d retries", self._device.address, command, parameter, retries)
        
        '''First of all we check if there is a token to retrieve'''
        if command != CMD_GETTOKEN and self._token is None:
            '''If the command is NOT CMD_GETTOKEN, we'll issue a CMD_GETTOKEN before sending the actual command'''
            _LOGGER.debug("MagicSwitchbot[%s]: The device hasn't got a token yet. Let's get one...")
            go = await self._auth()
        else:
            if self._token:
              _LOGGER.debug("MagicSwitchbot[%s]: We've got a token. Go on...", self._device.address)
            go = True
            
        if go:
          if self._operation_lock.locked():
              _LOGGER.debug(
                  "MagicSwitchbot[%s]: Operation already in progress, waiting for it to complete; RSSI: %s",
                  self._device.address,
                  self.rssi,
              )
  
          max_attempts = retries
          if self._operation_lock.locked():
              _LOGGER.debug(
                  "MagicSwitchbot[%s]: Operation already in progress, waiting for it to complete; RSSI: %s",
                  self._device.address,
                  self.rssi,
              )
          async with self._operation_lock:
              for attempt in range(max_attempts):
                  try:
                      _LOGGER.debug("MagicSwitchbot[%s]: - Attempt #%d -", self._device.address, attempt + 1)
                      encrypted_command = self._prepareCommand(command, parameter)
                      return await self._send_command_locked(encrypted_command)
                  except BleakNotFoundError:
                      _LOGGER.error(
                          "MagicSwitchbot[%s]: device not found, no longer in range, or poor RSSI: %s",
                          self.name,
                          self.rssi,
                          exc_info=True,
                      )
                      return None
                  except CharacteristicMissingError as ex:
                      if attempt == retries:
                          _LOGGER.error(
                              "MagicSwitchbot[%s]: characteristic missing: %s; Stopping trying; RSSI: %s",
                              self.name,
                              ex,
                              self.rssi,
                              exc_info=True,
                          )
                          return None
  
                      _LOGGER.debug(
                          "MagicSwitchbot[%s]: characteristic missing: %s; RSSI: %s",
                          self.name,
                          ex,
                          self.rssi,
                          exc_info=True,
                      )
                  except BLEAK_EXCEPTIONS:
                      if attempt == retries:
                          _LOGGER.error(
                              "MagicSwitchbot[%s]: communication failed; Stopping trying; RSSI: %s",
                              self.name,
                              self.rssi,
                              exc_info=True,
                          )
                          return None
  
                      _LOGGER.debug(
                          "MagicSwitchbot[%s]: communication failed with:", self._device.address, exc_info=True
                      )

          raise RuntimeError("Unreachable")

    @property
    def name(self) -> str:
        """Returns the device name."""
        return f"{self._device.name} ({self._device.address})"

    @property
    def rssi(self) -> int:
        """Returns the RSSI of the device."""
        return self._get_adv_value("rssi")

    async def _ensure_connected(self):
        """Ensure connection to the device is established."""
        if self._connect_lock.locked():
            _LOGGER.debug(
                "MagicSwitchbot[%s]: Connection already in progress, waiting for it to complete; RSSI: %s",
                self.name,
                self.rssi,
            )
        if self._client and self._client.is_connected:
            self._reset_disconnect_timer()
            return
        async with self._connect_lock:
            # Check again while holding the lock
            if self._client and self._client.is_connected:
                self._reset_disconnect_timer()
                return
            _LOGGER.debug("MagicSwitchbot[%s]: Connecting; RSSI: %s", self._device.address, self.rssi)
            client = await establish_connection(
                BleakClientWithServiceCache,
                self._device,
                self.name,
                self._disconnected,
                use_services_cache=True,
                ble_device_callback=lambda: self._device
            )
            _LOGGER.debug("MagicSwitchbot[%s]: Connected; RSSI: %s", self._device.address, self.rssi)
            resolved = self._resolve_characteristics(client.services)
            if not resolved:
                # Try to handle services failing to load
                resolved = self._resolve_characteristics(await client.get_services())
            self._cached_services = client.services if resolved else None
            self._client = client
            self._reset_disconnect_timer()
            await self._start_notify()

    def _resolve_characteristics(self, services: BleakGATTServiceCollection) -> bool:
        """Initialize characteristics handles to the device"""
        self._read_char = services.get_characteristic(UUID_USERREAD_CHAR)
        self._write_char = services.get_characteristic(UUID_USERWRITE_CHAR)
        return bool(self._read_char and self._write_char)

    def _reset_disconnect_timer(self):
        """Reset disconnect timer."""
        if self._disconnect_timer:
            self._disconnect_timer.cancel()
        self._expected_disconnect = False
        self._disconnect_timer = self.loop.call_later(
            DISCONNECT_DELAY, self._disconnect
        )

    def _disconnected(self, client: BleakClientWithServiceCache) -> None:
        """Disconnected callback."""
        if self._expected_disconnect:
            _LOGGER.debug(
                "MagicSwitchbot[%s]: Disconnected from device; RSSI: %s", self._device.address, self.rssi
            )
            return
        _LOGGER.warning(
            "MagicSwitchbot[%s]: Device unexpectedly disconnected; RSSI: %s",
            self.name,
            self.rssi,
        )

    def _disconnect(self):
        """Disconnects from the device."""
        self._disconnect_timer = None
        asyncio.create_task(self._execute_timed_disconnect())

    async def _execute_timed_disconnect(self):
        """Execute timed disconnection."""
        _LOGGER.debug(
            "MagicSwitchbot[%s]: Disconnecting after timeout of %s",
            self.name,
            DISCONNECT_DELAY,
        )
        await self._execute_disconnect()

    async def _execute_disconnect(self):
        """Execute disconnection."""
        async with self._connect_lock:
            client = self._client
            self._expected_disconnect = True
            self._client = None
            self._read_char = None
            self._write_char = None
            self._token = None
            if client and client.is_connected:
                await client.disconnect()

    async def _send_command_locked(self, command: bytes) -> bool:
        """Sends an encrypted command to the device and reads the response."""
        await self._ensure_connected()
        try:
            return await self._execute_command_locked(command)
        except BleakDBusError as ex:
            # Disconnect so we can reset state and try again
            await asyncio.sleep(0.25)
            _LOGGER.debug(
                "MagicSwitchbot[%s]: RSSI: %s; Backing off %ss; Disconnecting due to error: %s",
                self.name,
                self.rssi,
                0.25,
                ex,
            )
            await self._execute_disconnect()
            raise
        except BleakError as ex:
            # Disconnect so we can reset state and try again
            _LOGGER.debug(
                "MagicSwitchbot[%s]: RSSI: %s; Disconnecting due to error: %s", self._device.address, self.rssi, ex
            )
            await self._execute_disconnect()
            raise

    def _notification_handler(self, _sender: int, data: bytearray) -> None:
        """Internal routine to handle BLE notification responses."""
        _LOGGER.info("MagicSwitchbot[%s] Notification received. Data: %s", self._device.address, data)
        
        if self._notify_future and not self._notify_future.done():
            self._notify_future.set_result(data)
            return
        _LOGGER.debug("MagicSwitchbot[%s]: The notification was not from our device", self._device.address)

    async def _start_notify(self) -> None:
        """Start notification."""
        _LOGGER.debug("MagicSwitchbot[%s]: Subscribe to notifications; RSSI: %s", self._device.address, self.rssi)
        await self._client.start_notify(self._read_char, self._notification_handler)
        
    async def _execute_command_locked(self, command: bytes) -> bool:
        """Executes the command and reads the response."""
        assert self._client is not None
        if not self._read_char:
            raise CharacteristicMissingError(UUID_USERREAD_CHAR)
        if not self._write_char:
            raise CharacteristicMissingError(UUID_USERWRITE_CHAR)
        self._notify_future = asyncio.Future()
        client = self._client
        
        _LOGGER.debug("MagicSwitchbot[%s]: Sending command: %s", self._device.address, command)
        await client.write_gatt_char(self._write_char, binascii.a2b_hex(command), True)

        _LOGGER.debug("MagicSwitchbot[%s]: Waiting for notifications...", self._device.address)

        async with async_timeout.timeout(NOTIFY_TIMEOUT):
            notify_msg = await self._notify_future
        _LOGGER.debug("MagicSwitchbot[%s]: Notification received: %s", self._device.address, notify_msg)
        self._notify_future = None

#        '''This sleep is important. Otherwise, it will freeze on next start_notify'''
#        await asyncio.sleep(0.25)
        
        plain_response = self._decrypt(notify_msg.hex())
        _LOGGER.debug("MagicSwitchbot[%s] Unencrypted result: %s", self._device.address, plain_response)
        return await self._processResponse(plain_response)

    def get_address(self) -> str:
        """Returns the address of the device."""
        return self._device.address

    def _get_adv_value(self, key: str) -> Any:
        """Returns a value from the advertisement data."""
        if self._override_adv_data and key in self._override_adv_data:
            _LOGGER.debug(
                "MagicSwitchbot[%s]: Using override value for %s: %s",
                self.name,
                key,
                self._override_adv_data[key],
            )
            return self._override_adv_data[key]
        if not self._sb_adv_data:
            return None
        return self._sb_adv_data.data["data"].get(key)

    def get_battery_percent(self) -> Any:
        """Returns the device battery level in percent."""
        return self._get_adv_value("battery")

    def update_from_advertisement(self, advertisement: MagicSwitchbotAdvertisement) -> None:
        """Updates the device data from advertisement."""
        # Only accept advertisements if the data is not missing
        # if we already have an advertisement with data
        # if self._device and ble_device_has_changed(self._device, advertisement.device):
        #    self._cached_services = None
        self._sb_adv_data = advertisement
        self._device = advertisement.device

    async def get_device_data(
        self, retry: int | None=None, interface: int | None=None
    ) -> MagicSwitchbotAdvertisement | None:
        """Finds MagicSwitchbot devices and their advertisement data."""
        if retry is None:
            retry = self._retry_count

        if interface:
            _interface: int = interface
        else:
            _interface = int(self._interface.replace("hci", ""))

        _data = await GetMagicSwitchbotDevices(interface=_interface).discover(
            retry=retry, scan_timeout=self._scan_timeout
        )

        if self._device.address in _data:
            self._sb_adv_data = _data[self._device.address]

        return self._sb_adv_data

    def _fire_callbacks(self) -> None:
        """Fire callbacks."""
        _LOGGER.debug("MagicSwitchbot[%s]: Fire callbacks", self._device.address)
        for callback in self._callbacks:
            callback()

    def subscribe(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Subscribes to the device notifications."""
        self._callbacks.append(callback)

        def _unsub() -> None:
            """Unsubscribe from device notifications."""
            self._callbacks.remove(callback)

        return _unsub

    async def update(self) -> None:
        """Update state of device."""

    def _set_advertisement_data(self, advertisement: MagicSwitchbotAdvertisement) -> None:
        """Set advertisement data."""
        if advertisement.data.get("data") or not self._sb_adv_data.data.get("data"):
            self._sb_adv_data = advertisement
        self._override_adv_data = None

    def switch_mode(self) -> bool | None:
        """Return true or false from cache."""
        # To get actual position call update() first.
        return self._get_adv_value("switchMode")
      
    async def _auth(self) -> bool:
        """Validates the password set on the device
        
        Validates the password set on the device and gets the communication token.
        The password we use is set on construct

        Returns
        -------
            bool
                Returns true if password is correct
        """
        '''The parameter that CMD_GETTOKEN expects is the encoded passwor or empty if not set''' 
        return await self._sendCommand(CMD_GETTOKEN, self._password_encoded)

    def _passwordToHex(self, password):
        """Converts password to Hex
        
        Converts the supplied password to an hexadecimal string
        
        Parameters
        ----------
            password : str
                Plain text password
                
        Return
        ------
            str
                Password encoded in hexadecimal
        """
        return hexlify(password.encode()).decode()
      
    def _encrypt(self, data) -> str:
        """Encrypts data using AES128 ECB
        Parameters
        ----------
            data : str
                Hexadecimal representation of the data to encrypt

        Returns
        -------
            str
                Hexadecimal representation of encrypted data
        """
        cipher = AES.new(bytes(bytearray(CRYPT_KEY)), AES.MODE_ECB)
        encrypted = cipher.encrypt(bytes.fromhex(data)).hex()
        return encrypted
      
    def _decrypt(self, data) -> str:
        """Decrypts data using AES128 ECB
        Parameters
        ----------
            data : str
                Hexadecimal representation of the data to decrypt

        Returns
        -------
            str
                Hexadecimal representation of decrypted data
        """
        
        '''We need a byte string as the key to decrypt or encrypt'''
        decipher = AES.new(bytes(bytearray(CRYPT_KEY)), AES.MODE_ECB)
        return decipher.decrypt(bytes.fromhex(data)).hex()
    
    def _prepareCommand(self, command, parameter):
        """Prepare the command to send to the device
        
        Prepares an encrypted string based on a command and a parameter to send to the MagicSwitchBot device
        
        Parameters
        ----------
            command : str
                Hexadecimal representation of the command to send (usually 2 hex bytes, len 4)
            parameter: str
                Hexadecimal representation of the parameter(s) to send (variable length)

        Returns
        -------
            str
                Hexadecimal representation of the 16 encrypted bytes to send to the device
        """
        
        '''Hex form of the parameter length:'''
        parmLen = "{:02X}".format(int(len(parameter) / 2))
        
        if self._token is None:
            tok = ""
        else:
            tok = self._token

        '''
        We calculate how long must be the random tail of the command.
        Each hex byte has a length of 2 characters, so the complete payload has 32 chars. The length byte also counts
        '''
        rndLen = 32 - len(command) - len(parameter) - len(tok) - 2
        rndTail = ''.join([str(y) for _ in range(rndLen) for y in random.choice('0123456789abcdef')])
        
        fullCommand = command + parmLen + parameter + tok + rndTail
        
        _LOGGER.info("MagicSwitchbot[%s] Sending %s command: %s", self._device.address, COMMANDS[command], fullCommand)

        return self._encrypt(fullCommand)

    async def _processResponse(self, response) -> bool:
        """Process the response from the device
      
        This method processes the response that we receive from the device after
        executing a command
      
        Parameters
        ----------
            response : str
                Hexadecimal representation of the 16 byte response
                
        Return
        ------
            bool
                Returns True if the command result is succesfull
        """
        success = False
        command = response[0:2]
        ret_code = response[2:4]
        param_length = int(response[4:6])
        param = response[6:(6 + 2 * param_length)]
      
        _LOGGER.info("MagicSwitchbot[%s] Response: (Command = %s, Return Code = %s, Length = %d, Params = %s)", self._device.address, command, ret_code, param_length, param)
      
        if command == CMD_GETTOKEN[0:2]:
            if ret_code == RC_TOKENOK:
                token = param[0:8]
                self._chip_type = param[8:10]
                self._ver_major = int(param[10:12])
                self._ver_minor = int(param[12:14])
                self._dev_type = param[14:16]
                self._en_pwd = "False" if param[16:18] == '00' else "True"
                self._token = token 
                _LOGGER.info("MagicSwitchbot[%s] The current connection token is %s", self._device.address, token)
                _LOGGER.info("MagicSwitchbot[%s] Chip type: %s, Firmware version: %d.%d, Device type: %s, Password enabled: %s",
                             self._device.address,
                             self._chip_type,
                             self._ver_major,
                             self._ver_minor,
                             self._dev_type,
                             self._en_pwd)
                success = True
            else:
                _LOGGER.error("MagicSwitchbot[%s] Error retrieving token. Please check password", self._device.address)
        elif command == CMD_GETBAT[0:2]:
            if ret_code == RC_GETBAT and param.upper() != "FF":
                self._battery = int("0x" + param, 16)
                _LOGGER.info("MagicSwitchbot[%s] Battery level: %d%%", self._device.address, self._battery)
                success = True
            else:
                self._battery = None
        elif command == CMD_SWITCH[0:2]:
            if ret_code == RC_SWITCH and param == STA_OK:
                # We get a little more for the mechanical arm to stop. Otherwise, the user could send
                # another command when it is moving yet, so the program would freeze
                await asyncio.sleep(2.25)
                _LOGGER.info("MagicSwitchbot[%s] Switch state changed successfully", self._device.address)
                success = True
            else:
                _LOGGER.error("MagicSwitchbot[%s] Error changing switch state", self._device.address)
                
        return success 
