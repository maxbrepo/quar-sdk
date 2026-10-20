# Visual Quar — Language Manual (0.0.4 beta)

> **Status:** source-grounded draft, not a certified language standard. Generated from the supplied 2026-10-19 SDK archive and historical documentation. No repository source code was modified.

## Reading this manual

Three profiles are documented: **inferred** (`_inf`), **mixed** (`_mix`), and **typed** (`_typ`). These are source-profile choices, not three distinct languages. The typed profile covers familiar C-style types and fixed-width/system-oriented types; there is no separate “Rust mode” specified here.

**Evidence labels:** `EXAMPLE PRESENT` = exact `.vq` sample exists in the archive; `DOCUMENTED` = described in supplied project materials; `NOT DEMONSTRATED` = no mode-specific `.vq` sample was located. Example presence is not a runtime test or proof of native-backend parity.

The first-pass chapter reports contain historical failures and compatibility gaps. QRVM, IR/QIR, and native C support must be verified separately. Chapter 1 of the second review was reported validated by the project owner; the other chapters are not automatically considered second-pass complete.

## Chapters

01. **Primitive types, constants and conversions** — [inferred](./01-types/01-types_inf.md) · [mixed](./01-types/01-types_mix.md) · [typed](./01-types/01-types_typ.md)
02. **Operators and expressions** — [inferred](./02-operators/02-operators_inf.md) · [mixed](./02-operators/02-operators_mix.md) · [typed](./02-operators/02-operators_typ.md)
03. **Conditions and selection** — [inferred](./03-conditions/03-conditions_inf.md) · [mixed](./03-conditions/03-conditions_mix.md) · [typed](./03-conditions/03-conditions_typ.md)
04. **Loops and iteration** — [inferred](./04-loops/04-loops_inf.md) · [mixed](./04-loops/04-loops_mix.md) · [typed](./04-loops/04-loops_typ.md)
05. **Functions and parameters** — [inferred](./05-functions/05-functions_inf.md) · [mixed](./05-functions/05-functions_mix.md) · [typed](./05-functions/05-functions_typ.md)
06. **Arrays** — [inferred](./06-arrays/06-arrays_inf.md) · [mixed](./06-arrays/06-arrays_mix.md) · [typed](./06-arrays/06-arrays_typ.md)
07. **Strings and Unicode** — [inferred](./07-strings/07-strings_inf.md) · [mixed](./07-strings/07-strings_mix.md) · [typed](./07-strings/07-strings_typ.md)
08. **Structured types** — [inferred](./08-structures/08-structures_inf.md) · [mixed](./08-structures/08-structures_mix.md) · [typed](./08-structures/08-structures_typ.md)
09. **Object-oriented programming** — [inferred](./09-oop/09-oop_inf.md) · [mixed](./09-oop/09-oop_mix.md) · [typed](./09-oop/09-oop_typ.md)
10. **File input/output** — [inferred](./10-file-io/10-file-io_inf.md) · [mixed](./10-file-io/10-file-io_mix.md) · [typed](./10-file-io/10-file-io_typ.md)
11. **Console and environment** — [inferred](./11-console/11-console_inf.md) · [mixed](./11-console/11-console_mix.md) · [typed](./11-console/11-console_typ.md)
12. **Error handling** — [inferred](./12-errors/12-errors_inf.md) · [mixed](./12-errors/12-errors_mix.md) · [typed](./12-errors/12-errors_typ.md)
13. **Modules and imports** — [inferred](./13-modules/13-modules_inf.md) · [mixed](./13-modules/13-modules_mix.md) · [typed](./13-modules/13-modules_typ.md)
14. **Kart package manager** — [inferred](./14-kart/14-kart_inf.md) · [mixed](./14-kart/14-kart_mix.md) · [typed](./14-kart/14-kart_typ.md)
15. **Memory safety** — [inferred](./15-memory/15-memory_inf.md) · [mixed](./15-memory/15-memory_mix.md) · [typed](./15-memory/15-memory_typ.md)
16. **Diagnostics and source locations** — [inferred](./16-diagnostics/16-diagnostics_inf.md) · [mixed](./16-diagnostics/16-diagnostics_mix.md) · [typed](./16-diagnostics/16-diagnostics_typ.md)
17. **Intermediate representation (QIR)** — [inferred](./17-qir/17-qir_inf.md) · [mixed](./17-qir/17-qir_mix.md) · [typed](./17-qir/17-qir_typ.md)
18. **Bytecode and runtime** — [inferred](./18-runtime/18-runtime_inf.md) · [mixed](./18-runtime/18-runtime_mix.md) · [typed](./18-runtime/18-runtime_typ.md)

## Sources and limits

- `quar-sdk/README.md` (uploaded SDK release candidate).
- `quar-sdk/examples/0.0.3` and `quar-sdk/examples/0.0.4` (exact source examples).
- `__documentation/capitoli 1-12/DOSSIER_COMPLETO.md` (historical reconstruction).
- `__documentation/14`, `16`, `17` and other chapter-specific reports.

**Important:** Sections 16–18 cover compiler internals; these files intentionally avoid inventing user-facing syntax. The chapter-to-file split is a navigation scheme, not evidence that each chapter introduces three separate grammars.

## Editorial follow-up

Before calling this a normative language specification, audit each example against parser, semantic analysis, QRVM, QIR and C backend; record expected output/errors and assign explicit support status per profile.
