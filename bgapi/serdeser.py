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

"""
Takes care of serializing and deserializing of api commands and events
"""

import binascii
import struct
import logging
import operator

from .apiparser import toInt


logger = logging.getLogger(__package__)

MSG_COMMAND = 0
MSG_EVENT = 1

HEADER_LENGTH = 4


def to_bytes(s):
    if isinstance(s, bytes):
        return s
    else:
        return s.encode("latin-1")


def make_header(msg_type, device_id, class_id, command_id, payload_len):
    header = [
            (msg_type << 7) | (device_id << 3) | (payload_len >> 8),
            payload_len & 0xff,
            class_id,
            command_id,
    ]
    return struct.pack("<%dB" % HEADER_LENGTH, *header)


class Serializer(object):

    def __init__(self, apis):
        self.apis = {}
        self.device_ids = {}
        for api in apis:
            self.apis[api.device_id] = api
            self.device_ids[api.device_name] = api.device_id

    def _convertEnumDefine(self, apiparam, val, enums, defines):
        """
        Converts textual definitions into their numeric versions
        """
        if not apiparam.validator_id:
            return toInt(val)
        if not isinstance(val, basestring) or  len(val) == 0 or val[0] in "0123456789":
            return toInt(val)

        if apiparam.validator_type == "enum":
            val = enums[val].value
        elif apiparam.validator_type == "define":
            vals = val.split("|")
            val = 0
            for v in vals:
                val |= defines[v].value
        return toInt(val)

    def _parseParameters(self, args, apiparams, enums, defines):
        """ Returns tuple (pack format list, argument list)  """
        if len(args) != len(apiparams):
            raise TypeError("Expected %d arguments, %d given (%r)" % (len(apiparams), len(args), args))

        packers = {
            # {format : (pack code, python value to pack) }
            "int8" :
                lambda apiparam, x: ("b", self._convertEnumDefine(apiparam, x, enums, defines)),
            "uint8" :
                lambda apiparam, x: ("B", self._convertEnumDefine(apiparam, x, enums, defines)),
            "int16" :
                lambda apiparam, x: ("h", self._convertEnumDefine(apiparam, x, enums, defines)),
            "uint16" :
                lambda apiparam, x: ("H", self._convertEnumDefine(apiparam, x, enums, defines)),
            "int32" :
                lambda apiparam, x: ("i", self._convertEnumDefine(apiparam, x, enums, defines)),
            "uint32" :
                lambda apiparam, x: ("I", self._convertEnumDefine(apiparam, x, enums, defines)),
            "int64" :
                lambda apiparam, x: ("q", self._convertEnumDefine(apiparam, x, enums, defines)),
            "uint64" :
                lambda apiparam, x: ("Q", self._convertEnumDefine(apiparam, x, enums, defines)),
            "uint8array" :
                lambda apiparam, x: ("%ds" % (len(to_bytes(x)) + 1), struct.pack("<B", len(x)) + to_bytes(x)),
            "uint16array" :
                lambda apiparam, x: ("%ds" % (len(to_bytes(x)) + 2), struct.pack("<H", len(x)) + to_bytes(x)),
            "bd_addr" :
                lambda apiparam, x: ("6s", binascii.unhexlify(to_bytes(x).replace(b":", b""))[::-1]), #Last part is to reverse byte order
            "hw_addr" :
                lambda apiparam, x: ("6s", binascii.unhexlify(to_bytes(x).replace(b":", b""))),
            "ipv4" :
                lambda apiparam, x: ("4s", b"".join(map(struct.Struct(">B").pack, map(int, x.split("."))))),
            "uuid_128" :
                lambda apiparam, x: ("16s", to_bytes(x)),
            "aes_key_128" :
                lambda apiparam, x: ("16s", to_bytes(x)),
            "sl_bt_uuid_64_t" :
                lambda apiparam, x: ("8s", to_bytes(x)),
            "sl_bt_uuid_16_t" :
                lambda apiparam, x: ("2s", to_bytes(x)),
            "byte_array":
                lambda apiparam, x: ("%ds" % apiparam.datatype.length, to_bytes(x)),

        }

        a = tuple(zip(*[ packers[apiparam.format](apiparam, val) for apiparam, val in zip(apiparams, args) ]))
        if not a:
            return ([], [])

        return a

    def command(self, device_id, class_name, command_name, args):
        if isinstance(device_id, str):
            device_id = self.device_ids[device_id]

        apiclass = self.apis[device_id][class_name]
        apicommand = apiclass.commands[command_name]

        # parameters into binary
        pack_format, params = self._parseParameters(args, apicommand.params, apiclass.enums, apiclass.defines)
        pack_format = "".join(pack_format)
        param_data_len = struct.calcsize("<%s" % pack_format)

        header = make_header(MSG_COMMAND, device_id, apiclass.index,
                             apicommand.index, param_data_len)
        payload = struct.pack("<%s" % pack_format, *params)

        return header + payload

class DeserializerError(Exception):
    """ Base class for deserializer related exceptions. """
    def __init__(self, msg):
        msg += "\nPlease check if correct XAPI file is in use."
        super().__init__(msg)

class DeserializerApiMissingError(DeserializerError):
    """ This error is thrown if no API definition is found with the given device ID. """
    def __init__(self, device_id):
        msg = "No API definition for device ID {:d}".format(device_id)
        super().__init__(msg)

class DeserializerEventMissingError(DeserializerError):
    """ This error is thrown if no event definition is found for the given class. """
    def __init__(self, class_id, event_id):
        msg = "No event definition with index {:d} for class {:d}.".format(class_id, event_id)
        super().__init__(msg)

