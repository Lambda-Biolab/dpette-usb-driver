---
title: "Protocol notes"
status: "DRAFT"
updated: "2026-04-06"
owner: "lambda biolab"
---

# Protocol notes

Document all findings from USB capture analysis here **before**
implementing them in code.

## Serial parameters

| Parameter  | Value     | Source / confidence |
|------------|-----------|---------------------|
| Baud rate  | unknown   | —                   |
| Byte size  | 8 (assumed) | —                 |
| Parity     | N (assumed) | —                 |
| Stop bits  | 1 (assumed) | —                 |

## Framing

<!-- Describe the packet structure once identified -->

- Start byte(s): ?
- Length field: ?
- Message type byte: ?
- Payload: ?
- Checksum / CRC: ?
- End byte(s): ?

## Commands (host → device)

<!-- Add entries as they are discovered -->

| Name       | Type byte | Payload format | Description |
|------------|-----------|----------------|-------------|
| PING       | ?         | —              | Liveness check |
| IDENTIFY   | ?         | —              | Query model/firmware |
| SET_VOLUME | ?         | ?              | Set target volume |
| ASPIRATE   | ?         | ?              | Draw liquid |
| DISPENSE   | ?         | ?              | Expel liquid |
| BLOW_OUT   | ?         | ?              | Clear tip |
| EJECT_TIP  | ?         | ?              | Eject tip |

## Responses (device → host)

| Name       | Type byte | Payload format | Description |
|------------|-----------|----------------|-------------|
| ACK        | ?         | —              | Command accepted |
| ERROR      | ?         | ?              | Error code |
| IDENTITY   | ?         | ?              | Model + firmware info |

## Checksums

<!-- Describe the checksum algorithm once identified -->

Algorithm: unknown (candidates: XOR, CRC-8, CRC-16, modular sum)

## Capture examples

<!-- Paste annotated hex dumps here -->

```
# Example (placeholder):
# TX: AA 01 00 55   — PING?
# RX: AA 80 00 55   — ACK?
```
