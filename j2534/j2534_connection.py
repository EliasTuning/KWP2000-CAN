import queue
import threading
import logging

from .j2534 import J2534
from .j2534 import Protocol_ID
from .j2534 import Ioctl_ID
from .j2534 import Ioctl_Flags
from .j2534 import Ioctl_Parameters
from .j2534 import SCONFIG
from .j2534 import Error_ID
import can

import ctypes


class J2534Connection():
    """
    Low-level J2534 connection wrapper.
    
    Provides raw send/receive functionality for CAN frames through a J2534 Pass-Thru device.
    
    :param dll_path: Path to J2534 DLL (optional, will auto-detect if None)
    :type dll_path: str or None
    :param baudrate: CAN bus baud rate (default: 500000)
    :type baudrate: int
    :param debug: Enable debug logging (default: False)
    :type debug: bool
    :param logger: Optional logger instance (default: root logger)
    :type logger: logging.Logger or None
    """

    def __init__(
            self,
            dll_path: str = None,
            baudrate: int = 500000,
            debug: bool = False,
            logger: logging.Logger = None
    ):
        from .j2534_detect import J2534RegistryDetector
        
        self.logger = logger if logger is not None else logging.getLogger()
        
        # Auto-detect DLL if not provided
        if dll_path is None:
            detector = J2534RegistryDetector()
            devices = detector.list_devices_short()
            if devices:
                # Use first available device
                dll_path = list(devices.values())[0]
                self.logger.info(f"Auto-detected J2534 DLL: {dll_path}")
            else:
                # Fallback to default path
                dll_path = "C:/Program Files (x86)/OpenECU/OpenPort 2.0/drivers/openport 2.0/op20pt32.dll"
                self.logger.warning(f"No J2534 devices found in registry, using default: {dll_path}")

        self.debug = debug

        # Set up a J2534 interface using the DLL provided
        self.interface = J2534(windll=dll_path)

        # Set the protocol to CAN, Baud rate as specified
        self.protocol = Protocol_ID.CAN
        self.baudrate = baudrate

        # Open the interface (connect to the DLL)
        result, self.devID = self.interface.PassThruOpen()
        if result.name == 'ERR_DEVICE_NOT_CONNECTED':
            raise Exception("Device not connected!")

        if debug:
            result = self.interface.PassThruIoctl(
                Handle=0,
                IoctlID=Ioctl_Flags.TX_IOCTL_SET_DLL_DEBUG_FLAGS,
                ioctlInput=Ioctl_Flags.TX_IOCTL_DLL_DEBUG_FLAG_J2534_CALLS,
            )

        # Get the firmeware and DLL version etc, mainly for debugging output
        (
            self.result,
            self.firmwareVersion,
            self.dllVersion,
            self.apiVersion,
        ) = self.interface.PassThruReadVersion(self.devID)
        self.logger.info(
            "J2534 FirmwareVersion: "
            + str(self.firmwareVersion.value)
            + ", dllVersoin: "
            + str(self.dllVersion.value)
            + ", apiVersion"
            + str(self.apiVersion.value)
        )

        # get the channel ID of the interface (used for subsequent communication)
        self.result, self.channelID = self.interface.PassThruConnect(
            self.devID, self.protocol.value, self.baudrate
        )

        # Set the filters and clear the read buffer (filters will be set based on tx/rxids)
        self.result = self.interface.PassThruStartMsgFilter(
            self.channelID, self.protocol.value
        )
        self.result = self.interface.PassThruIoctl(
            self.channelID, Ioctl_ID.CLEAR_RX_BUFFER
        )

        stmin = SCONFIG()
        stmin.Parameter = Ioctl_Parameters.ISO15765_STMIN.value
        stmin.Value = ctypes.c_ulong(0)
        self.result = self.interface.PassThruIoctl(
            Handle=self.channelID, IoctlID=Ioctl_ID.SET_CONFIG, ioctlInput=stmin
        )

        if self.result == Error_ID.ERR_SUCCESS:
            self.logger.info("Set ISO15665_STMIN to 0")
        else:
            self.logger.info("Failed to set ISO15765_STMIN to 0")
            message = self.interface.PassThruGetLastError()
            self.logger.info("Failure message: " + str(message.value))

        blocksize = SCONFIG()
        blocksize.Parameter = Ioctl_Parameters.ISO15765_BS.value
        stmin.Value = ctypes.c_ulong(0)
        self.result = self.interface.PassThruIoctl(
            Handle=self.channelID, IoctlID=Ioctl_ID.GET_CONFIG, ioctlInput=blocksize
        )

        stmin = SCONFIG()
        stmin.Parameter = Ioctl_Parameters.STMIN_TX.value

        st_min = 0xF2
        stmin.Value = ctypes.c_ulong(st_min)
        self.result = self.interface.PassThruIoctl(
            Handle=self.channelID, IoctlID=Ioctl_ID.SET_CONFIG, ioctlInput=stmin
        )

        if self.result == Error_ID.ERR_SUCCESS:
            self.logger.info("Set ISO15665_STMIN_TX to: " + str(stmin.Value))
        else:
            self.logger.info("Failed to set ISO15765_STMIN_TX: " + str(self.result))
            message = self.interface.PassThruGetLastError()
            self.logger.info("Failure message: " + str(message.value))

        self.rxqueue = queue.Queue()
        self.exit_requested = False
        self.opened = False

    def reset_cable(self):
        """Reset cable and filters."""
        self.logger.info("Resetting cable/filter")
        self.result = self.interface.PassThruStartMsgFilter(
            self.channelID, self.protocol.value
        )
        self.result = self.interface.PassThruIoctl(
            self.channelID, Ioctl_ID.CLEAR_RX_BUFFER
        )

    def open(self):
        self.exit_requested = False
        self.rxthread = threading.Thread(target=self.rxthread_task)
        self.rxthread.daemon = True
        self.rxthread.start()
        self.opened = True
        self.logger.info("J2534 Connection opened")
        return self

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def is_open(self):
        return self.opened

    def rxthread_task(self):

        while not self.exit_requested:

            try:
                result, data, numMessages = self.interface.PassThruReadMsgs(
                    self.channelID, self.protocol.value, 1, 1
                )

                if data is not None:
                    self.rxqueue.put(data)
            except Exception:
                self.logger.critical("Exiting J2534 rx thread")
                self.exit_requested = True

    def close(self):
        self.exit_requested = True
        self.rxthread.join()
        result = self.interface.PassThruDisconnect(self.channelID)
        result = self.interface.PassThruClose(self.devID)
        self.opened = False
        self.logger.info("J2534 Connection closed")

    def specific_send(self, payload):
        result = self.interface.PassThruWriteMsgs(
            self.channelID, payload, self.protocol.value
        )

    def specific_wait_frame(self, timeout=4):
        if not self.opened:
            raise RuntimeError("J2534 Connection is not open")

        timedout = False
        frame = None
        try:
            frame = self.rxqueue.get(block=True, timeout=timeout)
            # frame = self.rxqueue.get(block=True, timeout=5)

        except queue.Empty:
            timedout = True

        if timedout:
            pass
            # raise Exception(
            #    "Did not received response from J2534 RxQueue (timeout=%s sec)"
            #    % timeout
            # )

        return frame

    def empty_rxqueue(self):
        while not self.rxqueue.empty():
            self.rxqueue.get()

    # Send and Receive Commands:
    def send(self, msg: can.Message, timeout):
        Data = msg.arbitration_id.to_bytes(4, "big") + msg.data
        self.specific_send(Data)
        pass

    def recv(self, timeout):
        frame = self.specific_wait_frame(timeout)
        if (frame is None):
            return frame
        # print(frame.hex())
        can_message_id = int.from_bytes(frame[0:4], "big")
        can_data = frame[4: len(frame)]

        msg = can.Message(
            arbitration_id=can_message_id, data=can_data, is_extended_id=False
        )
        return msg
