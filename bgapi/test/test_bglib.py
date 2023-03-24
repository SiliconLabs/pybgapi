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
import unittest
from time import sleep

import logging
from testfixtures import log_capture

from bgapi.bglib import BGLib, CommandError, CommandFailedError, BGResponse
from bgapi.apiparser import ParsedApi
from bgapi.serdeser import MSG_COMMAND, MSG_EVENT, HEADER_LENGTH

from .helper import *
from .testconnector import TestConnector

class BGLibTester(unittest.TestCase):

    def setUp(self):
        self.api = ParsedApi(os.path.join(os.path.dirname(__file__), "test.xml"))
        self.conn = TestConnector()
        self.lib = BGLib(self.conn, self.api, log_id="TestLogID")
        self.test = self.lib.test
        self.lib.open()

    def tearDown(self):
        self.lib.close()

    def make_command(self, class_name, command_name, payload):
        cls = self.api[class_name]
        cmd = cls.commands[command_name]
        return make_packet(MSG_COMMAND, self.api.device_id, cls.index, cmd.index, payload)

    def make_event(self, class_name, event_name, payload):
        cls = self.api[class_name]
        evt = cls.events[event_name]
        return make_packet(MSG_EVENT, self.api.device_id, cls.index, evt.index, payload)

    add_step = lambda self, *args, **kwargs: self.conn.add_step(*args, **kwargs)

    def wait(self, time):
        time = float(time)
        self.add_step("@", time)

    def expect_command(self, class_name, command_name, payload):
        self.add_step(">", b"".join(self.make_command(class_name, command_name, payload)))

    def send_response(self, class_name, command_name, payload):
        self.add_step("<", b"".join(self.make_command(class_name, command_name, payload)))

    def send_event(self, class_name, event_name, payload):
        self.add_step("<", b"".join(self.make_event(class_name, event_name, payload)))


class TestCommon(BGLibTester):

    def test_command(self):
        self.expect_command("simple", "returns", "12")
        self.send_response("simple", "returns", "34")

        result = self.lib.test.simple.returns(0x12)
        self.assertEqual(result, (0x34,))

    def test_command_with_success_result(self):
        self.expect_command("simple", "can_fail", "")
        self.send_response("simple", "can_fail", "0000")

        response = self.lib.test.simple.can_fail()
        self.assertEqual(response.result, 0)

    def test_command_no_return(self):
        self.expect_command("simple", "no_return", "12")

        result = self.lib.test.simple.no_return(0x12)
        self.assertEqual(result, None)

    def test_command_complex(self):
        self.expect_command("complex", "multi_type", "125634")
        self.send_response("complex", "multi_type", "abefcd")

        result = self.lib.test.complex.multi_type(0x12, 0x3456)
        self.assertEqual(result, (0xab, 0xcdef))

    def test_command_complex_array(self):
        self.expect_command("complex", "array", "3412025678")
        self.send_response("complex", "array", "cdab02eeff")

        result = self.lib.test.complex.array(0x1234, str2bin("5678"))
        self.assertEqual(result, (0xabcd, str2bin("eeff")))

    def test_event_before_response(self):
        self.expect_command("simple", "returns", "12")
        self.send_event("simple", "no_params", "")
        self.send_response("simple", "returns", "34")

        result = self.lib.test.simple.returns(0x12)
        self.assertEqual(result, (0x34,))
        event = self.lib.get_event()
        self.assertEqual(event.__name__, "NoParams")

    def test_multiple_commands(self):
        self.expect_command("simple", "command_a", "")
        self.send_response("simple", "command_a", "")
        result = self.lib.test.simple.command_a()
        self.assertEqual(result.__name__, "CommandA")

        self.expect_command("simple", "command_b", "")
        self.send_response("simple", "command_b", "")
        result = self.lib.test.simple.command_b()
        self.assertEqual(result.__name__, "CommandB")

    def test_event_generator(self):
        self.send_event("complex", "multi_type_event", "125634")
        self.send_event("simple", "no_params", "")

        eg = self.lib.gen_events(timeout=0.1)

        e = next(eg)
        self.assertEqual(e.__name__, 'MultiTypeEvent')

        e = next(eg)
        self.assertEqual(e.__name__, 'NoParams')

        self.assertRaises(StopIteration, next, eg)

    # Enable debug-level event logs for this test
    @log_capture(level=logging.DEBUG)
    def test_debug_logging(self, l):
        self.expect_command("complex", "multi_type", "010200")
        self.send_response("complex", "multi_type", "020100")
        result = self.lib.test.complex.multi_type(0x01, 0x0002)
        self.send_event("complex", "multi_type_event", "125634")

        event = self.lib.get_event(1.0)

        # Expect log about command, event, and response
        l.check(("bgapi", "DEBUG", "TestLogID > test_cmd_complex_multi_type(param1=1, param2=2)"),
                ("bgapi", "DEBUG", "TestLogID < test_rsp_complex_multi_type(return1=2, return2=1)"),
                ("bgapi", "DEBUG", "TestLogID < test_evt_complex_multi_type_event(value1=18, value2=13398)"))


