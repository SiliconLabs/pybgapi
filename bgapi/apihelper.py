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

import re


def camelcase(text):
    return "".join([x.capitalize() for x in text.split("_")])


def strip_html(description, singleLine = False):
    return re.sub("<.*?>", "", description).strip()


def api_cmd_to_ascii(cmdnode):
    description = strip_html(cmdnode.description)
    if not description:
        description = "Send command %s." % cmdnode.name

    text = [description]
    text.append("\nArguments:")
    if not cmdnode.params:
        text.append(" (none)")
    for param in cmdnode.params:
        text.append("\t - %s: %s"%(param.name, strip_html(param.description)))
    if hasattr(cmdnode, "returns") and cmdnode.returns:
        text.append("\nReturn values:")
        for ret in cmdnode.returns:
            if ret.description:
                text.append(" - %s: %s"%(ret.name, strip_html((ret.description))))
            else:
                text.append(" - %s"%ret.name) 
    return "\n".join(text)


class ApiHelper(object):
    def __init__(self, api):
        self.api = api
        self.classes = self.api.keys()

    def split_user_input(self, text):
        """
        Returns ( class, command, [param1, param2, ...] )
        """
        apiclass, rest = text.split("_",1)
        if " " in rest:
            command, rest = rest.split(" ", 1)
        else:
            command = rest
            rest = ""
        params = rest.split(" ")
        return (apiclass, command, params)

    def complete_enum_define(self, apiclass, apiparam, val):
        """
        Takes the param to be suggested and current val
        returns a sorted list of suggestions
        """
        if apiparam.validator_id == None: return []
        if apiparam.validator_type == "enum":
            possible_vals = apiclass.enums[apiparam.validator_id].keys()
        elif apiparam.validator_type == "define":
            if "|" in val: val = val.split("|")[-1]
            possible_vals = apiclass.defines[apiparam.validator_id].keys()
        else:
            possible_vals = []
        return sorted(filter(lambda x: x.startswith(val), possible_vals))

    def is_current_param_complete(self, userinput):
        return userinput.endswith(" ")

    def is_command_complete(self, userinput):
        return " " in userinput

    def is_class_complete(self, userinput):
        return "_" in userinput

    def completion_suggestions(self, text):
        class_name, command_name, params =  self.split_user_input(text)
        if not self.is_class_complete(text):
            return sorted(filter(lambda x: x.startswith(apiclass), self.api.keys()))
        if class_name not in self.api:
            return []
        if not self.is_command_complete(text):
            command_suggestions = sorted(filter(lambda x: x.startswith(command_name), self.api[class_name].command_names))
            return ["%s_%s"%(class_name, x) for x in command_suggestions]
        if command_name not in self.api[class_name].commands:
            return []

        if params[0] == "":
            cur_param = 0
        else:
            cur_param = len(params)-1

        if cur_param >= len(param_count):
            return []

        apiclass = self.api[apiclass]
        apiparam = apiclass.commands[command].prams[cur_param]
        return complete_enum_define(self, apiclass, apiparam, params[cur_param])
