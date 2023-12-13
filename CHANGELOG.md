## Changelog

### 1.3.0 - 2023-12-13

#### Added
- CPC connector. Requires [libcpc Python binding](https://github.com/SiliconLabs/cpc-daemon/tree/main/lib/bindings/python) to be installed.
- Robust connector to eliminate errors in the transport layer.
- `command` attribute in the `CommandFailedError` to provide more details about the error.

#### Changed
- Python version compatibility updated.

### 1.2.0 - 2022-09-02
#### Added
- Thread safety for commands.
- Support the `byte_array` type.

#### Changed
- Improve error messages in deserializer.

### 1.1.0 - 2021-06-28
#### Added
- Support the `sl_bt_uuid_16_t` type.
- Fix communication issues caused by glitches on the physical layer.
- Parse API version to support compatibility check.

#### Changed
- Parse define and enum names so that they start with the group name.

### 1.0.0 - 2021-04-19
#### Added
- Initial public version.
