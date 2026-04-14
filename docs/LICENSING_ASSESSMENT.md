# Licensing Assessment — dpette-usb-driver

Assessment of IP and licensing considerations for making this repository public.

## Verdict: LOW RISK — safe to publish with minor cleanup

The Python driver is original code communicating over a standard USB-UART
serial interface. No vendor code or binaries are committed.

## Legal Basis

Reverse engineering of communication protocols for interoperability is
protected under:

- **US:** DMCA §1201(f) interoperability exception
  — https://www.law.cornell.edu/uscode/text/17/1201
- **EU:** Software Directive 2009/24/EC, Article 6
  — https://eur-lex.europa.eu/eli/dir/2009/24/oj

No DRM, encryption, or access controls are circumvented. The driver observes
and speaks a plaintext serial protocol over standard UART hardware.

## Items to Address Before Public Release

1. **Remove `captures/static-analysis/pettecali_instructions.pdf`** — vendor
   document, potential copyright issue. Verify it is publicly distributed by
   DLAB before including.

2. **Review `docs/PROTOCOL_NOTES.md`** — currently references Ghidra
   disassembly addresses (e.g., `FUN_140069730`). Consider describing observed
   behavior instead of citing decompilation artifacts. Not legally required,
   but reduces exposure.

3. **Add interoperability disclaimer to README:**
   > Not affiliated with DLAB Scientific. Protocol information was determined
   > through interoperability analysis of serial communication.

## What Is Already Clean

- `.gitignore` excludes `PetteCali.exe`, decompiled `.c` files, and extracted
  binaries — no vendor code is committed
- All Python code is original (not derived from decompilation)
- No EULA, NDA, or patent restrictions found for DLAB pipette instruments
- DLAB does not publish a public API or SDK, strengthening the
  interoperability justification

## References

- DLAB Scientific (vendor): https://www.dlab.com.cn
- xg590/Learn_dPettePlus (prior art, third-party RE): referenced in README
