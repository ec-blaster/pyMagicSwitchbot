import asyncio
import logging
from typing import Any, Callable
from uuid import UUID
from binascii import hexlify

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
from .const import (
  DEFAULT_RETRY_COUNT,
  DEFAULT_SCAN_TIMEOUT,
  DISCONNECT_DELAY,
  UUID_USERREAD_CHAR,
  UUID_USERWRITE_CHAR
)

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
            self._password_encoded = None
        else:
            self._password_encoded = self._passwordToHex(password)
        self._client: BleakClientWithServiceCache | None = None
        self._cached_services: BleakGATTServiceCollection | None = None
        self._read_char: BleakGATTCharacteristic | None = None
        self._write_char: BleakGATTCharacteristic | None = None
        self._disconnect_timer: asyncio.TimerHandle | None = None
        self._expected_disconnect = False
        self.loop = asyncio.get_event_loop()
        self._callbacks: list[Callable[[], None]] = []

    def _commandkey(self, key: str) -> str:
        """Add password to key if set."""
        if self._password_encoded is None:
            return key
        key_action = key[3]
        key_suffix = key[4:]
        return KEY_PASSWORD_PREFIX + key_action + self._password_encoded + key_suffix

    async def _send_command(self, key: str, retry: int | None=None) -> bytes | None:
        """Send command to device and read response."""
        if retry is None:
            retry = self._retry_count
        command = bytearray.fromhex(self._commandkey(key))
        _LOGGER.debug("%s: Sending command %s", self.name, command)
        if self._operation_lock.locked():
            _LOGGER.debug(
                "%s: Operation already in progress, waiting for it to complete; RSSI: %s",
                self.name,
                self.rssi,
            )

        max_attempts = retry + 1
        if self._operation_lock.locked():
            _LOGGER.debug(
                "%s: Operation already in progress, waiting for it to complete; RSSI: %s",
                self.name,
                self.rssi,
            )
        async with self._operation_lock:
            for attempt in range(max_attempts):
                try:
                    return await self._send_command_locked(key, command)
                except BleakNotFoundError:
                    _LOGGER.error(
                        "%s: device not found, no longer in range, or poor RSSI: %s",
                        self.name,
                        self.rssi,
                        exc_info=True,
                    )
                    return None
                except CharacteristicMissingError as ex:
                    if attempt == retry:
                        _LOGGER.error(
                            "%s: characteristic missing: %s; Stopping trying; RSSI: %s",
                            self.name,
                            ex,
                            self.rssi,
                            exc_info=True,
                        )
                        return None

                    _LOGGER.debug(
                        "%s: characteristic missing: %s; RSSI: %s",
                        self.name,
                        ex,
                        self.rssi,
                        exc_info=True,
                    )
                except BLEAK_EXCEPTIONS:
                    if attempt == retry:
                        _LOGGER.error(
                            "%s: communication failed; Stopping trying; RSSI: %s",
                            self.name,
                            self.rssi,
                            exc_info=True,
                        )
                        return None

                    _LOGGER.debug(
                        "%s: communication failed with:", self.name, exc_info=True
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
                "%s: Connection already in progress, waiting for it to complete; RSSI: %s",
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
            _LOGGER.debug("%s: Connecting; RSSI: %s", self.name, self.rssi)
            client = await establish_connection(
                BleakClientWithServiceCache,
                self._device,
                self.name,
                self._disconnected,
                cached_services=self._cached_services,
                ble_device_callback=lambda: self._device,
            )
            _LOGGER.debug("%s: Connected; RSSI: %s", self.name, self.rssi)
            resolved = self._resolve_characteristics(client.services)
            if not resolved:
                # Try to handle services failing to load
                resolved = self._resolve_characteristics(await client.get_services())
            self._cached_services = client.services if resolved else None
            self._client = client
            self._reset_disconnect_timer()

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
                "%s: Disconnected from device; RSSI: %s", self.name, self.rssi
            )
            return
        _LOGGER.warning(
            "%s: Device unexpectedly disconnected; RSSI: %s",
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
            "%s: Disconnecting after timeout of %s",
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
            if client and client.is_connected:
                await client.disconnect()

    async def _send_command_locked(self, key: str, command: bytes) -> bytes:
        """Sends a command to the device and reads the response."""
        await self._ensure_connected()
        try:
            return await self._execute_command_locked(key, command)
        except BleakDBusError as ex:
            # Disconnect so we can reset state and try again
            await asyncio.sleep(0.25)
            _LOGGER.debug(
                "%s: RSSI: %s; Backing off %ss; Disconnecting due to error: %s",
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
                "%s: RSSI: %s; Disconnecting due to error: %s", self.name, self.rssi, ex
            )
            await self._execute_disconnect()
            raise

    async def _execute_command_locked(self, key: str, command: bytes) -> bytes:
        """Executes the command and reads the response."""
        assert self._client is not None
        if not self._read_char:
            raise CharacteristicMissingError(UUID_USERREAD_CHAR)
        if not self._write_char:
            raise CharacteristicMissingError(UUID_USERWRITE_CHAR)
        future: asyncio.Future[bytearray] = asyncio.Future()
        client = self._client

        def _notification_handler(_sender: int, data: bytearray) -> None:
            """Handle notification responses."""
            if future.done():
                _LOGGER.debug("%s: Notification handler already done", self.name)
                return
            future.set_result(data)

        _LOGGER.debug("%s: Subscribe to notifications; RSSI: %s", self.name, self.rssi)
        await client.start_notify(self._read_char, _notification_handler)

        _LOGGER.debug("%s: Sending command: %s", self.name, key)
        await client.write_gatt_char(self._write_char, command, False)

        async with async_timeout.timeout(5):
            notify_msg = await future
        _LOGGER.debug("%s: Notification received: %s", self.name, notify_msg)

        _LOGGER.debug("%s: UnSubscribe to notifications", self.name)
        await client.stop_notify(self._read_char)

        if notify_msg == b"\x07":
            _LOGGER.error("Password required")
        elif notify_msg == b"\t":
            _LOGGER.error("Password incorrect")
        return notify_msg

    def get_address(self) -> str:
        """Returns the address of the device."""
        return self._device.address

    def _get_adv_value(self, key: str) -> Any:
        """Returns a value from the advertisement data."""
        if self._override_adv_data and key in self._override_adv_data:
            _LOGGER.debug(
                "%s: Using override value for %s: %s",
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
        if self._device and ble_device_has_changed(self._device, advertisement.device):
            self._cached_services = None
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

    async def _get_basic_info(self) -> bytes | None:
        """Return basic info of device."""
        _data = await self._send_command(
            key=DEVICE_GET_BASIC_SETTINGS_KEY, retry=self._retry_count
        )

        if _data in (b"\x07", b"\x00"):
            _LOGGER.error("Unsuccessful, please try again")
            return None

        return _data

    def _fire_callbacks(self) -> None:
        """Fire callbacks."""
        _LOGGER.debug("%s: Fire callbacks", self.name)
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

    def _check_command_result(
        self, result: bytes | None, index: int, values: set[int]
    ) -> bool:
        """Check command result."""
        if not result or len(result) - 1 < index:
            result_hex = result.hex() if result else "None"
            raise MagicSwitchbotOperationError(
                f"{self.name}: Sending command failed (result={result_hex} index={index} expected={values} rssi={self.rssi})"
            )
        return result[index] in values

    def _set_advertisement_data(self, advertisement: MagicSwitchbotAdvertisement) -> None:
        """Set advertisement data."""
        if advertisement.data.get("data") or not self._sb_adv_data.data.get("data"):
            self._sb_adv_data = advertisement
        self._override_adv_data = None

    def switch_mode(self) -> bool | None:
        """Return true or false from cache."""
        # To get actual position call update() first.
        return self._get_adv_value("switchMode")

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
