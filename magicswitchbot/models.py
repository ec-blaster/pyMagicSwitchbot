from typing import Any
from dataclasses import dataclass
from bleak.backends.device import BLEDevice

@dataclass
class MagicSwitchbotAdvertisement:
    """MagicSwitchbot advertisement."""
    address: str
    data: dict[str, Any]
    device: BLEDevice