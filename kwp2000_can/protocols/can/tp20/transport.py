"""TP20 transport layer for sending and receiving byte data over CAN."""

import queue
import threading
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

from .constants import (
    CAN_ID_SETUP_REQUEST,
    CAN_ID_SETUP_RESPONSE_BASE,
    DEFAULT_RX_ID,
    DEFAULT_TX_ID,
    DATA_OP_WAIT_ACK_MORE,
    DATA_OP_WAIT_ACK_LAST,
    DATA_OP_NO_ACK_MORE,
    DATA_OP_NO_ACK_LAST,
    DATA_OP_ACK_READY,
    DATA_OP_ACK_NOT_READY,
    SEQ_MASK,
    OPCODE_CHANNEL_TEST,
    OPCODE_BREAK,
    OPCODE_DISCONNECT,
    MNTB,
    MNT,
    MNTC,
    MNCT,
    T_WAIT_MS,
    T_E_MS,
    TN_MS,
    T_CT_PASSIV_MS,
    BS_MIN,
    BS_MAX,
    PRIO_CA_CT,
    PRIO_BR,
    PRIO_ACK,
    PRIO_DT_CS_DC,
    OPCODE_PARAMETERS_REQUEST,
)
from .exceptions import (
    TP20AckRetryException,
    TP20ChannelException,
    TP20DisconnectedException,
    TP20Exception,
    TP20TimeoutException,
)
from .frames import (
    build_setup_request,
    parse_setup_response,
    build_parameters_request,
    build_parameters_response,
    parse_parameters_response,
    build_data_frame,
    parse_data_frame,
    build_disconnect,
    build_channel_test,
)
from .timing import TimingParameter

from .base_can_connection import CanConnection


def _check_t1_gt_4_t3(t1_byte: int, t3_byte: int) -> None:
    """Raise ValueError if T1 <= 4*T3 (TP2.0_1_1 §5.2 requires T1 > 4*T3)."""
    t1_ms = TimingParameter.decode(t1_byte)
    t3_ms = TimingParameter.decode(t3_byte)
    if t1_ms <= 4 * t3_ms:
        raise ValueError(
            f"T1 ({t1_ms} ms) must be > 4×T3 ({t3_ms} ms) per TP2.0_1_1 §5.2"
        )


from .transport_base import Transport


class _CommandType(Enum):
    OPEN = auto()
    CLOSE = auto()
    SEND = auto()
    RECV = auto()
    RENEGOTIATE = auto()
    STOP = auto()


@dataclass
class _Command:
    cmd_type: _CommandType
    data: bytes = None
    timeout: float = None


@dataclass
class _Response:
    success: bool
    data: bytes = None
    exception: Exception = None


