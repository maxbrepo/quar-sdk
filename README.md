# Quar SDK

**Version 0.0.1 — September 17, 2026**

Quar SDK is the development environment and experimental toolchain for the Quar language ecosystem.

## Currently Supported Language

* **Visual Quar**

Visual Quar is currently the primary language supported by Quar SDK.

## Execution

Quar SDK 0.0.1 provides two experimental execution paths.

### QRVM

Visual Quar programs can be executed through **QRVM (Quar Virtual Machine)**.

The current QRVM reference implementation is written in Python. QRVM executes Quar instructions independently from the C compilation backend.

### C Transpilation

Visual Quar can be transpiled to C and subsequently compiled into native executable code.

Current targets:

* **Linux:** C compilation through GCC.
* **Windows:** C compilation through MinGW, with the Windows target currently developed and tested from Linux using Wine.

## Current Status

Quar SDK 0.0.1 is the first early development release intended to validate the core architecture of the Visual Quar toolchain.

The current architecture includes:

* Visual Quar source processing.
* Initial compiler pipeline.
* C transpilation backend.
* Native compilation path.
* Initial QRVM execution path.
* Python-based QRVM reference implementation.

Both the C/native execution path and the initial QRVM execution path have been successfully tested.

Quar SDK, Visual Quar, QRVM, the instruction set, compiler architecture, APIs and project structure are under active development and may change substantially before version 1.0.

## Project Status

**Quar SDK 0.0.1 — Initial Development Release**

Released: **September 17, 2026**
