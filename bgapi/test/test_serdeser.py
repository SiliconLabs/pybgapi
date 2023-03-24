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

import os
import struct
import unittest

from bgapi.apiparser import ParsedApi
from bgapi.serdeser import Serializer, Deserializer, MSG_COMMAND, MSG_EVENT, HEADER_LENGTH

from .helper import *

class TestTypes(unittest.TestCase):

    def setUp(self):
        self.api = ParsedApi(os.path.join(os.path.dirname(__file__), "test.xml"))
        self.ser = Serializer([self.api])
        self.deser = Deserializer([self.api])

    def verify(self, msg, string):
        self.assertEqual(bin2str(msg), string)

    def verify_payload(self, msg, string):
        self.assertEqual(bin2str(msg[HEADER_LENGTH:]), string)

    def ser_command(self, class_name, command_name, *params):
        return self.ser.command(self.api.device_id, class_name, command_name, params)

    def deser_response(self, class_name, command_name, payload):
        payload = str2bin(payload)
        class_id = self.api[class_name].index
        command_id = self.api[class_name].commands[command_name].index
        header = make_header(MSG_COMMAND, self.api.device_id, class_id, command_id, len(payload))
        return self.deser.parse(header, payload, fromHost=False)

    def ser_type_test(self, type, value, result):
        cmd = self.ser_command("types", type, value)
        self.verify_payload(cmd, result)

    def deser_type_test(self, type, value, binary):
        (cmdevt, hfields, params) = self.deser_response("types", type, binary)
        self.assertEqual(params[0], value)

    def type_test(self, type, value, binary):
        self.ser_type_test(type, value, binary)
        self.deser_type_test(type, value, binary)

    # Actual tests start from here

    def test_int8(self):
        self.type_test("int8", -1, b"ff")
        self.type_test("int8", 127, b"7f")
        self.type_test("int8", -128, b"80")

    def test_uint8(self):
        self.type_test("uint8", 0x12, b"12")

    def test_int16(self):
        self.type_test("int16", -1, b"ffff")
        self.type_test("int16", 32767, b"ff7f")
        self.type_test("int16", -32768, b"0080")

    def test_uint16(self):
        self.type_test("uint16", 0x1234, b"3412")

    def test_int32(self):
        self.type_test("int32", -2147483648, b"00000080")
        self.type_test("int32", -305419896, b"88a9cbed")
        self.type_test("int32", -1, b"ffffffff")
        self.type_test("int32", 0, b"00000000")
        self.type_test("int32", 1, b"01000000")
        self.type_test("int32", 305419896, b"78563412")
        self.type_test("int32", 2147483647, b"ffffff7f")

    def test_uint32(self):
        self.type_test("uint32", 0x12345678, b"78563412")

    def test_int64(self):
        self.type_test("int64", -9223372036854775808, b"0000000000000080")
        self.type_test("int64", -1, b"ffffffffffffffff")
        self.type_test("int64", 0, b"0000000000000000")
        self.type_test("int64", 1, b"0100000000000000")
        self.type_test("int64", 81985529216486895, b"efcdab8967452301")
        self.type_test("int64", 9223372036854775807, b"ffffffffffffff7f")

    def test_uint64(self):
        self.type_test("uint64", 0x0123456789abcdef, b"efcdab8967452301")

    def test_uint8array(self):
        self.type_test("uint8array", str2bin(hexstring(0)), b"00" + hexstring(0))
        self.type_test("uint8array", str2bin(hexstring(5)), b"05" + hexstring(5))
        self.type_test("uint8array", str2bin(hexstring(255)), b"ff" + hexstring(255))

    def test_uint16array(self):
        self.type_test("uint16array", str2bin(hexstring(0)), b"0000" + hexstring(0))
        self.type_test("uint16array", str2bin(hexstring(5)), b"0500" + hexstring(5))
        self.type_test("uint16array", str2bin(hexstring(255)), b"ff00" + hexstring(255))
        self.type_test("uint16array", str2bin(hexstring(256)), b"0001" + hexstring(256))
        # Test maximum size of an array allowed by BGAPI packet format
        self.type_test("uint16array", str2bin(hexstring(2045)), b"fd07" + hexstring(2045))

    def test_bd_addr(self):
        self.type_test("bd_addr", "12:34:56:78:90:ab", b"ab9078563412")

    def test_hw_addr(self):
        self.type_test("hw_addr", "12:34:56:78:90:ab", b"1234567890ab")

    def test_ipv4(self):
        self.type_test("ipv4", "18.52.86.120", b"12345678")

    def test_uuid_128(self):
        self.type_test("uuid_128", b"Pepe the Frog 88", b"50657065207468652046726f67203838")

    def test_aes_key_128(self):
        self.type_test("aes_key_128", b"\x00\x01\x02\x03\x04\x05\x06\x07\x00\x01\x02\x03\x04\x05\x06\x07", b"00010203040506070001020304050607")

    def test_uuid_64(self):
        self.type_test("sl_bt_uuid_64_t", b"Harambe!", b"486172616d626521")

    def test_uuid_16(self):
        self.type_test("sl_bt_uuid_16_t", b"\x01\x02", b"0102")

    def test_byte_array(self):
        self.type_test("five_bytes_array", b'\x01\x02\x03\x04\x05', b"0102030405")
        self.type_test("ten_bytes_array", b'\x05\x06\x07\x00\x01\x02\x03\x04\x05\x06', b"05060700010203040506")

if __name__ == "__main__":
    unittest.main()
