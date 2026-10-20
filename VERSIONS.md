# Quar SDK Releases

This document records released Quar SDK versions and the current development line.

# Version 0.0.4

**Release date:** October 20, 2026** 
**Status:** Private development release candidate; not a public stable release

**Component targets:** Quar SDK 0.0.4, Visual Quar 0.0.4; Quar Edit last documented at 0.0.2; Kart begins at 0.0.1. Component version metadata should be verified independently.

## Development summary

- First pass through chapters 1–18: QRVM-first implementation and tests.
- Second pass: reconcile frontend, IR, QIR, QRVM, and Quarc, adding missing functionality without claiming complete backend parity.
- Chapter 1 second pass: lexical resolution and IR/module-loader reconciliation validated by the project owner. Ordinary shadowing remains off; experimental shadowing is explicit.
- Kart local package-management foundation; ongoing experimental memory-safety, diagnostics and bytecode/runtime work.
- Last reported full Python suite: **1,392 PASS, 0 FAIL, 1 XFAIL**, plus 419 passing subtests. User confirmed examples and tests pass on the applied cumulative baseline.

## Boundaries

QRVM typed/inferred/mixed and Quarc/native paths have tested cases, but do not yet guarantee equal support for all language constructs. The remaining second-pass chapters 2–18 are not yet reconciled. The project is pre-1.0 and may change interfaces or semantics.

The repository remains private pending a separate license and security review before any future public release.

============================================================


============================================================

# Version 0.0.3

**Release date:** October 7, 2026**
**Status:** Pre-release / Active Development

Quar SDK 0.0.3 is the current development line. Its component targets are Visual Quar 0.0.3 and Quar Edit 0.0.2. The components use independent version numbers: SDK releases do not force the editor and language to share the same version.

The version is not yet frozen. Items listed here describe functionality present in the current development tree and should not be interpreted as a final stable-release guarantee.

------------------------------------------------------------------------

## Visual Quar Language

The typed 0.0.3 baseline has been developed and regression-tested through the structured-types chapter.

Major areas added or consolidated during this development line include:

- fixed-width signed and unsigned integer families and numeric aliases;
- constants, default initialization, safe numeric compatibility, overflow/underflow diagnostics, and precision-loss diagnostics;
- unified text literal work and Unicode-oriented string semantics;
- arithmetic, comparison, logical, bitwise, shift, precedence, parentheses, modulo, and compound assignment;
- `if`, `else if`, truthiness, structured `case`, and legacy switch compatibility;
- `while`, `do while`, explicit `loop`, ascending/descending `for`, `break`, `continue`, and conservative infinite-loop diagnostics;
- typed functions, recursion, default parameters, named arguments, and related validation;
- static arrays, multidimensional bounds checking, indexed iteration, and experimental dynamic arrays;
- Unicode strings with length, indexing, substring, find, replace, trim, conversion, iteration, escapes, and ordered comparison;
- mutable `struct`, immutable `record`, `enum`, aliases, tuples, destructuring, enum associated values/payloads, and `match` with exhaustiveness and duplicate-variant validation.

Recent language development is QRVM-first. Native C backend support is not assumed for every newer construct until separately implemented and tested.

------------------------------------------------------------------------

## Regression Runner and Feature Status

The 0.0.3 development tools distinguish successful execution from controlled expected errors and internal crashes.

Regression results use the categories:

`PASS`, `EXPECTED ERROR`, `FAIL`, and `CRASH`.

Feature status infrastructure also separates maturity from architectural dependencies so experimental features can exist without being mislabeled as stable.

------------------------------------------------------------------------

## Source Projection and Easy Vocabulary

0.0.3 introduces `tooling/source_projection` as an editor-independent Visual Quar service.

The service keeps canonical Visual Quar source separate from its visible representation and supports explicit source profiles, canonical/extended vocabulary, UTF-8 language data, NFC Unicode normalization, and non-destructive projection.

The development tree includes experimental Easy Vocabulary support for identifier and comment representation. Known, composed, partial, and unknown vocabulary can be distinguished, allowing incomplete translation to fall back rather than fabricate source meaning.

