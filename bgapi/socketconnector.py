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

import socket
import warnings

from .connector import *


class SocketConnector(Connector):
    """Connector for TCP/IP or Unix domain socket connections

    The address format depends on the selected address family. See the
    socket module documentation in the Python standard library for more
    details about supported address families. The family parameter supports
    constants from the socket module, e.g. socket.AF_INET, or the family
    name may be passed as a string, which is converted to the correct type.

    For TCP/IP connections, the address is a tuple (host, port).
    Example:
        >>> SocketConnector(('127.0.0.1', 1234))
        >>> SocketConnector(('127.0.0.1', 1234), family='inet')
        >>> SocketConnector(('::1', 1234), family='inet6')

    For Unix domain socket connections, the address is a local filesystem
    path.
    Example:
        >>> SocketConnector('/path/to/bgapi.sock', family='unix')

    NOTE: The port parameter is deprecated and should not be used anymore!
    """

    def __init__(self, address, port=None, family=socket.AF_INET):
        if isinstance(family, str):
            try:
                family = 'AF_' + family.upper()
                family = getattr(socket, family)
            except AttributeError:
                raise ValueError("Unknown address family '{}'".format(family))
        self.family = family

        if port is None:
            self.address = address
        else:
            warnings.warn(
                    "The 'port' parameter is deprecated, use 'address' in a "
                    "(host, port) format instead.",
                    DeprecationWarning)
            self.address = (address, int(port))

        self.s = None

    def open(self):
        if self.s:
            return
        self.s = socket.socket(self.family, socket.SOCK_STREAM)
        try:
            self.s.connect(self.address)
        except Exception as e:
            raise ConnectorException(e.message)

    def close(self):
        if not self.s:
            return
        self.s.close()
        self.s = None

    def write(self, data):
        try:
            self.s.send(data)
        except socket.timeout as e:
            raise ConnectorException(e.message)

    def read(self, size=1):
        try:
            return self.s.recv(size)
        except socket.timeout:
            # When a recv returns 0 bytes, it means the other side has closed (or is in the process of closing) the connection.
            # Current implementation doesn't differentiate this situation from regular timeout.
            return ""

    def set_read_timeout(self, timeout):
        self.s.settimeout(timeout)

    def set_write_timeout(self, timeout):
        # socket doesn't have separate write timeout
        pass
