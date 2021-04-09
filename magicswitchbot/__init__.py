"""
Library to control MagicSwitchbot devices

@author: ec-blaster
@since: March 2021
@license: MIT 
"""
import time
import binascii
import logging
import random
from bluepy import btle
from Crypto.Cipher import AES
from threading import Timer
from binascii import hexlify

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


class PeripheralExt(btle.Peripheral):
    """Derived class from bluepy
    
    This subclass constructor is based  based on Pull Request #374 by Gunnarl,
    https://github.com/IanHarvey/bluepy/pull/374)
    It allows us to stablish a connect timeout to the bluetooth device.
    """

    def __init__(self, deviceAddr=None, addrType=btle.ADDR_TYPE_PUBLIC, iface=None, timeout=None):
        btle.BluepyHelper.__init__(self)
        self._serviceMap = None  # Indexed by UUID
        (self.deviceAddr, self.addrType, self.iface) = (None, None, None)

        if isinstance(deviceAddr, btle.ScanEntry):
            self._connect(deviceAddr.addr, deviceAddr.addrType, deviceAddr.iface, timeout)
        elif deviceAddr is not None:
            self._connect(deviceAddr, addrType, iface, timeout)
            
    def _connect(self, addr, addrType=btle.ADDR_TYPE_PUBLIC, iface=None, timeout=None):
        if len(addr.split(":")) != 6:
            raise ValueError("Expected MAC address, got %s" % repr(addr))
        if addrType not in (btle.ADDR_TYPE_PUBLIC, btle.ADDR_TYPE_RANDOM):
            raise ValueError("Expected address type public or random, got {}".format(addrType))
        self._startHelper(iface)
        self.addr = addr
        self.addrType = addrType
        self.iface = iface
        if iface is not None:
            self._writeCmd("conn %s %s %s\n" % (addr, addrType, "hci" + str(iface)))
        else:
            self._writeCmd("conn %s %s\n" % (addr, addrType))
        rsp = self._getResp('stat', timeout)
        if rsp is None:
            raise btle.BTLEDisconnectError("Timed out while trying to connect to peripheral %s, addr type: %s" % 
                                      (addr, addrType), rsp)
        while rsp['state'][0] == 'tryconn':
            rsp = self._getResp('stat', timeout)
        if rsp['state'][0] != 'conn':
            self._stopHelper()
            raise btle.BTLEDisconnectError("Failed to connect to peripheral %s, addr type: %s" % (addr, addrType), rsp)


