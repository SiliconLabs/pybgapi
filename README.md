# PyBGAPI

This package provides a Python interface for the BGAPI binary protocol. It
reads the BGAPI definition file and dynamically generates a parser for it.

## Getting Started

To get started with Silicon Labs Bluetooth software, see
[QSG169: Bluetooth® SDK v3.x Quick Start Guide](https://www.silabs.com/documents/public/quick-start-guides/qsg169-bluetooth-sdk-v3x-quick-start-guide.pdf).

In the NCP context, the application runs on a host MCU or a PC, which is
the NCP Host, while the Bluetooth stack runs on an EFR32, which is the
NCP Target.

The NCP Host and Target communicate via a serial interface (UART). The
communication between the NCP Host and Target is defined in the Silicon Labs
proprietary protocol, BGAPI. pyBGAPI is the reference implementation of
the BGAPI protocol in Python for the NCP Host.

[AN1259: Using the v3.x Silicon Labs Bluetooth® Stack in Network CoProcessor Mode](https://www.silabs.com/documents/public/application-notes/an1259-bt-ncp-mode-sdk-v3x.pdf)
provides a detailed description how NCP works and how to configure it for
custom hardware.

For latest BGAPI documentation, see [docs.silabs.com](https://docs.silabs.com/bluetooth/latest/).

## Usage

First, create an instance of the BGLib class, which is the main component of the package.
BGLib class provides functions for sending
BGAPI commands and returning responses and ways to receive
asynchronous BGAPI events. The BGLib constructor takes a connector, which is
the transport between BGLib and the device, and a list of BGAPI definition
files. These are the currently supported connectors:

- [SerialConnector](bgapi/serialconnector.py)
- [SocketConnector](bgapi/socketconnector.py)

Start by importing the *bgapi* package and creating a BGLib object with
the Bluetooth API and a serial port connector. The *SerialConnector* takes the
serial port as an argument, which is a device file on Linux OS and macOS, e.g.,
`'/dev/tty.usbmodem1421'`, or a COM port on windows, e.g., `'COM1'`. Remember to
change the path to *sl_bt.xapi* which can be found for each SDK version in the
Bluetooth SDK under */path/to/sdks/gecko_sdk_suite/v3.x/protocol/bluetooth/api*.

    >>> import bgapi
    >>> l = bgapi.BGLib(
    ...         bgapi.SerialConnector('/dev/tty.usbmodem1421'),
    ...         '/path/to/SDK/protocol/bluetooth/api/sl_bt.xapi')
    >>> l.open()

The BGLib constructor has an *event_handler* parameter too. Its default value is
`None`, which means that all received events go to a queue for later retrieval.
Alternatively, an event handler function may be passed, which is useful in
interactive mode for printing the received events, as follows:

    >>> def event_handler(evt):
    ...     print("Received event: {}".format(evt))

Start calling BGAPI commands, as follows:

    >>> l.bt.system.hello()
    rsp_system_hello(result=0)

The command functions are blocking, where the return value is the command's
response. The commands are in an attribute
named after the device name that the API is for, `bt` in this example. Then,
they are grouped by the class name.

The response objects behave like a Python *namedtuple*, i.e., the response
fields can be accessed as attributes (the dot notation) or like a tuple by
their index. The attribute access is usually the preferred option.

    >>> response = l.bt.system.get_counters(0)
    >>> print(response)
    rsp_system_get_counters(result=0, tx_packets=543, rx_packets=2000, crc_errors=195, failures=0)

    >>> print(response.crc_errors)
    195

    >>> print(response[3])
    195

    >>> address, = l.bt.system.get_bt_address()
    >>> print(address)
    00:0b:57:49:2b:47


If a command fails and reports a non-zero result code, an exception is thrown, as follows:

    >>> try:
    ...     l.bt.system.get_random_data(255)
    ... except bgapi.bglib.CommandFailedError as e:
    ...     print("Error 0x{:x} received, "
    ...           "did we exceed the maximum length of 16?"
    ...           .format(e.errorcode))
    Error 0x180 received, did we exceed the maximum length of 16?

The received events are stored in an event queue, which can be accessed by functions,
such as `gen_events()`. This function is a generator, which
yields events from the queue as they are received. With the default parameters,
it is non-blocking and stops as soon as no more events are received. Usually,
to receive a single event, you'll set a timeout, the *timeout* parameter,
and the maximum time the generator will run altogether, which is the *max_time*
parameter. The following example resets the device and waits for a boot event
for one second.

    >>> l.bt.system.reset(0)
    >>> for e in l.gen_events(timeout=None, max_time=1):
    ...     print("Received event: {}".format(e))
    ...     if e == 'bt_evt_system_boot':
    ...         print("Bluetooth stack booted: v{major}.{minor}.{patch}-b{build}".format(**vars(e)))
    ...         break
    Received event: bt_evt_system_boot(major=3, minor=1, patch=0, build=178, bootloader=17563648, hw=1, hash=36799935)
    Bluetooth stack booted: v3.1.0-b178

Event object fields are accessed the same way as the response
objects.
