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

import unittest
from bgapi.robustconnector import RobustConnector, PREAMBLE_BYTE
from .testconnector import TestConnector

PREAMBLE = bytes([PREAMBLE_BYTE])

class RobustTester(unittest.TestCase):

    READ_TIMEOUT = 0.1
    WRITE_TIMEOUT = 1.0

    def setUp(self):
        self.conn = TestConnector()
        self.robust = RobustConnector(self.conn)
        self.robust.open()
        self.robust.set_read_timeout(self.READ_TIMEOUT)
        self.robust.set_write_timeout(self.WRITE_TIMEOUT)

    def tearDown(self):
        self.robust.close()

    def test_write(self):
        self.conn.add_step(">", PREAMBLE + b"\x05\x1bhello\x92")
        self.conn.add_step(">", PREAMBLE + b"\x05\x1bworld\xb3")
        self.robust.write(b"hello")
        self.robust.write(b"world")

    def test_write_long(self):
        self.conn.add_step(">", PREAMBLE + b"\x00\x50" + b"x" * 512 + b"\xd1")
        self.robust.write(b"x" * 512)

    def test_no_crc(self):
        self.conn.add_step(">", PREAMBLE + b"\x05\x0chello")
        self.conn.add_step(">", PREAMBLE + b"\x05\x0cworld")
        self.robust.crc = False
        self.robust.write(b"hello")
        self.robust.write(b"world")

    def test_read(self):
        self.conn.add_step("<", PREAMBLE + b"\x05\x1bhello\x92")
        self.conn.add_step("<", PREAMBLE + b"\x05\x1bworld\xb3")
        hello = self.robust.read(5)
        world = self.robust.read(5)
        self.assertEqual(hello, b"hello")
        self.assertEqual(world, b"world")

    def test_read_long(self):
        self.conn.add_step("<", PREAMBLE + b"\x00\x50" + b"x" * 512 + b"\xd1")
        x = self.robust.read(512)
        self.assertEqual(x, b"x" * 512)

    def test_read_multi_steps(self):
        self.conn.add_step("<", PREAMBLE + b"\x05\x1bhello\x92")
        hello = self.robust.read(2)
        hello += self.robust.read(2)
        hello += self.robust.read(2)
        self.assertEqual(hello, b"hello")

    def test_invalid_crc(self):
        self.conn.add_step("<", PREAMBLE + b"\x05\x1bhello\xff")
        self.conn.add_step("<", PREAMBLE + b"\x05\x1bworld\xb3")
        world = self.robust.read(5)
        # Message with invalid CRC is dropped
        self.assertEqual(world, b"world")

    def test_invalid_headers(self):
        self.conn.add_step("<", b"\xff")
        self.conn.add_step("<", PREAMBLE + b"\x05\x1bhello\x92")
        self.conn.add_step("<", b"\xfe")
        self.conn.add_step("<", PREAMBLE + b"\x05\x1bworld\xb3")
        self.conn.add_step("<", PREAMBLE)
        self.conn.add_step("<", PREAMBLE + b"\x05\x1bhello\x92")
        self.conn.add_step("<", PREAMBLE + b"\xff")
        self.conn.add_step("<", PREAMBLE + b"\x05\x1bworld\xb3")
        self.conn.add_step("<", PREAMBLE + b"\xfe")
        self.conn.add_step("<", PREAMBLE + b"\x05\x1bhello\x92")
        self.conn.add_step("<", PREAMBLE * 3)
        self.conn.add_step("<", PREAMBLE + b"\x05\x1bworld\xb3")
        self.conn.add_step("<", PREAMBLE * 2 + b"\xff")
        self.conn.add_step("<", PREAMBLE + b"\x05\x1bhello\x92")
        self.conn.add_step("<", PREAMBLE * 2 + b"\xfe")
        self.conn.add_step("<", PREAMBLE + b"\x05\x1bworld\xb3")
        self.conn.add_step("<", PREAMBLE + b"\xfe\xff")
        self.conn.add_step("<", PREAMBLE + b"\x05\x1bhello\x92")
        self.conn.add_step("<", PREAMBLE + b"\xff\xfe")
        self.conn.add_step("<", PREAMBLE + b"\x05\x1bworld\xb3")
        self.conn.add_step("<", PREAMBLE + b"\xfe\xfe")
        self.conn.add_step("<", PREAMBLE + b"\x05\x1bhello\x92")
        self.conn.add_step("<", PREAMBLE + b"\xff\xff")
        self.conn.add_step("<", PREAMBLE + b"\x05\x1bworld\xb3")
        message = self.robust.read(60)
        self.assertEqual(message, b"helloworld" * 6)

if __name__ == "__main__":
    unittest.main()
