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

from setuptools import setup
from os import path

long_description = ""
long_description_input = ['README.md', 'CHANGELOG.md']
for infile in long_description_input:
    with open(path.join(path.dirname(__file__), infile), encoding='utf-8') as f:
        long_description += f.read() + "\n"

setup(
    name="pybgapi",
    author="Silicon Labs",
    url="https://www.silabs.com",
    description="Python interface for the BGAPI binary protocol",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="zlib",
    classifiers=[
        'License :: OSI Approved :: zlib/libpng License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],

    use_scm_version={'version_scheme': 'post-release'},
    setup_requires=['setuptools_scm'],

    packages=["bgapi"],
    data_files=[(".", ["CHANGELOG.md"])],

    python_requires=">=3.6",
    install_requires=["pyserial"],
    tests_require=["testfixtures"],

    test_suite="bgapi.test",
)
