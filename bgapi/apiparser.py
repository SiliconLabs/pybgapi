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

def toInt(s):
    if isinstance(s, str):
        s = str(s).strip()
        if s.startswith("0x"):
            return int(s[2:], 16)
        if s.startswith("0b"):
            return int(s[2:], 2)
    return int(s)


class ApiEnumVal(object):

    def __init__(self, enum, node):
        self.parent = enum
        self.name = node.attrib["name"]
        self.value = toInt(node.attrib["value"])
        self.description = node.findtext("description", default="")


class ApiDefineVal(ApiEnumVal): pass


class ApiEnum(dict):

    def __init__(self, api_class, node):
        self.api_class = api_class
        self.name = node.attrib["name"]
        self.description = node.findtext("description", default="")
        self.values = {}
        self.names = []

        for n in node.iter(tag="enum"):
            e = ApiEnumVal(self, n)
            self[e.name] = e
            self[e.value] = e
            self.names.append(e.name)


class ApiDefine(dict):

    def __init__(self, api_class, node):
        self.api_class = api_class
        self.name = node.attrib["name"]
        self.description = node.findtext("description", default="")
        self.values = {}
        self.names = []

        for n in node.iter(tag="define"):
            e = ApiDefineVal(self, n)
            self.names.append(e.name)
            self[e.name] = e
            self[e.value] = e


class ApiType(object):

    def __init__(self, node):
        if node is not None:
            self.name = node.get("name", "")
            self.base = node.get("base", "")
            self.length = toInt(node.get("length", default=0))
        else:
            self.name = ""
            self.base = ""
            self.length = 0

class ApiParameter(object):

    def __init__(self, parent, index, node):
        self.parent = parent
        self.index = toInt(index)
        self.name = node.attrib["name"]
        self.format = node.attrib["type"]
        self.datatype = self.parent.api_class.api.types.get(node.get("datatype", None), ApiType(None))
        self.validator_type = node.get("validator_type", None)
        self.validator_id = node.get("validator_id", None)
        self.description = node.findtext("description", default="")


class ApiCommand(object):

    def __init__(self, api_class, node):
        self.api_class = api_class
        self.index = toInt(node.attrib["index"])
        self.name = node.attrib["name"]
        self.description = node.findtext("description", default="")
        self.params = []
        self.returns = []
        self.no_return = bool(node.get("no_return", False))
        self.internal = bool(node.get("internal", False))
        if node.find("params") is not None:
            for n in node.find("params").iter(tag="param"):
                self.params.append(ApiParameter(self, len(self.params), n))
        if node.find("returns") is not None:
            for n in node.find("returns").iter(tag="param"):
                self.returns.append(ApiParameter(self, len(self.returns), n))


class ApiEvent(object):

    def __init__(self, api_class, node):
        self.api_class = api_class
        self.index = toInt(node.attrib["index"])
        self.name = node.attrib["name"]
        self.description = node.findtext("description", default="")
        self.internal = bool(node.get("internal", False))
        self.params = []
        for n in node.find("params").iter(tag="param"):
            self.params.append(ApiParameter(self, len(self.params), n))


class ApiClass(object):

    def __init__(self, api, node):
        self.api = api
        self.index = toInt(node.attrib["index"])
        self.name = node.attrib["name"]
        self.description = node.findtext("description", default="")
        self.enums = {}
        self.enum_names = []
        self.defines = {}
        self.define_names = []
        self.commands = {}
        self.command_names = []
        self.events = {}
        self.event_names = []

        for n in node.iter(tag="enums"):
            e = ApiEnum(self, n)
            self.enum_names.append(e.name)
            self.enums[e.name] = e

        for n in node.iter(tag="defines"):
            e = ApiDefine(self, n)
            self.define_names.append(e.name)
            self.defines[e.name] = e

        for n in node.iter(tag="command"):
            e = ApiCommand(self, n)
            self.command_names.append(e.name)
            self.commands[e.name] = e
            self.commands[e.index] = e

        for n in node.iter(tag="event"):
            e = ApiEvent(self, n)
            self.event_names.append(e.name)
            self.events[e.name] = e
            self.events[e.index] = e


class ParsedApi(dict):

    def __init__(self, filename=None, deviceId=0):
        self.filename = filename

        self.description = ""
        self.names = []
        self.types = {}

        from xml.etree.ElementTree import parse
        node = parse(self.filename).getroot()

        self.device_id = toInt(node.attrib["device_id"])
        self.device_name = node.attrib["device_name"]
        self.name = self.device_name
        # some old version of xapi might be missing datatypes totally
        # datatypes is important only for byte_array types when the length of
        # type needs to be specified
        for datatype in map(ApiType, node.findall("./datatypes/datatype")):
            self.types[datatype.name] = datatype

        try:
            self.version = node.attrib["version"]
        except KeyError:
            self.version = None
        for n in node.iter(tag="class"):
            e = ApiClass(self, n)
            self.names.append(e.name)
            self[e.name] = e
            self[e.index] = e
