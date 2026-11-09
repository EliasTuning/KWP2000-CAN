"""
Tests for the KWP2000-STAR DCAN serial transport (K+DCAN cable in D-CAN mode).

* close() releases the serial port.
* Bytes already waiting in the input buffer when a request is sent (a late reply
  to an earlier, timed-out request) are discarded, so wait_frame() returns the
  reply to THIS request. Seen on a BMW E90: without it, an earlier reply was
  read back for roughly a third of requests.

The first tests use an in-memory fake of serial.Serial; the last one runs the real
pyserial against a pseudo-terminal with a simulated ECU on the other end (POSIX only).
"""
import os
import sys
import threading
import time

import pytest

from kwp2000_can.interface.serial import comport_transport
from kwp2000_can.protocols.can.kwp200_star_dcan.transport import Kwp2000StarDcan

TESTER, ECU = 0xF1, 0x12


def response_frame(payload: bytes, ecu: int = ECU, tester: int = TESTER) -> bytes:
    """Short-format frame as the cable delivers it: [0x80|len, tester, ecu, payload..., sum]."""
    frame = bytes([0x80 | len(payload), tester, ecu]) + payload
    return frame + bytes([sum(frame) & 0xFF])


class FakeSerial:
    """In-memory stand-in for serial.Serial: echoes each write, then queues the scripted reply."""

    instances = []

    def __init__(self, **kwargs):
        self.port = kwargs.get('port')
        self.timeout = kwargs.get('timeout')
        self.is_open = True
        self.input = bytearray()
        self.replies = []
        self.written = []
        self.input_resets = 0
        FakeSerial.instances.append(self)

    def write(self, data):
        self.written.append(bytes(data))
        self.input += data                                   # the D-CAN line echo
        if self.replies:
            self.input += self.replies.pop(0)
        return len(data)

    def read(self, n):
        out, self.input[:] = bytes(self.input[:n]), self.input[n:]
        return out

    def flush(self):
        pass

    def reset_input_buffer(self):
        self.input_resets += 1
        self.input.clear()

    def close(self):
        self.is_open = False


@pytest.fixture
def fake_serial(monkeypatch):
    FakeSerial.instances = []
    monkeypatch.setattr(comport_transport.serial, 'Serial', FakeSerial)
    return FakeSerial


def test_close_releases_the_serial_port(fake_serial):
    transport = Kwp2000StarDcan(port='/dev/fake', target=ECU, source=TESTER)
    with transport:
        port = fake_serial.instances[-1]
        assert port.is_open
    assert not port.is_open


def test_reopen_after_close(fake_serial):
    transport = Kwp2000StarDcan(port='/dev/fake', target=ECU, source=TESTER)
    transport.open()
    transport.close()
    transport.open()
    assert fake_serial.instances[-1].is_open
    transport.close()


def test_stale_reply_is_discarded_before_a_request(fake_serial):
    with Kwp2000StarDcan(port='/dev/fake', target=ECU, source=TESTER) as transport:
        port = fake_serial.instances[-1]
        port.input += response_frame(bytes([0x61, 0x01, 0xAA]))     # late reply to an earlier request
        port.replies.append(response_frame(bytes([0x62, 0x40, 0x22, 0x0B])))
        transport.send(bytes([0x22, 0x40, 0x22]))
        assert transport.wait_frame(timeout=0.1) == bytes([0x62, 0x40, 0x22, 0x0B])
        assert port.input_resets == 1


def test_clearing_can_be_turned_off(fake_serial):
    with Kwp2000StarDcan(port='/dev/fake', target=ECU, source=TESTER, clear_input_before_send=False) as transport:
        port = fake_serial.instances[-1]
        port.replies.append(response_frame(bytes([0x50, 0x03])))
        transport.send(bytes([0x10, 0x03]))
        assert transport.wait_frame(timeout=0.1) == bytes([0x50, 0x03])
        assert port.input_resets == 0


def test_target_can_change_between_requests_on_one_open_port(fake_serial):
    """One open port, several ECUs: target is read at send/receive time."""
    with Kwp2000StarDcan(port='/dev/fake', target=ECU, source=TESTER) as transport:
        port = fake_serial.instances[-1]
        for ecu in (0x12, 0x29, 0x60):
            transport.target = ecu
            port.replies.append(response_frame(bytes([0x5A, ecu]), ecu=ecu))
            transport.send(bytes([0x1A, 0x80]))
            assert transport.wait_frame(timeout=0.1) == bytes([0x5A, ecu])
        assert len(fake_serial.instances) == 1


@pytest.mark.skipif(not sys.platform.startswith(('linux', 'darwin')), reason='needs a POSIX pseudo-terminal')
def test_stale_reply_discarded_with_real_pyserial_on_a_pty():
    import pty
    import termios
    import tty

    master, slave = pty.openpty()
    tty.setraw(slave)
    attrs = termios.tcgetattr(slave)
    attrs[3] &= ~termios.ECHO
    termios.tcsetattr(slave, termios.TCSANOW, attrs)
    request = bytes([0x22, 0x40, 0x22])
    request_frame = bytes([0x80 | len(request), ECU, TESTER]) + request
    request_frame += bytes([sum(request_frame) & 0xFF])
    stop = threading.Event()

    def ecu():
        """Simulated cable + ECU: echo the request frame, then answer it."""
        got = b''
        while not stop.is_set() and len(got) < len(request_frame):
            try:
                got += os.read(master, 64)
            except OSError:
                return
        if got == request_frame:
            os.write(master, got + response_frame(bytes([0x62, 0x40, 0x22, 0x0B])))

    try:
        with Kwp2000StarDcan(port=os.ttyname(slave), target=ECU, source=TESTER, timeout=1.0) as transport:
            # a late reply to an earlier request arrives while the port is open (pyserial's open() already
            # flushes whatever came before it)
            os.write(master, response_frame(bytes([0x61, 0x01, 0xAA])))
            time.sleep(0.05)
            worker = threading.Thread(target=ecu, daemon=True)
            worker.start()
            transport.send(request)
            assert transport.wait_frame(timeout=1.0) == bytes([0x62, 0x40, 0x22, 0x0B])
        worker.join(2)
    finally:
        stop.set()
        os.close(master)
        os.close(slave)