class TP20Transport(Transport):
    """
    TP20 transport layer that wraps a CAN connection.
    
    Handles TP20 protocol details like channel setup, segmentation, and reassembly.
    Sends and receives byte data directly.
    
    Usage:
        can_conn = MockCanConnection()
        transport = TP20Transport(can_conn, dest=0x01)
        with transport:
            transport.send(b'\\x10\\x89')
            data = transport.recv(timeout=1.0)
    """
    
    def __init__(
        self,
        can_connection: CanConnection,
        dest: int = 0x01,
        rx_id: int = DEFAULT_RX_ID,
        tx_id: int = DEFAULT_TX_ID,
        block_size: int = 0x0F,
        t1: int = 0x8A,
        t3: int = 0x32,
        timeout: float = 1.0,
        keepalive_interval_ms: float = 1000.0,
    ):
        """
        Initialize TP20 transport.

        Args:
            can_connection: CAN connection to use
            dest: Logical address of destination module (default: 0x01 for ECU)
            rx_id: Preferred RX CAN ID (default: 0x300)
            tx_id: Preferred TX CAN ID (default: 0x740)
            block_size: Block size for data transmission (default: 15)
            t1: Timing parameter 1 (default: 0x8A)
            t3: Timing parameter 3 (default: 0x32)
            timeout: Default timeout in seconds
            keepalive_interval_ms: Interval for channel test (A3) frames (default: 1000 ms)
        """
        self.can_connection = can_connection
        self.dest = dest
        self.preferred_rx_id = rx_id
        self.preferred_tx_id = tx_id
        if not BS_MIN <= block_size <= BS_MAX:
            raise ValueError(
                f"block_size must be {BS_MIN}..{BS_MAX} (TP2.0_1_1 §5.2), got {block_size}"
            )
        self.block_size = block_size
        self.t1 = t1
        self.t3 = t3
        _check_t1_gt_4_t3(t1, t3)  # TP2.0_1_1 §5.2
        self.timeout = timeout
        self.keepalive_interval_ms = keepalive_interval_ms

        # Channel state
        self._is_open = False
        self._channel_setup = False
        self._rx_can_id = None  # CAN ID we listen on
        self._tx_can_id = None  # CAN ID we transmit on
        self._remote_rx_id = None  # CAN ID remote listens on
        self._remote_tx_id = None  # CAN ID remote transmits on
        self._block_size = None
        self._t1 = None
        self._t3 = None
        
        # Receive buffer for reassembly
        self._receive_buffer = bytearray()
        self._receive_sequence = None
        self._receive_length = None
        self._sn_error_count = 0  # Blocknachforderung counter; reset on correct SN, close if > MNTB
        
        # Send sequence number (continues across messages)
        self._send_sequence = 0
        # T1 timeout retry counter (TP2.0_1_1 §6.3.1); reset on successful ACK, close if > MNT
        self._rc_s = 0
        # Break requested by receiver (TP2.0_1_1 §6.3.4); sender must end with EOM
        self._break_requested = False
        # Connection setup retry counter (TP2.0_1_1 §6.1.1); abort when RC_E > MNTC (11 total attempts per §5.1 n+1 rule)
        self._rc_e = 0
        # BEC per §6.3.2: reset on RR, increment on RNR; close if > MNTB
        self._bec = 0
        # Passive Connection Test (§6.4): expect CT from peer within T_CTpassiv; close if RC_CT > MNCT
        self._last_ct_received: float = 0.0
        self._rc_ct: int = 0
        # CS/CA re-exchange (§6.3): block sends while renegotiating
        self._renegotiating: bool = False

        # Threading primitives
        self._cmd_queue: queue.Queue[_Command] = queue.Queue()
        self._response_queue: queue.Queue[_Response] = queue.Queue()
        self._rx_queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._keepalive_stop_event = threading.Event()
        self._keepalive_thread: Optional[threading.Thread] = None
        self._worker_thread: Optional[threading.Thread] = None
        # Outgoing TPDU queue (priority, tie_breaker, can_id, data, event) per §4.2.2 and §6.2
        self._send_queue: queue.PriorityQueue = queue.PriorityQueue()
        self._send_seq = 0
        self._sender_stop_event = threading.Event()
        self._sender_thread: Optional[threading.Thread] = None
        
    def open(self) -> None:
        """Open the transport and establish TP20 channel via worker thread."""
        if self._is_open:
            return

        self._start_worker()
        self._submit_command(_CommandType.OPEN)

    def close(self) -> None:
        """Close the transport and stop the worker thread."""
        if not self._worker_thread:
            return

        # Attempt a graceful close first
        try:
            self._submit_command(_CommandType.CLOSE)
        except Exception:
            # Ignore close errors so we still stop the worker
            pass

        # Stop the worker thread
        try:
            self._submit_command(_CommandType.STOP)
        finally:
            if self._worker_thread and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=1.0)
            self._worker_thread = None

    def send(self, data: bytes) -> None:
        """
        Send byte data over TP20.

        Args:
            data: Byte data to send

        Raises:
            TP20DisconnectedException: If channel is not set up
            TP20Exception: If send fails
        """
        if not self._worker_thread:
            raise TP20Exception("Transport worker not running")

        self._submit_command(_CommandType.SEND, data=data)

    def recv(self, timeout: float = 1.0) -> Optional[bytes]:
        """
        Receive byte data over TP20.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            Received byte data, or None if timeout occurs

        Raises:
            TP20TimeoutException: If timeout occurs
            TP20Exception: If receive fails
        """
        if not self._worker_thread:
            raise TP20Exception("Transport worker not running")

        return self._submit_command(_CommandType.RECV, timeout=timeout)
    
    def wait_frame(self, timeout: float = 1.0) -> Optional[bytes]:
        """
        Wait for and receive a frame (KWP2000 Transport interface compatibility).

        This method wraps recv() but returns None on timeout instead of raising an exception,
        making TP20Transport compatible with KWP2000 Transport interface.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            Received byte data, or None if timeout occurs
        """
        try:
            return self.recv(timeout=timeout)
        except TP20TimeoutException:
            return None

    def _start_worker(self) -> None:
        """Start the worker thread if it is not already running."""
        if self._worker_thread and self._worker_thread.is_alive():
            return
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def _start_keepalive(self) -> None:
        """Start the keep-alive (A3) sender if enabled."""
        if self.keepalive_interval_ms <= 0:
            return
        if self._keepalive_thread and self._keepalive_thread.is_alive():
            return
        self._keepalive_stop_event.clear()
        self._keepalive_thread = threading.Thread(
            target=self._keepalive_loop, daemon=True
        )
        self._keepalive_thread.start()

    def _stop_keepalive(self) -> None:
        """Stop the keep-alive sender."""
        self._keepalive_stop_event.set()
        if self._keepalive_thread and self._keepalive_thread.is_alive():
            self._keepalive_thread.join(timeout=1.0)
        self._keepalive_thread = None

    def _start_sender(self) -> None:
        """Start the sender thread (drains _send_queue in priority order, T3 between sends)."""
        if self._sender_thread and self._sender_thread.is_alive():
            return
        self._sender_stop_event.clear()
        self._sender_thread = threading.Thread(target=self._sender_loop, daemon=True)
        self._sender_thread.start()

    def _stop_sender(self) -> None:
        """Stop the sender thread and drain the send queue."""
        self._sender_stop_event.set()
        if self._sender_thread and self._sender_thread.is_alive():
            self._sender_thread.join(timeout=1.0)
        self._sender_thread = None
        self._clear_send_queue()

    def _clear_send_queue(self) -> None:
        """Drain the send queue and signal any waiting events so callers don't block forever."""
        try:
            while True:
                item = self._send_queue.get_nowait()
                if len(item) >= 5 and item[4] is not None:
                    item[4].set()
        except queue.Empty:
            pass

    def _sender_loop(self) -> None:
        """Send TPDUs from queue in priority order; sleep T3 after each send (§4.2.2, §6.2)."""
        while not self._sender_stop_event.is_set():
            try:
                item = self._send_queue.get(timeout=0.05)
            except queue.Empty:
                continue
            priority, _tb, can_id, data, evt = item
            try:
                if self.can_connection:
                    self.can_connection.send_can_frame(can_id, data)
            except Exception:
                pass
            if evt is not None:
                evt.set()
            if self._t3 is not None:
                try:
                    t3_ms = TimingParameter.decode(self._t3)
                except (ValueError, TypeError):
                    t3_ms = 5.0
                self._sender_stop_event.wait(timeout=t3_ms / 1000.0)
            else:
                self._sender_stop_event.wait(timeout=0.005)

    def _send_tpdu(self, priority: int, can_id: int, data: bytes, wait_sent: bool = True) -> None:
        """Enqueue a TPDU for sending in priority order; optionally wait until sent (§4.2.2)."""
        evt = threading.Event() if wait_sent else None
        self._send_seq += 1
        self._send_queue.put((priority, self._send_seq, can_id, data, evt))
        if evt is not None:
            if not evt.wait(timeout=2.0):
                raise TP20Exception("Send timeout waiting for TPDU to be sent")

    def _keepalive_loop(self) -> None:
        """Periodically send channel test (A3) frames. This transport is the active CT side (CS sender) per TP2.0_1_1 §6.4 and only sends CT."""
        interval = self.keepalive_interval_ms / 1000.0
        while not self._keepalive_stop_event.wait(interval):
            if not self._is_open or not self._channel_setup:
                continue
            if self._tx_can_id is None:
                continue
            try:
                self._send_tpdu(PRIO_CA_CT, self._tx_can_id, build_channel_test(), wait_sent=False)
            except Exception:
                # Ignore keep-alive send errors to avoid stopping the loop
                continue

    def _submit_command(
        self,
        cmd_type: _CommandType,
        data: bytes = None,
        timeout: float = None,
    ):
        """Put a command on the queue and wait for the response."""
        self._cmd_queue.put(_Command(cmd_type, data=data, timeout=timeout))
        response = self._response_queue.get()
        if response.exception:
            raise response.exception
        return response.data

    def _worker_loop(self) -> None:
        """Background loop that polls CAN RX and processes commands."""
        while not self._stop_event.is_set():
            # Passive Connection Test (§6.4): close if no CT received within T_CTpassiv, RC_CT > MNCT
            if self._is_open and self._channel_setup and self._last_ct_received > 0:
                if time.time() - self._last_ct_received > T_CT_PASSIV_MS / 1000.0:
                    self._rc_ct += 1
                    self._last_ct_received = time.time()
                    if self._rc_ct > MNCT:
                        self._disconnect_channel()

            # Opportunistically poll CAN RX to keep the RX queue warm
            if self._is_open:
                try:
                    frame = self.can_connection.recv_can_frame(timeout=0.01)
                except Exception:
                    frame = None
                if frame is not None:
                    can_id, data = frame
                    # TP2.0_1_1 §6.4: on receipt of CT (0xA3) we must respond with CT.
                    # Accept CT on both channel IDs: some ECUs send CT on _tx_can_id (e.g. 0x740).
                    if (
                        self._channel_setup
                        and (can_id == self._rx_can_id or can_id == self._tx_can_id)
                        and len(data) == 1
                        and data[0] == OPCODE_CHANNEL_TEST
                    ):
                        self._last_ct_received = time.time()
                        self._rc_ct = 0
                        try:
                            self._send_tpdu(
                                PRIO_CA_CT,
                                self._tx_can_id,
                                build_channel_test(),
                                wait_sent=False,
                            )
                        except Exception:
                            pass
                        continue
                    self._rx_queue.put(frame)

            try:
                cmd = self._cmd_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            response = self._dispatch_command(cmd)
            self._response_queue.put(response)

            if cmd.cmd_type == _CommandType.STOP:
                break

    def _dispatch_command(self, cmd: _Command) -> _Response:
        """Execute a command and capture success/exception."""
        try:
            if cmd.cmd_type == _CommandType.OPEN:
                self._do_open()
                return _Response(True)
            if cmd.cmd_type == _CommandType.CLOSE:
                self._do_close()
                return _Response(True)
            if cmd.cmd_type == _CommandType.SEND:
                self._do_send(cmd.data)
                return _Response(True)
            if cmd.cmd_type == _CommandType.RECV:
                data = self._do_recv(timeout=cmd.timeout or self.timeout)
                return _Response(True, data=data)
            if cmd.cmd_type == _CommandType.RENEGOTIATE:
                self._do_renegotiate()
                return _Response(True)
            if cmd.cmd_type == _CommandType.STOP:
                self._do_stop()
                return _Response(True)
            return _Response(False, exception=TP20Exception("Unknown command"))
        except Exception as exc:  # pragma: no cover - defensive capture
            return _Response(False, exception=exc)

    def _do_open(self) -> None:
        """Open CAN connection and negotiate TP20 channel."""
        if self._is_open:
            return
        self.can_connection.open()
        self._is_open = True
        try:
            self._setup_channel()
            self._start_sender()
            self._negotiate_parameters()
            self._start_keepalive()
        except Exception as exc:
            self._do_close()
            raise TP20Exception(f"Failed to open TP20 channel: {exc}") from exc

    def _do_close(self) -> None:
        """Close TP20 channel and underlying CAN connection."""
        if not self._is_open:
            self._reset_state()
            return

        if self._channel_setup:
            try:
                self._disconnect_channel()
            except Exception:
                # Ignore errors during disconnect to ensure closure
                pass

        self._stop_keepalive()

        try:
            self.can_connection.close()
        finally:
            self._reset_state()

    def _do_send(self, data: bytes) -> None:
        if not self._is_open:
            raise TP20Exception("Transport not open")
        if not self._channel_setup:
            raise TP20DisconnectedException("Channel not set up")
        if self._renegotiating:
            raise TP20Exception("Send blocked during parameter renegotiation")

        length = len(data)
        payload = bytearray()
        payload.append((length >> 8) & 0xFF)
        payload.append(length & 0xFF)
        payload.extend(data)
        self._send_segmented(payload)

    def _do_recv(self, timeout: float) -> Optional[bytes]:
        if not self._is_open:
            raise TP20Exception("Transport not open")
        if not self._channel_setup:
            raise TP20DisconnectedException("Channel not set up")

        start_time = time.time()
        self._receive_buffer.clear()
        self._receive_length = None
        self._receive_sequence = None

        while True:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                raise TP20TimeoutException("Timeout waiting for frame")

            remaining_timeout = timeout - elapsed
            frame = self._next_frame(timeout=remaining_timeout)
            if frame is None:
                continue

            can_id, data = frame
            # CT (0xA3) accepted on both channel IDs; data frames only on _rx_can_id
            if len(data) == 1 and data[0] == OPCODE_CHANNEL_TEST and (can_id == self._rx_can_id or can_id == self._tx_can_id):
                self._last_ct_received = time.time()
                self._rc_ct = 0
                self._send_tpdu(
                    PRIO_CA_CT, self._tx_can_id, build_channel_test(), wait_sent=False
                )
                continue
            if can_id != self._rx_can_id:
                continue

            if len(data) == 1 and data[0] == 0xA8:
                raise TP20DisconnectedException("Received A8")
            if len(data) == 1 and data[0] == OPCODE_BREAK:
                # TP2.0_1_1 §6.3.4: sender will end with EOM; discard data
                self._receive_buffer.clear()
                self._receive_length = None
                self._receive_sequence = None
                continue

            # Remote-initiated CS/CA re-exchange (§6.3): reply with CA and reset state
            if len(data) >= 6 and data[0] == OPCODE_PARAMETERS_REQUEST:
                ca_frame = build_parameters_response(
                    block_size=self.block_size,
                    t1=self.t1,
                    t2=0xFF,
                    t3=self.t3,
                    t4=0xFF,
                )
                self._send_tpdu(PRIO_CA_CT, self._tx_can_id, ca_frame)
                self._reset_protocol_state_after_cs_ca()
                continue

            try:
                opcode, sequence, payload = parse_data_frame(data)
            except ValueError:
                continue

            if opcode in (DATA_OP_ACK_READY, DATA_OP_ACK_NOT_READY):
                continue

            if opcode in (
                DATA_OP_WAIT_ACK_MORE,
                DATA_OP_WAIT_ACK_LAST,
                DATA_OP_NO_ACK_MORE,
                DATA_OP_NO_ACK_LAST,
            ):
                if self._receive_sequence is not None:
                    expected_seq = (self._receive_sequence + 1) & SEQ_MASK
                    if sequence != expected_seq:
                        # TP2.0_1_1 §6.3.3/6.5: discard frame, send Ack RR with expected SN (request retransmit)
                        ack_frame = build_data_frame(
                            DATA_OP_ACK_READY, expected_seq, b""
                        )
                        self._send_tpdu(PRIO_ACK, self._tx_can_id, ack_frame)
                        self._sn_error_count += 1
                        if self._sn_error_count > MNTB:
                            self._disconnect_channel()
                            raise TP20ChannelException(
                                "SN error count exceeded MNTB (Blocknachforderung)"
                            )
                        continue

                if self._receive_length is None:
                    if len(payload) < 2:
                        continue
                    self._receive_length = (payload[0] << 8) | payload[1]
                    self._receive_buffer.extend(payload[2:])
                    self._receive_sequence = sequence
                    self._sn_error_count = 0
                else:
                    self._receive_buffer.extend(payload)
                    self._receive_sequence = sequence
                    self._sn_error_count = 0

                if opcode in (DATA_OP_WAIT_ACK_MORE, DATA_OP_WAIT_ACK_LAST):
                    ack_sequence = (sequence + 1) & SEQ_MASK
                    ack_frame = build_data_frame(
                        DATA_OP_ACK_READY, ack_sequence, b""
                    )
                    self._send_tpdu(PRIO_ACK, self._tx_can_id, ack_frame)

                if (
                    self._receive_length is not None
                    and len(self._receive_buffer) >= self._receive_length
                ):
                    received_data = bytes(
                        self._receive_buffer[: self._receive_length]
                    )
                    self._receive_buffer.clear()
                    self._receive_length = None
                    self._receive_sequence = None
                    return received_data

    def _do_stop(self) -> None:
        """Stop worker loop and close connection."""
        self._stop_event.set()
        self._do_close()

    def _next_frame(self, timeout: float) -> Optional[tuple]:
        """Get next CAN frame, preferring any already queued frames."""
        try:
            return self._rx_queue.get_nowait()
        except queue.Empty:
            pass
        return self.can_connection.recv_can_frame(timeout=timeout)

    def _format_frame(self, can_id: int, data: bytes) -> str:
        """Return a human-readable description of a received CAN frame."""
        prefix = f"ID 0x{can_id:03X}"

        if not data:
            return f"{prefix}: <empty>"

        # Single-byte control frames
        control_map = {
            OPCODE_CHANNEL_TEST: "CHANNEL_TEST (A3)",
            OPCODE_BREAK: "BREAK (A4)",
            OPCODE_DISCONNECT: "DISCONNECT (A8)",
        }
        if len(data) == 1:
            opcode = data[0]
            name = control_map.get(opcode, None)
            if name:
                return f"{prefix}: {name}"
            return f"{prefix}: single=0x{opcode:02X}"

        try:
            opcode, seq, payload = parse_data_frame(data)
            opcode_names = {
                DATA_OP_WAIT_ACK_MORE: "DATA WAIT_ACK_MORE",
                DATA_OP_WAIT_ACK_LAST: "DATA WAIT_ACK_LAST",
                DATA_OP_NO_ACK_MORE: "DATA NO_ACK_MORE",
                DATA_OP_NO_ACK_LAST: "DATA NO_ACK_LAST",
                DATA_OP_ACK_READY: "ACK READY",
                DATA_OP_ACK_NOT_READY: "ACK NOT_READY",
            }
            opcode_label = opcode_names.get(opcode, f"OP 0x{opcode:X}")
            payload_hex = payload.hex() if payload else "-"
            return f"{prefix}: {opcode_label}, seq={seq}, payload={payload_hex}"
        except Exception:
            return f"{prefix}: raw={data.hex()}"

    def _reset_protocol_state_after_cs_ca(self) -> None:
        """Reset protocol variables after CS/CA exchange per TP2.0_1_1 §5.2 (SN, counters, timers)."""
        self._send_sequence = 0
        self._rc_s = 0
        self._bec = 0
        self._sn_error_count = 0
        self._receive_buffer.clear()
        self._receive_length = None
        self._receive_sequence = None
        self._break_requested = False
        self._last_ct_received = time.time()
        self._rc_ct = 0

    def _reset_state(self) -> None:
        """Reset channel and buffer state."""
        self._channel_setup = False
        self._is_open = False
        self._rx_can_id = None
        self._tx_can_id = None
        self._remote_rx_id = None
        self._remote_tx_id = None
        self._block_size = None
        self._t1 = None
        self._t3 = None
        self._receive_buffer.clear()
        self._receive_length = None
        self._receive_sequence = None
        self._sn_error_count = 0
        self._send_sequence = 0
        self._rc_s = 0
        self._bec = 0
        self._break_requested = False
        self._rc_e = 0
        self._last_ct_received = 0.0
        self._rc_ct = 0
        self._renegotiating = False
        self._clear_queue(self._rx_queue)
        self._keepalive_stop_event.set()
        self._keepalive_thread = None
        self._stop_sender()

    @staticmethod
    def _clear_queue(target_queue: queue.Queue) -> None:
        """Drain all items from a queue without blocking."""
        try:
            while True:
                target_queue.get_nowait()
        except queue.Empty:
            return
    
    def _setup_channel(self) -> None:
        """Setup TP20 channel (TP2.0_1_1 §6.1.1: T_E + TN per attempt, RC_E, MNTC)."""
        self._rc_e = 0
        setup_req = build_setup_request(
            dest=self.dest,
            rx_id=self.preferred_rx_id,
            tx_id=0,
            rx_valid=False,
            tx_valid=True,
        )
        request_can_id = CAN_ID_SETUP_REQUEST
        response_can_id = CAN_ID_SETUP_RESPONSE_BASE + self.dest
        attempt_timeout_s = (T_E_MS + TN_MS) / 1000.0
        import logging
        logger = logging.getLogger()
        while True:
            self.can_connection.send_can_frame(request_can_id, setup_req)
            start_time = time.time()
            while time.time() - start_time < attempt_timeout_s:
                frame = self._next_frame(timeout=0.05)
                if frame is None:
                    continue
                can_id, data = frame
                if can_id != response_can_id:
                    continue
                try:
                    dest, rx_id, tx_id, rx_valid, tx_valid, app_type = parse_setup_response(data)
                    logger.debug(f"Setup response parsed: dest={dest:02X}, rx_id=0x{rx_id:03X}, tx_id=0x{tx_id:03X}, rx_valid={rx_valid}, tx_valid={tx_valid}, app_type={app_type:02X}")
                    self._remote_rx_id = rx_id
                    self._remote_tx_id = tx_id
                    self._tx_can_id = rx_id
                    self._rx_can_id = tx_id
                    self._channel_setup = True
                    self._rc_e = 0
                    logger.info(f"TP20 channel setup: RX CAN ID=0x{self._rx_can_id:03X}, TX CAN ID=0x{self._tx_can_id:03X}")
                    return
                except ValueError as e:
                    if "Negative" in str(e):
                        raise TP20ChannelException(f"Channel setup failed: {e}") from e
                    continue
            self._rc_e += 1
            if self._rc_e > MNTC:
                raise TP20TimeoutException(
                    f"Channel setup timeout after {MNTC + 1} attempts (RC_E > MNTC)"
                )
    
    def _negotiate_parameters(self) -> None:
        """Negotiate channel parameters (TP2.0_1_1 §6.1.1: T_E + TN per attempt, RC_E, MNTC)."""
        if not self._channel_setup:
            raise TP20ChannelException("Channel not set up")
        self._rc_e = 0
        params_req = build_parameters_request(
            block_size=self.block_size,
            t1=self.t1,
            t3=self.t3
        )
        attempt_timeout_s = (T_E_MS + TN_MS) / 1000.0
        while True:
            self._send_tpdu(PRIO_DT_CS_DC, self._tx_can_id, params_req)
            start_time = time.time()
            while time.time() - start_time < attempt_timeout_s:
                frame = self._next_frame(timeout=0.05)
                if frame is None:
                    continue
                can_id, data = frame
                if can_id != self._rx_can_id:
                    continue
                try:
                    block_size, t1, t2, t3, t4 = parse_parameters_response(data)
                except ValueError:
                    continue
                if not BS_MIN <= block_size <= BS_MAX:
                    self._disconnect_channel()
                    raise TP20ChannelException(
                        f"Remote block_size out of range {BS_MIN}..{BS_MAX} (TP2.0_1_1 §5.2)"
                    )
                try:
                    _check_t1_gt_4_t3(t1, t3)  # TP2.0_1_1 §5.2
                except ValueError as e:
                    self._disconnect_channel()
                    raise TP20ChannelException(
                        "Remote parameters violate T1 > 4×T3 (TP2.0_1_1 §5.2)"
                    ) from e
                self._block_size = min(self.block_size, block_size)
                self._t1 = t1
                self._t3 = t3
                self._rc_e = 0
                self._last_ct_received = time.time()
                self._rc_ct = 0
                return
            # Timeout: no valid CA in this attempt (TP2.0_1_1 §6.1.1)
            self._rc_e += 1
            if self._rc_e > MNTC:
                self._disconnect_channel()
                raise TP20TimeoutException(
                    f"Parameters negotiation timeout after {MNTC + 1} attempts (RC_E > MNTC)"
                )

    def renegotiate_parameters(self) -> None:
        """
        Re-exchange CS/CA on an open channel per TP2.0_1_1 §6.3.
        Blocks until exchange is complete; resets SN, counters, and timers.
        Raises if transport is not open or channel not set up.
        """
        if not self._worker_thread:
            raise TP20Exception("Transport worker not running")
        self._submit_command(_CommandType.RENEGOTIATE)

    def _do_renegotiate(self) -> None:
        """Application-initiated CS/CA re-exchange; block sends during exchange (§6.3)."""
        if not self._channel_setup:
            raise TP20ChannelException("Channel not set up")
        self._renegotiating = True
        try:
            params_req = build_parameters_request(
                block_size=self.block_size,
                t1=self.t1,
                t3=self.t3
            )
            attempt_timeout_s = (T_E_MS + TN_MS) / 1000.0
            self._send_tpdu(PRIO_DT_CS_DC, self._tx_can_id, params_req)
            start_time = time.time()
            while time.time() - start_time < attempt_timeout_s:
                frame = self._next_frame(timeout=0.05)
                if frame is None:
                    continue
                can_id, data = frame
                if can_id != self._rx_can_id:
                    continue
                try:
                    block_size, t1, t2, t3, t4 = parse_parameters_response(data)
                except ValueError:
                    continue
                if not BS_MIN <= block_size <= BS_MAX:
                    self._disconnect_channel()
                    raise TP20ChannelException(
                        f"Remote block_size out of range {BS_MIN}..{BS_MAX} (TP2.0_1_1 §5.2)"
                    )
                try:
                    _check_t1_gt_4_t3(t1, t3)
                except ValueError as e:
                    self._disconnect_channel()
                    raise TP20ChannelException(
                        "Remote parameters violate T1 > 4×T3 (TP2.0_1_1 §5.2)"
                    ) from e
                self._block_size = min(self.block_size, block_size)
                self._t1 = t1
                self._t3 = t3
                self._reset_protocol_state_after_cs_ca()
                return
            self._disconnect_channel()
            raise TP20TimeoutException("Parameter renegotiation timeout waiting for CA")
        finally:
            self._renegotiating = False
    
    def _send_segmented(self, payload: bytearray) -> None:
        """Send payload segmented into TP20 data frames."""
        if not self._channel_setup:
            raise TP20DisconnectedException("Channel not set up")
        self._break_requested = False
        sequence = self._send_sequence
        offset = 0
        payload_len = len(payload)
        block_count = 0
        
        while offset < payload_len:
            # Determine how much to send in this packet (max 7 bytes after opcode+seq)
            chunk_size = min(7, payload_len - offset)
            chunk = payload[offset:offset+chunk_size]
            
            # Determine if this is the last packet
            is_last = (offset + chunk_size >= payload_len)
            
            # Determine opcode based on whether we need ACK and if more packets follow
            # For simplicity, we'll request ACK every block_size packets or on last packet
            block_count += 1
            need_ack = (block_count >= self._block_size) or is_last
            
            if need_ack:
                if is_last:
                    opcode = DATA_OP_WAIT_ACK_LAST
                else:
                    opcode = DATA_OP_WAIT_ACK_MORE
            else:
                if is_last:
                    opcode = DATA_OP_NO_ACK_LAST
                else:
                    opcode = DATA_OP_NO_ACK_MORE
            
            # Build and send data frame (§4.2.2 priority 4; T3 applied by sender thread)
            data_frame = build_data_frame(opcode, sequence, chunk)
            self._send_tpdu(PRIO_DT_CS_DC, self._tx_can_id, data_frame)
            
            # Wait for ACK if needed; retry same DT on T1 timeout until RC_S > MNT (TP2.0_1_1 §6.3.1)
            if need_ack:
                while True:
                    try:
                        self._wait_for_ack(sequence)
                        break
                    except TP20AckRetryException:
                        self._send_tpdu(PRIO_DT_CS_DC, self._tx_can_id, data_frame)
            
            # TP2.0_1_1 §6.3.4: if receiver sent BR, end with EOM and discard rest
            if self._break_requested:
                next_seq = (sequence + 1) & SEQ_MASK
                eom_frame = build_data_frame(
                    DATA_OP_WAIT_ACK_LAST, next_seq, b""
                )
                self._send_tpdu(PRIO_DT_CS_DC, self._tx_can_id, eom_frame)
                self._send_sequence = next_seq
                self._break_requested = False
                return
            
            # Update for next packet
            offset += chunk_size
            sequence = (sequence + 1) & SEQ_MASK
            self._send_sequence = sequence  # Update global send sequence
            if need_ack:
                block_count = 0
    
    def _wait_for_ack(self, sequence: int) -> None:
        """Wait for ACK for given sequence number. Uses T1 + TN per TP2.0_1_1."""
        try:
            ack_timeout_s = (TimingParameter.decode(self._t1) + TN_MS) / 1000.0 if self._t1 is not None else self.timeout
        except (ValueError, TypeError):
            ack_timeout_s = self.timeout
        start_time = time.time()
        frames_received = []

        while time.time() - start_time < ack_timeout_s:
            frame = self._next_frame(timeout=0.1)
            if frame is None:
                continue
            
            can_id, data = frame

            if len(data) == 1 and data[0] == OPCODE_CHANNEL_TEST and (can_id == self._rx_can_id or can_id == self._tx_can_id):
                self._last_ct_received = time.time()
                self._rc_ct = 0
                self._send_tpdu(
                    PRIO_CA_CT, self._tx_can_id, build_channel_test(), wait_sent=False
                )
                continue
            if can_id != self._rx_can_id:
                import logging
                logger = logging.getLogger()
                logger.debug(f"Received frame on unexpected CAN ID: 0x{can_id:03X} (expected 0x{self._rx_can_id:03X}), data: {data.hex()}")
                continue
            if len(data) == 1 and data[0] == OPCODE_BREAK:
                # TP2.0_1_1 §6.3.4: receiver requested break; sender must end with EOM
                self._break_requested = True
                return
            frames_received.append((can_id, data))
            try:
                if len(data) == 1 and data[0] == 0xA8:
                    raise TP20DisconnectedException("Received A8")

                opcode, seq, _ = parse_data_frame(data)
                # ACK sequence number is the NEXT sequence number (sequence + 1)
                # So if we sent sequence 0, we expect ACK with sequence 1
                expected_ack_seq = (sequence + 1) & SEQ_MASK
                if opcode in (DATA_OP_ACK_READY, DATA_OP_ACK_NOT_READY) and seq == expected_ack_seq:
                    if opcode == DATA_OP_ACK_NOT_READY:
                        # TP2.0_1_1 §6.3.2: T_Wait, BEC++; close if BEC > MNTB
                        self._bec += 1
                        if self._bec > MNTB:
                            self._disconnect_channel()
                            raise TP20ChannelException(
                                "RNR count exceeded MNTB (BEC); channel closed"
                            )
                        time.sleep(T_WAIT_MS / 1000.0)
                        continue
                    self._rc_s = 0  # TP2.0_1_1: reset on successful ACK
                    self._bec = 0  # §6.3.2: reset on RR
                    return
            except ValueError:
                continue
        
        # T1 timeout (TP2.0_1_1 §6.3.1): resend last DT or close if RC_S > MNT
        import logging
        logger = logging.getLogger()
        formatted_frames = "\n".join(
            self._format_frame(cid, fdata) for cid, fdata in frames_received
        ) or "<none>"
        logger.warning(
            "Timeout waiting for ACK sequence %s. Expected CAN ID: 0x%03X. "
            "Received frames:\n%s",
            sequence,
            self._rx_can_id,
            formatted_frames,
        )
        self._rc_s += 1
        if self._rc_s > MNT:
            self._disconnect_channel()
            raise TP20ChannelException(
                f"ACK timeout count exceeded MNT ({MNT}); channel closed"
            )
        raise TP20AckRetryException("ACK timeout; retry sending last DT")
    
    def _disconnect_channel(self) -> None:
        """Disconnect TP20 channel."""
        if not self._channel_setup:
            return

        disconnect_frame = build_disconnect()
        self._send_tpdu(PRIO_DT_CS_DC, self._tx_can_id, disconnect_frame)
        
        # Wait for disconnect response (optional, but good practice)
        start_time = time.time()
        while time.time() - start_time < 0.5:  # Shorter timeout for disconnect
            frame = self._next_frame(timeout=0.1)
            if frame is None:
                continue
            
            can_id, data = frame
            if can_id == self._rx_can_id and len(data) == 1 and data[0] == 0xA8:
                break  # Got disconnect response
        
        self._channel_setup = False
    
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

