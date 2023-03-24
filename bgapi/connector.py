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

class Connector(object):
    """
    Connector class abstracts data transmission between arbitrary end-points, like
    serial-ports or TCP/IP-sockets.
    """

    def open(self):
        """
        Open connector. Raises ConnectorException on failure.
        """
        raise NotImplementedError()

    def close(self):
        """
        Close connector. Shouldn't fail.
        """
        raise NotImplementedError()

    def write(self, data):
        """
        Write data to connector.
        """
        raise NotImplementedError()

    def read(self, size=1):
        """
        Read data from connector. Read blocks until received size number of bytes.
        """
        raise NotImplementedError()

    def set_read_timeout(self, timeout):
        """
        Sets the timeout in seconds for read operations.
        """
        raise NotImplementedError()

    def set_write_timeout(self, timeout):
        """
        Sets the timeout in seconds for write operations.
        """
        raise NotImplementedError()


class ConnectorException(Exception):
    """ Base class for connector related exceptions. """

class ConnectorTimeoutException(ConnectorException):
    """ Timeouts give this exception. """