class Deserializer(object):

    def parseHeader(self, header):
        """
        Returns tuple with:
            - type: COMMAND=0 or EVENT=1
            - device id: BLE = 0
            - parameter length
            - class id
            - command id
        """
        return (
            (operator.getitem(header, 0) & 0x80) >> 7,
            (operator.getitem(header, 0) & 0x78) >> 3,
            (operator.getitem(header, 0) & 0x7) << 8 | operator.getitem(header, 1),
            operator.getitem(header, 2),
            operator.getitem(header, 3)
            )

    def __init__(self, apis):
        self.apis = {}
        for api in apis:
            self.apis[api.device_id] = api

    def _convertEnumDefine(self, apiparam, val, enums, defines):
        if not apiparam.validator_id:
            return val
        if apiparam.validator_type == "enum":
            return enums[apiparam.validator_id][val].name
        elif apiparam.validator_type == "define":
            ret = []
            for flag in apiparam.defines[apiparam.validator_id]:
                if flag.value & val: ret.append(flag.name)
            if len(ret) != 0:
                return "|".join(ret)
        return val

    def parse(self, header, payload, fromHost, enumdefines=True):
        """
            Returns a tuple consisting of: (apicommand, header field tuple, param list)
        """
        hfields = self.parseHeader(header)

        cmdevt, device_id, parameter_len, classIndex, cmdEvtIndex = hfields
        try:
            api = self.apis[device_id]
        except KeyError:
            raise DeserializerApiMissingError(device_id) from None
        apidoc_name = api.name

        if cmdevt == MSG_COMMAND:
            cmdevt = api[classIndex].commands[cmdEvtIndex]
            if fromHost:
                apiparams = cmdevt.params
                apidoc_name += "_cmd"
            else:
                apiparams = cmdevt.returns
                apidoc_name += "_rsp"
        else:
            try:
                cmdevt = api[classIndex].events[cmdEvtIndex]
            except KeyError:
                raise DeserializerEventMissingError(classIndex, cmdEvtIndex) from None
            apiparams = cmdevt.params
            apidoc_name += "_evt"

        apidoc_name += "_%s_%s" % (cmdevt.api_class.name, cmdevt.name)

        unpackers = {
            "int8":
                lambda apiparam, x: ("b"),
            "uint8":
                lambda apiparam, x: ("B"),
            "int16":
                lambda apiparam, x: ("h"),
            "uint16":
                lambda apiparam, x: ("H"),
            "int32":
                lambda apiparam, x: ("i"),
            "uint32":
                lambda apiparam, x: ("I"),
            "int64":
                lambda apiparam, x: ("q"),
            "uint64":
                lambda apiparam, x: ("Q"),
            "uint8array":
                lambda apiparam, x: ("x%ds" % struct.unpack("<B", x[:1])),
            "uint16array":
                lambda apiparam, x: ("xx%ds" % struct.unpack("<H", x[:2])),
            "bd_addr":
                lambda apiparam, x: ("6s"),
            "hw_addr":
                lambda apiparam, x: ("6s"),
            "ipv4":
                lambda apiparam, x: ("4s"),
            "uuid_128":
                lambda apiparam, x: ("16s"),
            "aes_key_128":
                lambda apiparam, x: ("16s"),
            "sl_bt_uuid_64_t":
                lambda apiparam, x: ("8s"),
            "sl_bt_uuid_16_t":
                lambda apiparam, x: ("2s"),
            "byte_array":
                lambda apiparam, x: ("%ds" % apiparam.datatype.length),
        }

        pos = 0
        pack_format = ""
        for (i, apiparam) in enumerate(apiparams):
            if pos >= len(payload):
                # Message has less params than in the API definition
                missing_params = [param.name for param in apiparams]
                logger.warning(
                        "Received message '%s' with parameter(s) %s missing.",
                        apidoc_name,
                        ", ".join(["'%s'" % (p.name) for p in apiparams[i:]]))
                break
            # Give first 2 bytes of the field for array unpackers
            fmt = unpackers[apiparam.format](apiparam, payload[pos:pos+2])
            pack_format += fmt
            pos += struct.calcsize(fmt)

        if len(payload) > pos:
            # Message has more params than in the API definition, ignore extra
            logger.warning("Received message '%s' with %d byte(s) extra payload.",
                    apidoc_name, len(payload) - pos)
            payload = payload[:pos]

        vals = struct.unpack("<%s" % pack_format, payload)

        params = list(vals)

        # If message had less params than defined in the API, put None in place
        missing_params = len(apiparams) - len(params)
        params += [None] * missing_params

        converters = {
            "int8": lambda x: x,
            "uint8": lambda x: x,
            "int16": lambda x: x,
            "uint16": lambda x: x,
            "int32": lambda x: x,
            "uint32": lambda x: x,
            "int64": lambda x: x,
            "uint64": lambda x: x,
            "uint8array": lambda x: x,
            "uint16array": lambda x: x,
            "bd_addr": lambda x: ":".join(["{:02x}".format(b) for b in iter(reversed(x))]),
            "hw_addr": lambda x: ":".join(["{:02x}".format(b) for b in iter(x)]),
            "ipv4": lambda x: ".".join(map(str, iter(x))),
            "uuid_128": lambda x: x,
            "aes_key_128": lambda x: x,
            "sl_bt_uuid_64_t": lambda x: x,
            "sl_bt_uuid_16_t": lambda x: x,
            "byte_array": lambda x: x,
        }

        params = [converters[apiparam.format](param) for (param, apiparam) in zip(params, apiparams)]

        if enumdefines:
            enums = api[classIndex].enums
            defines = api[classIndex].defines
            params = [self._convertEnumDefine(apiparams[i], params[i], enums , defines) for i in range(len(apiparams))]

        return (cmdevt, hfields, params)
