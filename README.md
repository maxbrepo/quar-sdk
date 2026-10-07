# Quar SDK

**Current development version: 0.0.3 — pre-release, October 7, 2026**

Quar SDK is the modular development environment and experimental toolchain for the Quar language ecosystem.

Its purpose is to let Visual Quar, Quar Edit, QRVM, native compilation, external programming-language toolchains, source representation, localization, and future development tools evolve as cooperating modules rather than as a single mandatory editor or runtime.

Version 0.0.3 is the current development line. It substantially expands both the Visual Quar language baseline and the connection between Quar Edit and reusable Quar SDK services. It is not yet frozen as a stable release.

## Component Versions

- Quar SDK: **0.0.3**
- Visual Quar: **0.0.3**
- Quar Edit: **0.0.2**

These components are versioned independently.

## Project Structure

### Quar Edit

Quar Edit is the reference editor and development interface, not a required frontend for Visual Quar.

The bootstrap implementation uses Python and GTK. In the current SDK 0.0.3 development tree, Quar Edit advances from 0.0.1 to 0.0.2, adding Visual Quar syntax highlighting and a non-destructive Source View connected to the SDK Source Projection service.

For `.vq` documents, QEdit keeps the authoritative working source separate from the visible projection. Changing Source View therefore changes representation rather than silently rewriting the canonical source.

QEdit remains modular: language services should live in the SDK when they can be useful to other clients. Future integrations such as Vim, Geany, or other editors can consume the same services without depending on QEdit.

### Visual Quar

Visual Quar is the primary language of the Quar ecosystem. Source files use the `.vq` extension.

The 0.0.3 frontend continues to use lexical analysis, parsing, AST construction, and semantic analysis. The typed language baseline now covers the procedural core through structured types, including:

- fixed-width numeric types and aliases;
- constants, default initialization, checked numeric compatibility, and text truthiness;
- arithmetic, comparison, logical, bitwise, shift, and compound-assignment expressions;
- `if`, `else if`, structured `case`, loops, `break`, and `continue`;
- typed functions, recursion, default parameters, and named arguments;
- static and experimental dynamic arrays;
- Unicode strings, indexing, substring/search/replace/trim, conversion, and iteration;
- mutable `struct`, immutable `record`, `enum`, aliases, tuples, destructuring, enum payloads, and `match`.

The recent language work is validated primarily through QRVM. The native C backend remains a separate development path and must not be assumed to support every newer 0.0.3 feature until explicitly implemented and tested.

### QRVM

QRVM is the development-oriented execution path for Visual Quar. Its current reference implementation is written in Python.

QRVM remains independent from the C backend so rapid language development, regression testing, and native compilation can evolve separately.

### C Backend and Native Compilation

The native path transpiles supported validated Visual Quar source into C and delegates final compilation to an external C toolchain:

`Visual Quar source -> frontend -> generated C -> native C compiler -> executable`

The C backend is intentionally allowed to lag behind the QRVM reference path while the language is still changing rapidly.

### Source Projection and Easy Vocabulary

0.0.3 introduces the editor-independent `tooling/source_projection` service.

Its central rule is that Visual Quar keeps one canonical source representation while tools may request another visible representation. Projection is non-destructive and is kept separate from file writing.

The service currently provides:

- canonical and extended vocabulary styles;
- source profiles and explicit/inferred/mixed metadata;
- Unicode UTF-8 language packs with NFC normalization;
- deterministic keyword and type projection;
- experimental Easy Vocabulary support for identifiers and comments;
- identifier handling for common compound styles such as snake_case, camelCase, and PascalCase;
- coverage classification for known, composed, partial, and unknown vocabulary;
- a vocabulary architecture designed to grow toward thousands of canonical concepts without changing the projection API.

The development tree currently registers 26 Unicode language packs. Their presence means the infrastructure and data modules exist; it does not imply completed linguistic or native-speaker validation for every language.

### External Toolchains

Quar Edit connects programming-language profiles to external compilers, interpreters, runtimes, and build tools. Build, Compile, Run, and Interpret operations can be exposed or disabled according to the selected language and available toolchain.

This provides a common workflow without requiring Quar SDK to contain every supported language implementation.

## Quar Edit Programming Profiles

The editor baseline includes profiles for C, C++, Assembly, Rust, Pascal, Go, Zig, Python, Java, JavaScript, TypeScript, Mojo, Visual Quar, and FreeBASIC.

## User Interface Localization

QEdit interface localization is separate from Visual Quar source projection. The `quar-edit/lang` resources translate editor UI strings; `tooling/source_projection` represents Visual Quar source in different languages.

The development tree contains UI/localization resources for the same broad multilingual set used by the SDK. Native-speaker review and right-to-left graphical validation remain ongoing work.

## Development Status and Boundaries

Quar SDK 0.0.3 is still an early pre-1.0 development version. Syntax, APIs, source profiles, language services, VM behavior, compiler architecture, and editor integration may change.

Experimental features are deliberately allowed when they can be isolated from the stable core. Dynamic arrays and advanced source projection are examples: they can be exercised now while deeper memory-model, native-backend, and linguistic work continues.

Known legacy or deferred regression work is tracked separately from the validated typed baseline. A feature should not be described as stable merely because an experimental implementation exists.

## Documentation

`VERSION` contains the current development version.

`VERSIONS.md` records released versions and the current pre-release development line.

`SCHEMATICS.md` provides compact diagrams of the SDK, Visual Quar execution paths, Source Projection, and QEdit integration.

Quar SDK, Visual Quar, and Quar Edit use independent component versions. The current target set is Quar SDK 0.0.3, Visual Quar 0.0.3, and Quar Edit 0.0.2. Version 0.0.3 expands the language itself and turns reusable language/editor services into explicit SDK modules.
