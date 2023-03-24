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

import time
from collections import deque
from threading import Lock, Event

from bgapi.connector import Connector

def sleep(seconds):
    if seconds > 0:
        time.sleep(seconds)


class TestConnectorException(Exception): pass


class TestConnector(Connector):

    ACTIONS = ["<", ">", "@"]

    def __init__(self):
        self.read_timeout = 0.0

        self.steps = deque()
        self.get_step_lock = Lock()
        self.new_step = Event()
        self.got_step = Event()

        super(TestConnector, self).__init__()

    def open(self):
        return

    def close(self):
        return

    def write(self, data):
        while data:
            self._process_wait()

            write_step = self._get_step(">")
            if not write_step:
                raise TestConnectorException("Unexpected write %r" % data)

            verify_data = write_step[1]
            # If not enough data received, put rest of the verify_data back to the queue
            if len(data) < len(verify_data):
                self.steps.appendleft((">", verify_data[len(data):]))

            for i, (byte, verify_byte) in enumerate(zip(data, verify_data), start=1):
                if byte != verify_byte:
                    raise TestConnectorException("Invalid write: %r != %r" % (data[:i], verify_data[:i]))

            # If too much data received, reiterate with rest of the data
            data = data[len(verify_data):]

        self._process_wait() # Do for next step also

    def read(self, size=1):
        start_time = time.time()
        retval = b""

        timeout_left = lambda: self.read_timeout - (time.time() - start_time)

        while size:
            wait = self._process_wait()
            if wait:
                if wait > timeout_left():
                    sleep(timeout_left())
                    break
                sleep(wait)
                continue

            # Wait for read step           
            read_step = self._get_step(action="<", timeout=timeout_left())
            if not read_step: break

            read_data = read_step[1]
            # If not enough data requested, put rest of the read_data back to the queue
            if size < len(read_data):
                self.steps.appendleft(("<", read_data[size:]))
                read_data = read_data[:size]

            retval += read_data
            size -= len(read_data)

        self._process_wait() # Do for next step also

        return retval

    def set_read_timeout(self, timeout):
        self.read_timeout = timeout

    def set_write_timeout(self, timeout):
        pass

    def _process_wait(self):
        time_to_wait = 0.0

        wait_step = self._get_step("@")
        if wait_step:
            wait_arg = wait_step[1]
            try:
                (wait_time, started) = wait_arg
                # Wait already started
                waited = time.time() - started
                if waited < wait_time:
                    # Wait some more
                    self.steps.appendleft(("@", (wait_time - waited, time.time())))
                    time_to_wait = wait_time - waited
                else:
                    # Waited enough
                    pass
            except TypeError:
                # Start wait
                self.steps.appendleft(("@", (wait_arg, time.time())))
                time_to_wait = wait_arg

        return time_to_wait

    def _get_step(self, action=None, timeout=0.0):
        start_time = time.time()
        timeout_left = lambda: timeout - (time.time() - start_time)

        while True:
            try:
                self.get_step_lock.acquire()
                next_step = self.steps.popleft()
                next_action = next_step[0]

                if action == None or next_action == action:
                    self.get_step_lock.release()
                    self.got_step.set()
                    return next_step

                # Put the step back to the queue
                self.steps.appendleft(next_step)
                self.get_step_lock.release()

                # Wait for someone to get the action out of the queue
                self.got_step.clear()
                self.got_step.wait(timeout_left())
                self.got_step.clear()

            except IndexError:
                self.get_step_lock.release()
                # Wait for new step to arrive
                self.new_step.clear()
                self.new_step.wait(timeout_left())
                self.new_step.clear()

            if timeout != None and timeout_left() <= 0:
                break

    def add_step(self, action, arg):
        if action not in self.ACTIONS:
            raise ValueError("Invalid action '%s'" % action)
        self.steps.append((action, arg))
        self.new_step.set()

    def add_step_str(self, *steps):
        for step in steps:
            (action, arg) = step.split(":", 1)

            if action == "@":
                arg = float(arg)

            self.add_step(action, arg)