class TestInvalid(BGLibTester):

    def test_command_no_response(self):
        self.expect_command("simple", "returns", "12")

        self.assertRaises(CommandError, self.lib.test.simple.returns, 0x12)

    def test_command_with_error_result(self):
        self.expect_command("simple", "can_fail", "")
        self.send_response("simple", "can_fail", "3412")

        with self.assertRaisesRegex(CommandFailedError,
                "Command returned 'result' parameter with non-zero errorcode: 0x1234"
                ) as context:
            self.lib.test.simple.can_fail()

        exception = context.exception

        self.assertEqual(exception.errorcode, 0x1234)

        self.assertIsInstance(exception.response, BGResponse)
        self.assertEqual(exception.response.result, 0x1234)

    def test_command_wrong_response(self):
        self.expect_command("simple", "command_a", "")
        self.send_response("simple", "command_b", "")
        self.assertRaises(CommandError, self.lib.test.simple.command_a)

    @log_capture(level=logging.WARNING)
    def test_command_late_response(self, l):
        # Command fails, because no response received in time
        self.expect_command("simple", "command_a", "")
        self.assertRaises(CommandError, self.lib.test.simple.command_a)

        # Send response
        self.send_response("simple", "command_a", "")
        sleep(2 * self.conn.read_timeout) # wait for the response to get processed

        # Expect log about unexpected response
        l.check(("bgapi", "WARNING", "Received unexpected response 'test_rsp_simple_command_a()'"))

        # Send another command and expect to get correct response
        self.expect_command("simple", "command_b", "")
        self.send_response("simple", "command_b", "")
        response = self.lib.test.simple.command_b()
        self.assertEqual(response.__name__, "CommandB")


class TestAPIMismatch(BGLibTester):

    @log_capture(level=logging.WARNING)
    def test_event_with_less_params(self, l):
        self.send_event("complex", "multi_type_event", "12")
        event = self.lib.get_event(1.0)
        self.assertEqual(event.__name__, "MultiTypeEvent")
        self.assertEqual(event, (0x12, None))  # None in place of missing param

        l.check(("bgapi", "WARNING", "Received message 'test_evt_complex_multi_type_event' with parameter(s) 'value2' missing."))

    @log_capture(level=logging.WARNING)
    def test_event_with_more_params(self, l):
        self.send_event("complex", "multi_type_event", "12563478")
        event = self.lib.get_event(1.0)
        self.assertEqual(event.__name__, "MultiTypeEvent")
        self.assertEqual(event, (0x12, 0x3456))  # Extra param is ignored

        l.check(("bgapi", "WARNING", "Received message 'test_evt_complex_multi_type_event' with 1 byte(s) extra payload."))