The vocabulary architecture is designed to grow toward thousands of canonical concepts without requiring a new projection API.

The current tree registers 26 Unicode language packs. These packs establish infrastructure and vocabulary data; they are not all claimed to have completed native-speaker validation.

------------------------------------------------------------------------

## Quar Edit 0.0.2 Integration

Quar Edit advances from 0.0.1 to 0.0.2 in this SDK development line and now acts as the first client of the Visual Quar Source Projection service.

For `.vq` documents the editor can maintain authoritative source text separately from a display-only projection. Source View is connected to SDK source profiles rather than implementing a private translation engine inside QEdit.

The development tree also includes Visual Quar syntax highlighting tied to the same vocabulary/profile infrastructure, with Off, Classic, and High Contrast presentation choices.

This architecture is intentionally editor-independent: QEdit is the reference integration, while other editors can consume the same SDK service in the future.

------------------------------------------------------------------------

## Unicode and Localization

QEdit UI localization and Visual Quar source projection remain separate concerns.

UI resources translate the editor itself. Source Projection represents Visual Quar code. Both are designed around Unicode so future languages are not constrained to Latin-script assumptions.

------------------------------------------------------------------------

## Experimental / Deferred Areas

0.0.3 deliberately allows isolated experimental functionality while deeper architecture remains open. Examples include dynamic arrays and advanced source projection/vocabulary behavior.

The memory/ownership model, complete native support for newer language constructs, inferred/mixed-language completion, and other advanced system-language work remain future development areas.

Known legacy or deferred regressions are tracked separately and do not redefine the validated typed baseline.

============================================================

# Version 0.0.2

**Release date:** September 28, 2026  
**Status:** Early Development Release

Quar SDK 0.0.2 expanded the initial Visual Quar toolchain into a broader development environment centered around Quar Edit, language profiles, external toolchain integration, and multilingual interface support.

------------------------------------------------------------------------

## Quar Edit

During the Quar SDK 0.0.2 line, Quar Edit remained at component version 0.0.1. SDK and editor versions are independent.

The editor baseline included file and folder operations, tab-based editing, saving and Save As, preferences infrastructure, keyboard shortcuts, themes, source templates, language profiles, source-extension recognition, and language-dependent build and execution operations.

Quar Edit connected supported language profiles to external compilers, interpreters, runtimes, and build tools. Operations could be enabled or disabled according to the selected language and availability of its required toolchain.

Build and execution timing were handled separately.

------------------------------------------------------------------------

## Visual Quar / QRVM / Native Path

Visual Quar remained the primary language of the ecosystem. Its development architecture used a frontend validation pipeline followed by either the QRVM development path or the C/native compilation path.

QRVM remained independent from the C backend, while the native path generated C source and delegated final compilation to an external native C toolchain.

------------------------------------------------------------------------

## Programming Languages and UI Localization

The Quar Edit 0.0.1 baseline included profiles for C, C++, Assembly, Rust, Pascal, Go, Zig, Python, Java, JavaScript, TypeScript, Mojo, Visual Quar, and FreeBASIC.

The release also included multilingual UI resources across a broad set of languages. Native-speaker review and graphical validation, particularly for right-to-left interfaces, remained ongoing work.

============================================================

# Version 0.0.1

**Release date:** September 17, 2026  
**Status:** Initial Development Release

Quar SDK 0.0.1 established the first working foundation of the Visual Quar toolchain.

------------------------------------------------------------------------

## Visual Quar

The first Visual Quar processing pipeline was established around lexical analysis, parsing, AST construction, and semantic analysis.

The initial language subset supported typed declarations, assignments, variables, integer values, arithmetic expressions, and operator precedence. External `.vq` source files could be processed by the toolchain.

------------------------------------------------------------------------

## QRVM

The first QRVM execution path introduced a Python reference implementation with a stack-oriented execution model independent from the C compilation backend.

------------------------------------------------------------------------

## C Transpilation and Native Compilation

Visual Quar programs could be transpiled to C and subsequently compiled into native executable code. Linux/GCC and Windows/MinGW paths were documented and tested during the initial foundation work.

Both the QRVM path and the C/native path were successfully tested for the initial language subset.

============================================================
