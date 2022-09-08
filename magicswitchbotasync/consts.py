"""Library to handle connection with MagicSwitchbot."""

"""Connection constants"""
DEFAULT_RETRY_COUNT = 3  # Max number of iterations to try when sending commands to the device
DEFAULT_RETRY_TIMEOUT = 1  # Number of seconds between retries
DEFAULT_SCAN_TIMEOUT = 5  # Max timeout when looking for devices
DISCONNECT_DELAY = 49  # How long to hold the connection to wait for additional commands before disconnecting the device.

"""Constants definition for BLE communication"""    
UUID_SERVICE = "0000fee7-0000-1000-8000-00805f9b34fb"
UUID_USERWRITE_CHAR = "000036f5-0000-1000-8000-00805f9b34fb"
UUID_USERREAD_CHAR = "000036f6-0000-1000-8000-00805f9b34fb"
UUID_NOTIFY_SET = "00002902-0000-1000-8000-00805f9b34fb"
