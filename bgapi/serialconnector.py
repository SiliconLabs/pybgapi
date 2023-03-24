# Copyright 2021 Silicon Laboratories Inc. www.silabs.com
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

import serial
from .connector import *


class SerialConnector(Connector):

    def __init__(self, port, baudrate=115200, rtscts=False):
        self.s = serial.Serial(baudrate=baudrate, rtscts=rtscts)
        self.s.port = port # port given separately to prevent automatic opening

        super(SerialConnector, self).__init__()

    def open(self):
        try:
            self.s.open()
        except serial.SerialException as e:
            raise ConnectorException(e)

    def close(self):
        # Temporarily disable RTS/CTS because in some cases, closing the serial
        # port takes 30 seconds to complete if handshaking is enabled, at least
        # with Linux and FT232 USB to serial adapters.
        rtscts = self.s.rtscts
        self.s.rtscts = False
        try:
            self.s.close()
        finally:
            self.s.rtscts = rtscts

    def write(self, data):
        try:
            self.s.write(data)
        except ValueError as e:
            raise ConnectorException(e)
        except serial.SerialTimeoutException as e:
            raise ConnectorTimeoutException(e)

    def read(self, size=1):
        try:
            return self.s.read(size)
        except ValueError as e:
            raise ConnectorException(e)

    def set_read_timeout(self, timeout):
        self.s.timeout = timeout

    def set_write_timeout(self, timeout):
        self.s.writeTimeout = timeout