class MagicSwitchbotDelegate (btle.DefaultDelegate):
    """MagicSwitchbotDelegate
    
    Bluetooth notifications subscription to handle responses from the MagicSwitchbot device
    """

    def __init__(self, readHandle, mac):
        """Class constructor
        
        This constructor must receive the handle of the characteristic we want to subscribe to.
        Parameters
        ----------
        readHandle : int
            Handle to the bluetooth characteristic we want to subscribe
        mac : string
            MAC address of the device
        """
        btle.DefaultDelegate.__init__(self)
        self._readHandle = readHandle
        self._mac = mac
        self._data = None
        self._received = False
        _LOGGER.debug("MagicSwitchbot[%s] Notification handler initialized", mac)
      
    def resetData(self):
        """Resets the received data through the characteristic
        """
        self._data = None
        self._received = False
        _LOGGER.debug("MagicSwitchbot[%s] Resetting received data", self._mac)
      
    def hasData(self) -> bool:
        """Check if data received
      
        This method checks if we received any data after latest reset
      
        Returns
        -------
            bool
                Returns True if there is data present
        """
        return self._received
    
    def getData(self) -> str:
        """Gets the received data
      
        This method retrieves the data sent by the device to the client
        in response to the latest command issued.
      
        Returns
        -------
            str
                Hexadecimal representation of the received data
        """
        return self._data.hex()
      
    def handleNotification(self, cHandle, data):
        """Notifications handler
      
        This method manages all notifications received from the MagicSwitchbot device
        We must filter those notifications that we expect in a normal protocol life cycle
      
        Parameters
        ----------
        cHandle : int
            Handle to the characteristic that sends the notification data 
          
        data : bytes
            Data that the characteristic sends
        """
        if (cHandle == self._readHandle):
            '''Filter our notified data'''
            self._received = True
            self._data = data
        else:
            '''Discard all other notifications'''
            _LOGGER.debug("MagicSwitchbot[%s] Received data from device at unexpected handle %d: %s", self._mac, cHandle, data)
            btle.DefaultDelegate.handleNotification(self, cHandle, data)


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
    
    def __init__(self, mac, retry_count=DEFAULT_RETRY_COUNT, password=None, interface=0, connect_timeout=DEFAULT_CONNECT_TIMEOUT, disconnect_timeout=NO_TIMEOUT) -> None:
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
        self._device = None
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
        
    def __del__(self):
        self._disconnect()

    def _connect(self, connect_timeout=DEFAULT_CONNECT_TIMEOUT, disconnect_timeout=NO_TIMEOUT, retries=1) -> bool:
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
            try:
                _LOGGER.debug("MagicSwitchbot[%s] Connecting using hci%d with %d seconds timeout (%d of %d retries)...", self._mac, self._interface, connect_timeout, (i + 1), retries)
                self._device = PeripheralExt(deviceAddr=self._mac,
                                             addrType=btle.ADDR_TYPE_PUBLIC,
                                             iface=self._interface,
                                             timeout=connect_timeout)
                _LOGGER.info("MagicSwitchbot[%s] Connected with hci%d.", self._mac, self._interface)
                partial_connect = True
                
                '''Initialize service and characteristics handles to the device'''
                self._service = self._device.getServiceByUUID(self.UUID_SERVICE)
                self._userReadChar = self._service.getCharacteristics(self.UUID_USERREAD_CHAR)[0]
                self._cccdDescriptor = self._userReadChar.getDescriptors(forUUID=self.UUID_NOTIFY_SET)[0]
                self._userWriteChar = self._service.getCharacteristics(self.UUID_USERWRITE_CHAR)[0]
    
                '''Once we connected, let's enable the response notifications'''
                self._enableNotifications()
                
                connected = True
                
                self._scheduleDisconnection()
            except btle.BTLEDisconnectError as e:
                if partial_connect:
                    _LOGGER.error("MagicSwitchbot[%s] Incomplete connection to device (%s)", self._mac, str(e))
                else:
                    _LOGGER.error("MagicSwitchbot[%s] Couldn't connect to device (%s)", self._mac, str(e))
                self._device = None
            except btle.BTLEException:
                _LOGGER.error("MagicSwitchbot[%s] Failed to connect to device", self._mac, exc_info=True)
                self._device = None
            except Exception:
                _LOGGER.error("MagicSwitchbot[%s] Error getting device info", self._mac, exc_info=True)
                self._device = None
            
            if connected:
                return True
            elif i < retries - 1:
                _LOGGER.debug("MagicSwitchbot[%s] Retrying in %d seconds...", self._mac, DEFAULT_RETRY_TIMEOUT)
                time.sleep(DEFAULT_RETRY_TIMEOUT)
        
        return connected
    
    def _scheduleDisconnection(self):
        '''We stablish a timer to disconnect after some time, if the user wants so'''
        
        if self._timer is not None:
            self._timer.cancel()
            
        if self._disconnectTimeout != NO_TIMEOUT:
            self._timer = Timer(self._disconnectTimeout, self._disconnect, [True]) 
            self._timer.start()
            _LOGGER.info("MagicSwitchbot[%s] Auto-disconnect scheduled for %d seconds.", self._mac, self._disconnectTimeout)

    def _enableNotifications(self) -> bool:
        """Enable read notifications
        
        We establish how we receive the notifications from the device
        """
        readHandle = self._userReadChar.getHandle()

        notifOk = False

        _LOGGER.debug("MagicSwitchbot[%s] Enabling notifications for userRead characteristic (%s). Handle: 0x%X", self._mac, self.UUID_USERREAD_CHAR, readHandle)
        _LOGGER.debug("MagicSwitchbot[%s] Client Characteristic Configuration Descriptor: %s. Handle: 0x%X", self._mac, self.UUID_NOTIFY_SET, self._cccdDescriptor.handle)

        '''Subscribe to userRed characteristic notifications'''
        self._delegate = MagicSwitchbotDelegate(readHandle, self._mac)
        self._device.withDelegate(self._delegate)

        '''Enable the notifications for the read characteristic'''
        try:
            res = self._cccdDescriptor.write(binascii.a2b_hex(self.CMD_ENNOTIF), withResponse=True)
            res = self._cccdDescriptor.read()
            _LOGGER.debug("MagicSwitchbot[%s] Characteristic notifications enabled: %s", self._mac, res)
            notifOk = True
        except btle.BTLEGattError as e:
            _LOGGER.error("MagicSwitchbot[%s] Error enabling notifications: %s\n", self._mac, str(e))

        return notifOk

    def _disconnect(self, scheduled=False) -> None:
        """Discconnects from the device"""
        
        self._timer = None
        _LOGGER.debug("MagicSwitchbot[%s] Disconnecting%s", self._mac, " on scheduled time" if scheduled else "")
        if not self._is_connected():
            self._device = None
            _LOGGER.debug("MagicSwitchbot[%s] The device was not connected", self._mac)
            return
        
        try:
            self._device.disconnect()
            _LOGGER.info("MagicSwitchbot[%s] Client disconnected", self._mac)
            self._token = None
        except Exception as e:
            _LOGGER.warning("MagicSwitchbot[%s] Error disconnecting: %s", self._mac, str(e))
        finally:
            self._device = None
            
    def _is_connected(self) -> bool:
        """Checks if the device is connected
        
        Return
        ------
            bool
                Returns True if the device is still connected
        """
        
        if self._device is not None:
            conn_status = ""
            
            for i in range (self._retry_count):
                try:
                    '''We get the current connection state using an undocumented method from Peripheral'''
                    if self._device is not None:
                        conn_status = self._device.getState()
                    else:
                        conn_status = ""
                except Exception as e:
                    _LOGGER.warn("MagicSwitchbot[%s] %s when checking connection state (%d of %d attempts)", self._mac, str(e), i + 1, self._retry_count)
                    
                    if i < self._retry_count - 1:
                        '''We'll retry to check the state'''
                        time.sleep(0.5)
                    else:
                        '''We have an unknown state. Let's disconnect'''
                        if self._device is not None:
                            self._device.disconnect()
                        self._token = None
                        self._device = None
            connected = (conn_status == "conn")
        else:
            connected = False
            
        _LOGGER.debug("MagicSwitchbot[%s] Connected state: %s", self._mac, "True" if connected else "False")
        
        return connected
            
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
        cipher = AES.new(bytes(bytearray(self.CRYPT_KEY)), AES.MODE_ECB)
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
        decipher = AES.new(bytes(bytearray(self.CRYPT_KEY)), AES.MODE_ECB)
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
        
        _LOGGER.info("MagicSwitchbot[%s] Sending %s command: %s", self._mac, self.COMMANDS[command], fullCommand)

        return self._encrypt(fullCommand)

    def _writeData(self, data) -> bool:
        """Write data to the device
        
        This method writes data to the device via BLE, using the "userWrite" characteristic
        
        Parameters
        ----------
            data: str
                Hexadecimal string with 16 encryopted bytes of data to write

        Returns
        -------
            bool
                Returns True if the data is sent succesfully
        """
      
        self._delegate.resetData()
        _LOGGER.debug("MagicSwitchbot[%s] Sending encrypted data: %s", self._mac, data)
        write_result = self._userWriteChar.write(binascii.a2b_hex(data), True)
        
        if not write_result:
            _LOGGER.error("MagicSwitchbot[%s] Sent command but didn't get a response. Please check the device.", self._mac)
        else:
            _LOGGER.debug("MagicSwitchbot[%s] Data sent OK", self._mac)
            
        return write_result

    def _sendCommand(self, command, parameter, retries) -> bool:
        """Sends a command to the device
        
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
                Returns True if the data was sent succesfully and did get a positive aknowledge after
        """
        
        if self._connect(connect_timeout=self._connectTimeout, retries=retries):
            '''First of all we check if there is a token to retrieve'''
            if command != self.CMD_GETTOKEN and self._token is None:
                '''If the command is NOT GETTOKEN, we'll issue a GETOTKEN command before sending the actual command'''
                go = self._auth()
            else:
                go = True
            
            if go:
                send_success = False
                resp_success = False
                encrypted_command = self._prepareCommand(command, parameter)
                try:
                    send_success = self._writeData(encrypted_command)
                    if send_success:
                        ''' Wait for a response'''
                        
                        _LOGGER.debug("MagicSwitchbot[%s] Waiting for notifications...", self._mac)
                        received = False
                        start_time = time.time()
                        while not self._delegate.hasData():
                            elapsed_time = time.time() - start_time
                            if self._device.waitForNotifications(1.0):
                                received = True
                                continue
                            if elapsed_time >= NOTIFY_TIMEOUT:
                                continue
                                
                            _LOGGER.debug("MagicSwitchbot[%s] Waiting...", self._mac)
                        
                        if received:
                            encrypted_response = self._delegate.getData()
                            _LOGGER.debug("MagicSwitchbot[%s] Encrypted data received: %s", self._mac, encrypted_response)
                            
                            plain_response = self._decrypt(encrypted_response)
                            _LOGGER.debug("MagicSwitchbot[%s] Unencrypted result: %s", self._mac, plain_response)
                            resp_success = self._processResponse(plain_response)
                        else:
                            _LOGGER.error("MagicSwitchbot[%s] No response received in %d seconds ", self._mac, NOTIFY_TIMEOUT)
                except Exception as e:
                    _LOGGER.warn("MagicSwitchbot[%s] Communication error: %s", self._mac, str(e))
                    self._disconnect()
                    
                if resp_success:
                    self._scheduleDisconnection()
                    return True
                if retries < 1:
                    _LOGGER.error("MagicSwitchbot[%s] Communication failed. We won't try again.", self._mac, exc_info=True)
                    self._device = None
                    return False
                else:
                    _LOGGER.warning("MagicSwitchbot[%s] Communication failed. Remaining attempts: %d...", self._mac, retries)
        
                time.sleep(DEFAULT_RETRY_TIMEOUT)
                return self._sendCommand(command, parameter, retries - 1)
            else:
                return False
        else:
            return False
      
    def _auth(self) -> bool:
        """Validate the password set on the device
        
        Validate the password set on the device and gets the communication token.
        The password we use is set on construct

        Returns
        -------
            bool
                Returns true if password is correct
        """
        return self._sendCommand(self.CMD_GETTOKEN, "" if self._password is None else self._passwordToHex(self._password), self._retry_count)
    
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
        
    def _processResponse(self, response) -> bool:
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
      
        _LOGGER.info("MagicSwitchbot[%s] Response: (Command = %s, Return Code = %s, Length = %d, Params = %s)", self._mac, command, ret_code, param_length, param)
      
        if command == self.CMD_GETTOKEN[0:2]:
            if ret_code == self.RC_TOKENOK:
                token = param[0:8]
                chip_type = param[8:10]
                ver_major = int(param[10:12])
                ver_minor = int(param[12:14])
                dev_type = param[14:16]
                en_pwd = "False" if param[16:18] == '00' else "True"
                self._token = token 
                _LOGGER.info("MagicSwitchbot[%s] The current connection token is %s", self._mac, token)
                _LOGGER.info("MagicSwitchbot[%s] Chip type: %s, Firmware version: %d.%d, Device type: %s, Password enabled: %s", self._mac, chip_type, ver_major, ver_minor, dev_type, en_pwd)
                success = True
            else:
                _LOGGER.error("MagicSwitchbot[%s] Error retrieving token. Please check password", self._mac)
        elif command == self.CMD_GETBAT[0:2]:
            if ret_code == self.RC_GETBAT and param.upper() != "FF":
                self._battery = int("0x" + param, 16)
                _LOGGER.info("MagicSwitchbot[%s] Battery level: %d%%", self._mac, self._battery)
                success = True
            else:
                self._battery = None
        elif command == self.CMD_SWITCH[0:2]:
            if ret_code == self.RC_SWITCH and param == self.STA_OK:
                _LOGGER.info("MagicSwitchbot[%s] Switch state changed successfully", self._mac)
                success = True
            else:
                _LOGGER.error("MagicSwitchbot[%s] Error changing switch state", self._mac)
                
        return success 


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
        """Validate the password set on the device
        
        Validate the password set on the device and gets the communication token.
        The password we use is set on construct

        Returns
        -------
            bool
                Returns true if password is correct
        """
        return self._auth()
    
    def disconnect(self) -> None:
        """Discconnects from the device"""
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
        """Turn device on."""
        return self._sendCommand(self.CMD_SWITCH, self.PAR_SWITCHON, self._retry_count)

    def turn_off(self) -> bool:
        """Turn device off."""
        return self._sendCommand(self.CMD_SWITCH, self.PAR_SWITCHOFF, self._retry_count)
      
    def push(self) -> bool:
        """Just push  a button"""
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
