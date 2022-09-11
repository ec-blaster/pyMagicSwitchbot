"""Library to handle connection with MagicSwitchbot."""

"""Connection constants"""
DEFAULT_RETRY_COUNT = 3  # Max number of iterations to try when sending commands to the device
DEFAULT_RETRY_TIMEOUT = 1  # Number of seconds between retries
DEFAULT_SCAN_TIMEOUT = 5  # Max timeout when looking for devices
NOTIFY_TIMEOUT = 5 # Max seconds to wait before the device sends back the response to a command
DISCONNECT_DELAY = 49  # How long to hold the connection to wait for additional commands before disconnecting the device.

"""Constants definition for BLE communication"""    
#UUID_SERVICE = "0000fee7-0000-1000-8000-00805f9b34fb"
UUID_USERWRITE_CHAR = "000036f5-0000-1000-8000-00805f9b34fb"
UUID_USERREAD_CHAR = "000036f6-0000-1000-8000-00805f9b34fb"

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