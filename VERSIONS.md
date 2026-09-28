# Quar SDK Releases

This document records the released Quar SDK versions and the main
capabilities introduced by each release.

============================================================

# Version 0.0.2

**Release date:** September 28, 2026\
**Status:** Early Development Release

Quar SDK 0.0.2 expands the initial Visual Quar toolchain into a broader
development environment centered around Quar Edit, language profiles,
external toolchain integration, and multilingual interface support.

------------------------------------------------------------------------

## Quar Edit

Version 0.0.2 establishes the first functional Quar Edit baseline.

The editor includes file and folder operations, tab-based editing,
saving and Save As, preferences infrastructure, keyboard shortcuts,
themes, source templates, language profiles, source-extension
recognition, and language-dependent build and execution operations.

Quar Edit connects supported language profiles to external compilers,
interpreters, runtimes, and build tools. Operations can be enabled or
disabled according to the selected language and the availability of its
required toolchain.

Build and execution timing are handled separately.

------------------------------------------------------------------------

## Visual Quar

Visual Quar remains the primary language of the Quar ecosystem.

Its development architecture continues to use a frontend validation
pipeline followed by either the QRVM development path or the C/native
compilation path.

------------------------------------------------------------------------

## QRVM

QRVM remains the development-oriented virtual-machine path for Visual
Quar.

It is kept separate from the C backend so that rapid execution and
native compilation can evolve independently.

------------------------------------------------------------------------

## C Transpilation and Native Compilation

The native Visual Quar path continues to generate C source and delegate
final compilation to an external native C toolchain.

The two Visual Quar execution directions therefore remain:

`Visual Quar -> QRVM`

`Visual Quar -> C -> native compiler -> executable`

------------------------------------------------------------------------

## Programming Languages

Quar Edit 0.0.2 includes profiles for **C, C++, Assembly, Rust, Pascal,
Go, Zig, Python, Java, JavaScript, TypeScript, Mojo, Visual Quar, and
FreeBASIC**.

## User Interface Languages

Quar Edit 0.0.2 includes localization resources for **English, Italiano,
Español (España), Português (Brasil), 日本語, 简体中文, 繁體中文,
한국어, हिन्दी, Français, العربية, Русский, Deutsch, Türkçe, Bahasa
Indonesia, Tiếng Việt, Polski, বাংলা, ไทย, فارسی, اردو, Українська,
Nederlands, Ελληνικά, Čeština, and Română**.

The localization baseline covers the 59 interface keys defined for this
release. Native-speaker review and continued graphical validation,
particularly for right-to-left interfaces, remain separate validation
work.

============================================================

# Version 0.0.1

**Release date:** September 17, 2026\
**Status:** Initial Development Release

Quar SDK 0.0.1 established the first working foundation of the Visual
Quar toolchain.

------------------------------------------------------------------------

## Visual Quar

The first Visual Quar processing pipeline was established around lexical
analysis, parsing, AST construction, and semantic analysis.

The initial language subset supported typed declarations, assignments,
variables, integer values, arithmetic expressions, and operator
precedence.

External `.vq` source files could be processed by the toolchain.

------------------------------------------------------------------------

## QRVM

The first QRVM execution path was introduced.

The QRVM reference implementation was written in Python and provided a
stack-oriented execution model independent from the C compilation
backend.

The initial instruction set included operations for loading and storing
values, arithmetic, output, stack cleanup, and program termination.

------------------------------------------------------------------------

## C Transpilation and Native Compilation

Visual Quar programs could be transpiled to C and subsequently compiled
into native executable code.

The documented native targets were Linux through GCC and Windows through
MinGW, with the Windows target developed and tested from Linux using
Wine.

Both the QRVM path and the C/native path were successfully tested.

============================================================