# ${PROJECT_NAME}

> ${PROJECT_DESC}

## Documentation

- [README](${BLOB}/README.md)
- [AGENTS](${BLOB}/AGENTS.md)
- [CONTRIBUTING](${BLOB}/CONTRIBUTING.md)
- [Protocol Notes](${BLOB}/docs/PROTOCOL_NOTES.md)
- [Safety Model](${BLOB}/docs/SAFETY_MODEL.md)
- [Hardware](${BLOB}/docs/HARDWARE.md)
- [Experiment Log](${BLOB}/docs/EXPERIMENT_LOG.md)

## Source

- [driver.py](${BLOB}/src/dpette/driver.py): High-level API (connect, aspirate, dispense, mix)
- [protocol.py](${BLOB}/src/dpette/protocol.py): 6-byte packet encode/decode, command enums
- [serial_link.py](${BLOB}/src/dpette/serial_link.py): Thin pyserial wrapper
- [safety.py](${BLOB}/src/dpette/safety.py): Volume/speed validation, cycle-count limits
- [config.py](${BLOB}/src/dpette/config.py): SerialConfig, port discovery

## Tools

- [interactive_probe.py](${BLOB}/tools/interactive_probe.py): Interactive probing
- [capture_usb.py](${BLOB}/tools/capture_usb.py): USB traffic capture
