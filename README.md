# Quar SDK

**Current development version: 0.0.4 — private development release candidate, October 2026**

Quar SDK is the modular development environment and experimental toolchain for the Quar language ecosystem.

Its purpose is to let Visual Quar, Quar Edit, QRVM, native compilation, external programming-language toolchains, source representation, localization, and future development tools evolve as cooperating modules rather than as a single mandatory editor or runtime.

Version 0.0.4 extends the previously developed QRVM-first language baseline with intermediate-representation work, package-management foundations, runtime and memory-safety experiments, and a second review of chapters 1–18. Chapter 1 of that second pass has been tested by the project owner. The release remains experimental and is intended to stay private pending a separate public-release review.

## Component Versions

- Quar SDK: **0.0.4**
- Visual Quar: **0.0.4**
- Quar Edit: **0.0.2** (last documented component version; verify independently before tagging)
- Kart: **0.0.1** (initial package-manager version in this development line)

These components are versioned independently.

## Project Structure

### Quar Edit

Quar Edit is the reference editor and development interface, not a required frontend for Visual Quar.

The bootstrap implementation uses Python and GTK. In the documented 0.0.3 line, Quar Edit advanced from 0.0.1 to 0.0.2, adding Visual Quar syntax highlighting and a non-destructive Source View connected to the SDK Source Projection service.

For `.vq` documents, QEdit keeps the authoritative working source separate from the visible projection. Changing Source View therefore changes representation rather than silently rewriting the canonical source.

QEdit remains modular: language services should live in the SDK when they can be useful to other clients. Future integrations such as Vim, Geany, or other editors can consume the same services without depending on QEdit.

### Visual Quar

Visual Quar is the primary language of the Quar ecosystem. Source files use the `.vq` extension.

The frontend continues to use lexical analysis, parsing, AST construction, and semantic analysis. The language baseline developed during the first QRVM-focused pass covers the procedural core through structured types, including:

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

The 0.0.3 line introduced the editor-independent `tooling/source_projection` service.

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

Quar SDK 0.0.4 remains an early pre-1.0 development version. Syntax, APIs, source profiles, language services, VM behavior, compiler architecture, and editor integration may change.

Experimental features are deliberately allowed when they can be isolated from the stable core. Dynamic arrays and advanced source projection are examples: they can be exercised now while deeper memory-model, native-backend, and linguistic work continues.

Known legacy or deferred regression work is tracked separately from the validated typed baseline. A feature should not be described as stable merely because an experimental implementation exists.

## Documentation

`VERSION` contains the current development version.

`VERSIONS.md` records released versions and the current pre-release development line.

`SCHEMATICS.md` provides compact diagrams of the SDK, Visual Quar execution paths, Source Projection, and QEdit integration.

Quar SDK, Visual Quar, and Quar Edit use independent component versions. The current release line targets Quar SDK 0.0.4 and Visual Quar 0.0.4. Component versions remain independent; Quar Edit is last documented at 0.0.2 and Kart begins at 0.0.1. Verify component-specific metadata before publication.

## What Changed in the 0.0.4 Development Line

- **Two-pass development:** chapters 1–18 were first explored primarily through QRVM; the second pass revisits those chapters to reconcile missing functionality across frontend, IR/QIR, QRVM and the C backend. The second-pass Chapter 1 is validated; chapters 2–18 are not claimed to be reconciled.
- **Intermediate representations:** IR and subsequent QIR work provide additional compiler paths. Their presence does not imply identical feature coverage across every execution path.
- **Chapter 1 reconciliation:** lexical name resolution, imported calls versus variant constructors, module-loading integration, IR C emission, runtime panic reporting, and regression filtering were addressed. Ordinary shadowing remains disabled; experimental lexical shadowing is opt-in.
- **Kart:** local package-management foundations and supporting tests were introduced.
- **Memory safety and tooling:** experimental memory-safety, diagnostics, and bytecode/runtime work progressed across later chapters, with known limitations retained.
- **Verification:** the final development-session report recorded 1,392 passing Python tests, zero failures, one expected failure and 419 passing subtests; the project owner subsequently confirmed that tests and examples worked on their PC. These figures describe that tested baseline, not universal QRVM/Quarc equivalence.

The 0.0.4 repository is intended to remain private for now. License selection, history-wide secret scanning, credential rotation where needed, and public-release review are deferred to a later publication milestone. Any credential known to be exposed must be revoked immediately rather than waiting for that milestone.
