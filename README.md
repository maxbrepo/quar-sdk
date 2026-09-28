# Quar SDK

**Current version: 0.0.2 --- September 28, 2026**

Quar SDK is the development environment and experimental toolchain for
the Quar language ecosystem.

Its purpose is to provide a coherent environment in which the Visual
Quar language, Quar Edit, QRVM, native compilation, external
programming-language toolchains, localization, and future development
tools can evolve as connected modules rather than as unrelated
applications.

Version 0.0.2 expands the toolchain foundation created in 0.0.1 into the
first broader Quar SDK development environment.

## Project Structure

Quar SDK is currently divided into several cooperating modules.

### Quar Edit

Quar Edit is the editor and main development interface.

The bootstrap implementation uses Python and GTK. Version 0.0.2 provides
the first functional editor baseline with file and folder handling,
tab-based editing, saving and Save As, preferences, keyboard shortcuts,
themes, source templates, language profiles, source-extension
recognition, and build/run integration.

Quar Edit is designed to remain an editor with a clear interface to
development tools rather than embedding every compiler or runtime
internally.

### Visual Quar

Visual Quar is the primary language of the Quar ecosystem.

Visual Quar source files use the `.vq` extension. The language frontend
is organized around lexical analysis, parsing, AST construction, and
semantic analysis.

After frontend processing, Visual Quar can follow either the QRVM
development path or the C/native compilation path.

### QRVM

QRVM is the Quar Virtual Machine and provides the development-oriented
execution path for Visual Quar.

The current reference implementation is written in Python. QRVM remains
independent from the C backend so that rapid development execution and
native compilation can evolve separately.

### C Backend and Native Compilation

The native Visual Quar path transpiles validated Visual Quar source into
C and delegates final compilation to an external C toolchain.

The conceptual path is:

`Visual Quar source -> frontend -> generated C -> native C compiler -> executable`

### External Toolchains

Quar Edit connects language profiles to external compilers,
interpreters, runtimes, and build tools.

Depending on the selected language, the editor can expose operations
such as Build, Compile, Run, and Interpret. Operations can be disabled
when the required external tool is unavailable.

This provides a common editing and development workflow without
requiring Quar SDK to contain every supported language implementation.

## Current Features

Version 0.0.2 currently provides:

-   Functional Quar Edit editor baseline.
-   File and folder workflow.
-   Tab-based source editing.
-   Preferences, themes, actions, and keyboard shortcuts.
-   Source templates and extension recognition.
-   Multi-language programming profiles.
-   External compiler, interpreter, runtime, and toolchain integration.
-   Language-dependent Build, Compile, Run, and Interpret operations.
-   Separate build and execution timing.
-   Visual Quar frontend processing.
-   QRVM development execution path.
-   Visual Quar-to-C transpilation and native compilation path.
-   Multilingual interface infrastructure.

## Programming Languages

Quar Edit 0.0.2 includes profiles for **C, C++, Assembly, Rust, Pascal,
Go, Zig, Python, Java, JavaScript, TypeScript, Mojo, Visual Quar, and
FreeBASIC**.

The profile system associates each language with its relevant source
extensions, templates, development operations, and external tool
requirements.

## User Interface Languages

Quar Edit 0.0.2 includes localization resources for **English, Italiano,
Español (España), Português (Brasil), 日本語, 简体中文, 繁體中文,
한국어, हिन्दी, Français, العربية, Русский, Deutsch, Türkçe, Bahasa
Indonesia, Tiếng Việt, Polski, বাংলা, ไทย, فارسی, اردو, Українська,
Nederlands, Ελληνικά, Čeština, and Română**.

The localization baseline covers the **59 interface keys** defined for
this release.

Internal identifiers and source code remain canonical in English while
user-visible strings are kept in localization resources.

The presence of a localization resource does not imply completed
native-speaker review. Right-to-left graphical behavior for Arabic,
Persian, and Urdu also remains subject to continued validation.

## Current Development Boundaries

Quar SDK 0.0.2 is still an early development release.

Syntax-highlighting definitions and language information are being
developed, but highlighting is not described as an operational 0.0.2
feature until it is fully connected to the editor text buffer.

Advanced debugging, deeper project management, and other complete-IDE
capabilities remain future development areas.

The language, VM, compiler architecture, editor, APIs, profiles, and SDK
structure may continue to change before version 1.0.

## Documentation

`VERSION` contains the current machine-readable release number.

`VERSIONS.md` records the history and capabilities of individual
releases.

`SCHEMATICS.md` provides compact diagrams of the main Quar SDK
architecture and execution paths.

For historical details, version 0.0.1 established the initial Visual
Quar compiler, QRVM, C transpilation, and native execution foundation;
version 0.0.2 builds the editor and broader SDK environment around that
foundation.
