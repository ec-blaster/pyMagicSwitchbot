"""Discover switchbot devices."""

from __future__ import annotations

import asyncio
import logging

import bleak
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from .consts import DEFAULT_RETRY_COUNT, DEFAULT_RETRY_TIMEOUT, DEFAULT_SCAN_TIMEOUT
from .models import MagicSwitchbotAdvertisement

_LOGGER = logging.getLogger(__name__)
CONNECT_LOCK = asyncio.Lock()


class GetMagicSwitchbotDevices:
    """Scan for all MagicSwitchbot devices and return by type."""

    def __init__(self, interface: int=0) -> None:
        """Get MagicSwitchbot devices class constructor."""
        self._interface = f"hci{interface}"
        self._adv_data: dict[str, MagicSwitchbotAdvertisement] = {}

    def detection_callback(
        self,
        device: BLEDevice,
        advertisement_data: AdvertisementData,
    ) -> None:
        """Callback for device detection."""
        discovery = parse_advertisement_data(device, advertisement_data)
        if discovery:
            self._adv_data[discovery.address] = discovery

    async def discover(
        self, retry: int=DEFAULT_RETRY_COUNT, scan_timeout: int=DEFAULT_SCAN_TIMEOUT
    ) -> dict:
        """Find MagicSwitchbot devices and their advertisement data."""

        devices = None
        devices = bleak.BleakScanner(
            # TODO: Find new UUIDs to filter on. For example, see
            # https://github.com/OpenWonderLabs/SwitchBotAPI-BLE/blob/4ad138bb09f0fbbfa41b152ca327a78c1d0b6ba9/devicetypes/meter.md
            adapter=self._interface,
        )
        devices.register_detection_callback(self.detection_callback)

        async with CONNECT_LOCK:
            await devices.start()
            await asyncio.sleep(scan_timeout)
            await devices.stop()

        if devices is None:
            if retry < 1:
                _LOGGER.error(
                    "Scanning for MagicSwitchbot devices failed. Stop trying", exc_info=True
                )
                return self._adv_data

            _LOGGER.warning(
                "Error scanning for MagicSwitchbot devices. Retrying (remaining: %d)",
                retry,
            )
            await asyncio.sleep(DEFAULT_RETRY_TIMEOUT)
            return await self.discover(retry - 1, scan_timeout)

        return self._adv_data

    '''async def _get_devices_by_model(
        self,
        model: str,
    ) -> dict:
        """Get MagicSwitchbot devices by type."""
        if not self._adv_data:
            await self.discover()

        return {
            address: adv
            for address, adv in self._adv_data.items()
            if adv.data.get("model") == model
        }

    async def get_curtains(self) -> dict[str, MagicSwitchbotAdvertisement]:
        """Return all WoCurtain/Curtains devices with services data."""
        return await self._get_devices_by_model("c")

    async def get_bots(self) -> dict[str, MagicSwitchbotAdvertisement]:
        """Return all WoHand/Bot devices with services data."""
        return await self._get_devices_by_model("H")

    async def get_tempsensors(self) -> dict[str, MagicSwitchbotAdvertisement]:
        """Return all WoSensorTH/Temp sensor devices with services data."""
        base_meters = await self._get_devices_by_model("T")
        plus_meters = await self._get_devices_by_model("i")
        return {**base_meters, **plus_meters}

    async def get_contactsensors(self) -> dict[str, MagicSwitchbotAdvertisement]:
        """Return all WoContact/Contact sensor devices with services data."""
        return await self._get_devices_by_model("d")

    async def get_device_data(
        self, address: str
    ) -> dict[str, MagicSwitchbotAdvertisement] | None:
        """Return data for specific device."""
        if not self._adv_data:
            await self.discover()

        return {
            device: adv
            for device, adv in self._adv_data.items()
            # MacOS uses UUIDs instead of MAC addresses
            if adv.data.get("address") == address
        }
    '''


"""Parses the data that the device advertises when scanning for it"""


def parse_advertisement_data(
    device: BLEDevice,
    advertisement_data: AdvertisementData
) -> MagicSwitchbotAdvertisement | None:
    """Parse advertisement data."""
    """MagicSwitchbot advertises using only manufacturer data"""
    """The data format is:
        - 6 bytes for the device's MAC address
        - 1 byte for the battery level (0-100 deccimal)
        - 1 byte for EnPSW (password enabled). 00 is for no password and 01 for password enabled"""
    _mgr_datas = list(advertisement_data.manufacturer_data.values())
    
    if len(_mgr_datas) > 16:
      _data = _mgr_datas[0].hex()
      _LOGGER.debug("MagicSwitchbot data: %s", _data)
      _battery = int("0x" + _data[12:14], 16)
      _enPsw = int ("0x" + _data[14:16], 16)
    else:
      _data = ""
      _battery = 0
      _enPsw = 0

    _LOGGER.debug("Parsing MagicSwitchbot advertising data. Battery level: %d. Password enabled: %d", _battery, _enPsw)
    
    data = {
        "address": device.address,  # MacOS uses UUIDs
        "rawAdvData": _data,
        "data": { "battery": _battery, "rssi": device.rssi },
        "model": "MagicSwitchbot",
        "isEncrypted": True if _enPsw == 1 else False
    }

    return MagicSwitchbotAdvertisement(device.address, data, device)
  
