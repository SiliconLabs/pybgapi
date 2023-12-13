# Copyright 2023 Silicon Laboratories Inc. www.silabs.com
#
# SPDX-License-Identifier: Zlib
#
# The licensor of this software is Silicon Laboratories Inc.
#
# This software is provided 'as-is', without any express or implied
# warranty. In no event will the authors be held liable for any damages
# arising from the use of this software.
#
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
#
# 1. The origin of this software must not be misrepresented; you must not
#    claim that you wrote the original software. If you use this software
#    in a product, an acknowledgment in the product documentation would be
#    appreciated but is not required.
# 2. Altered source versions must be plainly marked as such, and must not be
#    misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.

"""
This connector adds an extra layer between the BGAPI and the connector
to provide reliable communication by guaranteeing data integrity.
A reliable packet consists of the 3 byte header, the (BGAPI) payload,
and the optional 1 byte CRC.
"""

import queue
import threading
from .connector import Connector, ConnectorException

PREAMBLE_BYTE = 0x5A
HEADER_SIZE = 3
MAX_PAYLOAD_LENGTH = 2047
CRC_PRESENT_FLAG = 0b00010000
PAYLOAD_LENGTH_MASK = 0b11100000

def pack(data, crc=True):
    """
    Prepend header and append optional CRC to the input data.
    """
    if len(data) > MAX_PAYLOAD_LENGTH:
        raise ConnectorException()

    packed_data = bytearray()

    # Constructing the header (3 bytes)
    packed_data.append(PREAMBLE_BYTE) # Preamble byte (1 byte)
    packed_data.append(len(data) & 0xFF) # Payload length (11 bit)
    packed_data.append((len(data) >> 3) & PAYLOAD_LENGTH_MASK)
    if crc:
        packed_data[2] |= CRC_PRESENT_FLAG # Set payload crc flag (1 bit)
    packed_data[2] |= crc4(packed_data[1:], 3) # Header CRC-4 (4 bit), excluding preamble

    # Add payload
    packed_data.extend(data)

    # Payload CRC-8 (1 byte)
    if crc:
        packed_data.append(crc8(data))

    return packed_data

def crc4(data, nibbles):
    """
    Calculate CRC-4 checksum using the x^4 + x + 1 polynomial.
    """
    table = [0x0, 0x7, 0xe, 0x9, 0x5, 0x2, 0xb, 0xc, 0xa, 0xd, 0x4, 0x3, 0xf, 0x8, 0x1, 0x6]
    crc = 0xa # CRC value of the preamble 0x5A
    for i in range(nibbles):
        shift = 4 if i % 2 == 0 else 0
        nibble = (data[i // 2] >> shift) & 0x0F
        crc = table[crc ^ nibble]
    return crc

def crc8(data):
    """
    Calculate CRC-8 checksum using the x^8 + x^2 + x + 1 polynomial.
    """
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc ^= 0x1070 << 3
            crc <<= 1
    return (crc >> 8) & 0xFF

class RobustConnector(Connector):
    """
    Provide extra robust layer above regular connectors.
    """

    def __init__(self, connector: Connector, crc=True):
        super().__init__()
        self.conn = connector
        self.crc = crc
        self.read_buffer = bytearray()
        self.read_queue = queue.Queue()
        self.read_timeout = None
        self.thread = None
        self.stop_flag = threading.Event()

    def open(self):
        """
        Open connector.
        """
        if self.thread is None:
            self.conn.open()
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def close(self):
        """
        Close connector.
        """
        if self.thread is not None:
            self._stop()
            self.conn.close()
            self.thread = None

    def write(self, data):
        """
        Write data to connector. Data must be a complete packet.
        """
        self.conn.write(pack(data, self.crc))

    def read(self, size=1):
        """
        Read data from connector. Read blocks until received size number of bytes.
        """
        while len(self.read_buffer) < size:
            try:
                self.read_buffer.extend(self.read_queue.get(timeout=self.read_timeout))
            except queue.Empty:
                break
        # Return at most size number of bytes, or the available bytes in the buffer
        read_size = min(len(self.read_buffer), size)
        data = bytes(self.read_buffer[:read_size])
        self.read_buffer = self.read_buffer[read_size:]
        return data

    def set_read_timeout(self, timeout):
        """
        Set the timeout in seconds for read operations.
        """
        self.read_timeout = timeout
        self.conn.set_read_timeout(timeout)

    def set_write_timeout(self, timeout):
        """
        Set the timeout in seconds for write operations.
        """
        self.conn.set_write_timeout(timeout)

    def _read(self, size=1):
        """
        Read from connector until requested data is available.
        """
        data = bytearray()
        while len(data) < size:
            if self.stop_flag.is_set():
                return None
            data.extend(self.conn.read(size - len(data)))
        return bytes(data)

    def _run(self):
        """
        Receive and unpack robust packets.
        """
        header = bytearray()
        while not self.stop_flag.is_set():
            # Get the missing part of the header
            data = self._read(HEADER_SIZE - len(header))
            if data is None:
                # Stop flag set while reading header
                continue
            header.extend(data)
            # Find the start of the packet
            preamble = header.find(PREAMBLE_BYTE)
            if preamble < 0:
                # Preamble not found, clear header
                header = bytearray()
                continue
            if preamble > 0:
                # Preamble found on an incorrect position
                header = header[preamble:]
                continue
            if crc4(header[1:], 4) != 0:
                # Check if the rest of the header contains preamble byte
                header = header[1:]
                continue
            # Get info from the header
            payload_size = header[1] | ((header[2] & PAYLOAD_LENGTH_MASK) << 3)
            crc_req = bool(header[2] & CRC_PRESENT_FLAG)
            # Clear header
            header = bytearray()
            # Get the packet payload
            payload = self._read(payload_size)
            if payload is None:
                # Stop flag set while reading payload
                continue
            if crc_req:
                crc = self._read(1)
                if crc is None:
                    # Stop flag set while reading CRC
                    continue
                if crc[0] != crc8(payload):
                    # Invalid packet CRC, drop packet
                    continue
            self.read_queue.put(payload)

    def _stop(self):
        self.stop_flag.set()
        self.thread.join()