class TestSplittedRead(BGLibTester):

    def test_splitted_header(self):
        header, payload = self.make_event("simple", "no_params", "")

        self.add_step("<", header[:len(header) // 2]) # send first part of the header
        self.wait(self.conn.read_timeout + 0.1)
        self.add_step("<", header[len(header) // 2:]) # send reset of the header

        event = self.lib.get_event(1.0)
        self.assertEqual(event.__name__, "NoParams")
        self.assertEqual(len(event), 0)

    def test_splitted_packet(self):
        header, payload = self.make_event("simple", "single_uint8", "12")

        self.add_step("<", header) # send header
        self.wait(2 * self.conn.read_timeout)
        self.add_step("<", payload) # send payload

        event = self.lib.get_event(1.0)
        self.assertEqual(event.__name__, "SingleUint8")
        self.assertEqual(event, (0x12,))

    def test_splitted_payload(self):
        header, payload = self.make_event("simple", "double_uint8", "1234")

        self.add_step("<", header + payload[:len(payload) // 2]) # send first part of the packet
        self.wait(2 * self.conn.read_timeout)
        self.add_step("<", payload[len(payload) // 2:]) # send first part of the packet

        event = self.lib.get_event(2.0)
        self.assertEqual(event.__name__, "DoubleUint8")
        self.assertEqual(event, (0x12, 0x34))


class TestOpenClose(BGLibTester):

    def test_close_while_reading_header(self):
        header, payload = self.make_event("simple", "no_params", "")

        self.add_step("<", header[:len(header) // 2])
        self.lib.close()

    def test_close_while_reading_payload(self):
        header, payload = self.make_event("simple", "double_uint8", "1234")

        self.add_step("<", header + payload[:len(payload) // 2])
        self.lib.close()

class TestKeepDeviceAwake(BGLibTester):

    def setUp(self):
        super(TestKeepDeviceAwake, self).setUp()
        self.keep_awake = None
        self.keep_awake_history = []
        self.lib.set_keep_device_awake_function(self.keep_awake_func)

    def keep_awake_func(self, keep_awake):
        self.keep_awake = keep_awake
        self.keep_awake_history.append(keep_awake)

    def test_device_is_not_kept_awake_after_connector_is_opened(self):
        self.lib.close()
        self.keep_awake = 1
        self.lib.open()

        self.assertEqual(self.keep_awake, 0)

    def test_keep_device_awake_when_sending_command(self):
        self.expect_command("simple", "command_a", "")
        self.send_response("simple", "command_a", "")
        self.lib.test.simple.command_a()

        self.assertEqual(self.keep_awake_history, [1, 0])

    def test_device_is_kept_awake_if_command_has_no_response(self):
        self.expect_command("simple", "no_return", "00")
        self.lib.test.simple.no_return(0)

        self.assertEqual(self.keep_awake, 1)

    def test_device_is_not_kept_awake_if_command_fails_to_respond(self):
        self.expect_command("simple", "command_a", "")
        self.assertRaises(CommandError, self.lib.test.simple.command_a)

        self.assertEqual(self.keep_awake, 0)

class TestWithoutLogId(BGLibTester):

    # This class is here to test that missing the optional parameter log_id doesn't break anything.
    def setUp(self):
        self.api = ParsedApi(os.path.join(os.path.dirname(__file__), "test.xml"))
        self.conn = TestConnector()
        self.lib = BGLib(self.conn, self.api)
        self.test = self.lib.test
        self.lib.open()

    @log_capture(level=logging.DEBUG)
    def test_logging_without_log_id(self, l):
        self.expect_command("complex", "multi_type", "010200")
        self.send_response("complex", "multi_type", "020100")
        result = self.lib.test.complex.multi_type(0x01, 0x0002)
        self.send_event("complex", "multi_type_event", "125634")

        event = self.lib.get_event(1.0)
        log_text = str(l).splitlines()
        # If no log_id parameter is given to BGLib, id() will be used, so it'll be a random integer.
        self.assertEqual(log_text[0], "bgapi DEBUG")
        self.assertRegex(log_text[1], '[0-9]+ > test_cmd_complex_multi_type\(param1=1, param2=2\)')
        self.assertEqual(log_text[2], "bgapi DEBUG")
        self.assertRegex(log_text[3], '[0-9]+ < test_rsp_complex_multi_type\(return1=2, return2=1\)')
        self.assertEqual(log_text[4], "bgapi DEBUG")
        self.assertRegex(log_text[5], '[0-9]+ < test_evt_complex_multi_type_event\(value1=18, value2=13398\)')

if __name__ == "__main__":
    unittest.main()
